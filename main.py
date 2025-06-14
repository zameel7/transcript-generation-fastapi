# main.py
"""
Whisper AI FastAPI Transcription Service

A FastAPI service that provides audio transcription using OpenAI Whisper.
This service exposes an API endpoint for transcript generation with proper
resource isolation and asynchronous processing capabilities.
"""

import whisper
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from pydantic import BaseModel, HttpUrl
import os
import shutil
import tempfile
import logging
import requests
import urllib.parse
from pathlib import Path
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title="Whisper AI Transcription Service",
    description="A high-performance transcription service using OpenAI Whisper for audio and video files",
    version="1.0.0"
)

# Global variable to store the Whisper model
model = None

# Configuration
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "turbo")  # Allow model selection via environment variable
WHISPER_CACHE_DIR = os.getenv("WHISPER_CACHE_DIR", None)  # Optional custom cache directory

def ensure_model_cached(model_name: str, cache_dir: str = None):
    """
    Ensure the Whisper model is downloaded and cached locally.
    This function can be called during container build or initialization.
    """
    try:
        logger.info(f"Ensuring model '{model_name}' is cached...")
        # This will download the model if not already cached
        whisper.load_model(model_name, download_root=cache_dir)
        logger.info(f"Model '{model_name}' is ready and cached!")
        return True
    except Exception as e:
        logger.error(f"Failed to cache model '{model_name}': {e}")
        return False

@app.on_event("startup")
async def startup_event():
    """
    Load the Whisper model when the application starts.
    This ensures the model is loaded once and reused for all requests.
    """
    global model
    try:
        # Pre-ensure the model is cached (this is idempotent)
        # Only download if not already cached to avoid memory issues
        logger.info(f"Ensuring model '{WHISPER_MODEL}' is cached...")
        ensure_model_cached(WHISPER_MODEL, WHISPER_CACHE_DIR)
        
        # Load the model as recommended in the context
        # 'turbo' is optimized for speed with minimal accuracy degradation (~6 GB VRAM, ~8x relative speed)
        # Alternative options: 'base' (~1 GB VRAM), 'medium' (~5 GB VRAM), 'large' (~10 GB VRAM)
        logger.info(f"Loading Whisper model '{WHISPER_MODEL}' into memory...")
        model = whisper.load_model(WHISPER_MODEL, download_root=WHISPER_CACHE_DIR)
        logger.info(f"Whisper model '{WHISPER_MODEL}' loaded successfully!")
    except MemoryError as e:
        logger.error(f"Not enough memory to load model '{WHISPER_MODEL}': {e}")
        logger.error("Try using a smaller model like 'base' or increase Docker memory allocation")
        raise e
    except Exception as e:
        logger.error(f"Failed to load Whisper model: {e}")
        # In production, you might want to exit gracefully or implement retry logic
        raise e

# Define the response model for consistent API output
class TranscriptionResponse(BaseModel):
    text: str
    language: str
    confidence: float = None
    file_type: str = None  # 'audio' or 'video'
    source: str = None  # 'upload' or 'url'
    
class HealthResponse(BaseModel):
    status: str
    message: str
    model_info: dict = None

class UrlTranscriptionRequest(BaseModel):
    url: HttpUrl
    max_file_size_mb: Optional[int] = 500  # Default max size in MB

@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint to check if the service is running."""
    return HealthResponse(
        status="healthy",
        message="Whisper AI Transcription Service is running!"
    )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for monitoring."""
    if model is None:
        raise HTTPException(status_code=503, detail="Service unavailable: Model not loaded")
    
    model_info = {
        "model_name": WHISPER_MODEL,
        "cache_dir": WHISPER_CACHE_DIR or "default (~/.cache/whisper/)",
        "supported_formats": {
            "audio": ["mp3", "wav", "m4a", "flac", "ogg", "aac", "opus"],
            "video": ["mp4", "avi", "mov", "mkv", "webm", "m4v", "3gp"]
        }
    }
    
    return HealthResponse(
        status="healthy",
        message="Service is ready to process transcriptions",
        model_info=model_info
    )

# Supported file extensions
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.opus', '.wma'}
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.m4v', '.3gp', '.flv', '.wmv'}

def get_file_type(filename: str) -> str:
    """Determine if the file is audio or video based on extension."""
    ext = Path(filename).suffix.lower()
    if ext in AUDIO_EXTENSIONS:
        return "audio"
    elif ext in VIDEO_EXTENSIONS:
        return "video"
    else:
        return "unknown"

def download_file_from_url(url: str, max_size_bytes: int = 500 * 1024 * 1024) -> tuple[str, str]:
    """
    Download a file from URL to a temporary location.
    
    Args:
        url: The URL to download from
        max_size_bytes: Maximum file size in bytes
        
    Returns:
        tuple: (temp_file_path, original_filename)
        
    Raises:
        HTTPException: If download fails or file is too large
    """
    try:
        # Parse URL to get filename
        parsed_url = urllib.parse.urlparse(url)
        original_filename = os.path.basename(parsed_url.path)
        
        # If no filename in URL, try to get from Content-Disposition header
        if not original_filename or '.' not in original_filename:
            try:
                head_response = requests.head(url, timeout=10, allow_redirects=True)
                content_disposition = head_response.headers.get('content-disposition', '')
                if 'filename=' in content_disposition:
                    original_filename = content_disposition.split('filename=')[1].strip('"')
                else:
                    # Fallback to content-type
                    content_type = head_response.headers.get('content-type', '')
                    if 'video' in content_type:
                        original_filename = 'video_file.mp4'
                    elif 'audio' in content_type:
                        original_filename = 'audio_file.mp3'
                    else:
                        original_filename = 'media_file'
            except:
                original_filename = 'media_file'
        
        # Ensure filename has an extension
        if '.' not in original_filename:
            original_filename += '.mp4'  # Default to mp4
            
        logger.info(f"Downloading file from URL: {url}")
        logger.info(f"Detected filename: {original_filename}")
        
        # Start download with streaming
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        # Check content length if available
        content_length = response.headers.get('content-length')
        if content_length and int(content_length) > max_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {max_size_bytes // (1024*1024)}MB."
            )
        
        # Create temporary file with appropriate extension
        file_ext = Path(original_filename).suffix
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
        temp_file_path = temp_file.name
        
        # Download with size checking
        downloaded_size = 0
        chunk_size = 8192
        
        with temp_file:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    downloaded_size += len(chunk)
                    if downloaded_size > max_size_bytes:
                        temp_file.close()
                        os.unlink(temp_file_path)
                        raise HTTPException(
                            status_code=413,
                            detail=f"File too large. Maximum size is {max_size_bytes // (1024*1024)}MB."
                        )
                    temp_file.write(chunk)
        
        logger.info(f"Downloaded {downloaded_size} bytes to {temp_file_path}")
        return temp_file_path, original_filename
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download file from URL {url}: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to download file: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error downloading from URL {url}: {e}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@app.post("/transcribe/", response_model=TranscriptionResponse)
async def transcribe_media(media_file: UploadFile = File(...)):
    """
    Transcribes an uploaded audio or video file using OpenAI Whisper AI.
    
    For video files, Whisper automatically extracts and processes the audio track.
    
    Args:
        media_file: The audio/video file to transcribe (supports various formats)
        
    Returns:
        TranscriptionResponse containing the transcribed text and detected language
        
    Raises:
        HTTPException: If transcription fails or invalid file is provided
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Service unavailable: Model not loaded")
    
    if not media_file.filename:
        raise HTTPException(status_code=400, detail="No media file provided.")

    # Determine file type
    file_type = get_file_type(media_file.filename)
    if file_type == "unknown":
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file format. Supported formats: {list(AUDIO_EXTENSIONS | VIDEO_EXTENSIONS)}"
        )

    # Validate file size (e.g., max 500MB for video, 100MB for audio)
    max_size = 500 * 1024 * 1024 if file_type == "video" else 100 * 1024 * 1024
    file_size = 0
    temp_media_path = None
    
    try:
        # Create a temporary file to save the uploaded media
        # Whisper's transcribe() method expects a file path
        with tempfile.NamedTemporaryFile(
            delete=False, 
            suffix=os.path.splitext(media_file.filename)[1]
        ) as temp_media:
            # Copy the uploaded file content to temporary file
            shutil.copyfileobj(media_file.file, temp_media)
            temp_media_path = temp_media.name
            file_size = os.path.getsize(temp_media_path)
            
        # Check file size
        if file_size > max_size:
            max_size_mb = max_size // (1024 * 1024)
            raise HTTPException(
                status_code=413, 
                detail=f"File too large. Maximum size for {file_type} files is {max_size_mb}MB."
            )
        
        # Perform transcription using the loaded Whisper model
        # For video files, Whisper automatically extracts the audio track
        # The transcribe() method reads the entire file and processes audio with a sliding 30-second window
        # It automatically detects the language by default
        logger.info(f"Starting transcription for {media_file.filename} ({file_type}, size: {file_size} bytes)")
        
        result = model.transcribe(temp_media_path)
        
        logger.info(f"Transcription completed for {media_file.filename}")

        # Extract results
        transcribed_text = result["text"].strip()
        detected_language = result.get("language", "unknown")
        
        # Basic confidence estimation based on result segments if available
        confidence = None
        if "segments" in result and result["segments"]:
            # Calculate average confidence from segments
            confidences = [segment.get("avg_logprob", 0) for segment in result["segments"]]
            if confidences:
                confidence = sum(confidences) / len(confidences)
        
        return TranscriptionResponse(
            text=transcribed_text,
            language=detected_language,
            confidence=confidence,
            file_type=file_type,
            source="upload"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Transcription failed for {media_file.filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    finally:
        # Clean up the temporary file
        if temp_media_path and os.path.exists(temp_media_path):
            try:
                os.remove(temp_media_path)
                logger.debug(f"Cleaned up temporary file: {temp_media_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file {temp_media_path}: {e}")

# Legacy endpoint alias for backward compatibility
@app.post("/transcribe/audio/", response_model=TranscriptionResponse)
async def transcribe_audio_legacy(audio_file: UploadFile = File(...)):
    """Legacy endpoint for audio-only transcription (redirects to main endpoint)."""
    return await transcribe_media(audio_file)

# New explicit video endpoint
@app.post("/transcribe/video/", response_model=TranscriptionResponse)
async def transcribe_video(video_file: UploadFile = File(...)):
    """
    Transcribes a video file by extracting and processing its audio track.
    
    Args:
        video_file: The video file to transcribe
        
    Returns:
        TranscriptionResponse containing the transcribed text from the video's audio
    """
    if not video_file.filename:
        raise HTTPException(status_code=400, detail="No video file provided.")
    
    file_type = get_file_type(video_file.filename)
    if file_type != "video":
        raise HTTPException(
            status_code=400,
            detail=f"Expected video file. Supported video formats: {list(VIDEO_EXTENSIONS)}"
        )
    
    return await transcribe_media(video_file)

# URL-based transcription endpoints
@app.post("/transcribe/url/", response_model=TranscriptionResponse)
async def transcribe_from_url(request: UrlTranscriptionRequest):
    """
    Transcribes audio/video from a URL by downloading it first.
    
    Args:
        request: Contains the URL and optional parameters
        
    Returns:
        TranscriptionResponse containing the transcribed text
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Service unavailable: Model not loaded")
    
    temp_file_path = None
    
    try:
        # Download file from URL
        max_size_bytes = request.max_file_size_mb * 1024 * 1024
        temp_file_path, original_filename = download_file_from_url(str(request.url), max_size_bytes)
        
        # Determine file type
        file_type = get_file_type(original_filename)
        if file_type == "unknown":
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format. Supported formats: {list(AUDIO_EXTENSIONS | VIDEO_EXTENSIONS)}"
            )
        
        # Perform transcription
        logger.info(f"Starting transcription for URL: {request.url} ({file_type})")
        
        result = model.transcribe(temp_file_path)
        
        logger.info(f"Transcription completed for URL: {request.url}")
        
        # Extract results
        transcribed_text = result["text"].strip()
        detected_language = result.get("language", "unknown")
        
        # Basic confidence estimation
        confidence = None
        if "segments" in result and result["segments"]:
            confidences = [segment.get("avg_logprob", 0) for segment in result["segments"]]
            if confidences:
                confidence = sum(confidences) / len(confidences)
        
        return TranscriptionResponse(
            text=transcribed_text,
            language=detected_language,
            confidence=confidence,
            file_type=file_type,
            source="url"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription failed for URL {request.url}: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    finally:
        # Clean up downloaded file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.debug(f"Cleaned up downloaded file: {temp_file_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up downloaded file {temp_file_path}: {e}")

# Alternative endpoint with query parameter for simple URL transcription
@app.post("/transcribe/from-url/", response_model=TranscriptionResponse)
async def transcribe_from_url_simple(url: HttpUrl = Query(..., description="URL of the audio/video file to transcribe")):
    """
    Simple endpoint to transcribe from URL using query parameter.
    
    Args:
        url: The URL of the audio/video file to transcribe
        
    Returns:
        TranscriptionResponse containing the transcribed text
    """
    request = UrlTranscriptionRequest(url=url)
    return await transcribe_from_url(request)

# Utility endpoint to pre-download models
@app.post("/admin/preload-model/")
async def preload_model(model_name: str = "turbo"):
    """
    Administrative endpoint to pre-download and cache a Whisper model.
    Useful for warming up containers or preparing for model switches.
    """
    try:
        success = ensure_model_cached(model_name, WHISPER_CACHE_DIR)
        if success:
            return {"message": f"Model '{model_name}' successfully cached", "model": model_name}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to cache model '{model_name}'")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error caching model: {str(e)}")

# Additional endpoint for batch processing (future enhancement)
@app.post("/transcribe/batch")
async def transcribe_batch():
    """
    Placeholder for batch transcription endpoint.
    This could be implemented for processing multiple files asynchronously.
    """
    raise HTTPException(status_code=501, detail="Batch transcription not yet implemented")

if __name__ == "__main__":
    import uvicorn
    
    # Run the application
    # This is useful for development. In production, use: uvicorn main:app --host 0.0.0.0 --port 8000
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload during development
        log_level="info"
    ) 