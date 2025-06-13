# main.py
"""
Whisper AI FastAPI Transcription Service

A FastAPI service that provides audio transcription using OpenAI Whisper.
This service exposes an API endpoint for transcript generation with proper
resource isolation and asynchronous processing capabilities.
"""

import whisper
from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
import os
import shutil
import tempfile
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title="Whisper AI Transcription Service",
    description="A high-performance transcription service using OpenAI Whisper",
    version="1.0.0"
)

# Global variable to store the Whisper model
model = None

@app.on_event("startup")
async def startup_event():
    """
    Load the Whisper model when the application starts.
    This ensures the model is loaded once and reused for all requests.
    """
    global model
    try:
        # Load the turbo model as recommended in the context
        # 'turbo' is optimized for speed with minimal accuracy degradation (~6 GB VRAM, ~8x relative speed)
        # Alternative options: 'base' (~1 GB VRAM), 'medium' (~5 GB VRAM), 'large' (~10 GB VRAM)
        logger.info("Loading Whisper model...")
        model = whisper.load_model("turbo")
        logger.info("Whisper model loaded successfully!")
    except Exception as e:
        logger.error(f"Failed to load Whisper model: {e}")
        # In production, you might want to exit gracefully or implement retry logic
        raise e

# Define the response model for consistent API output
class TranscriptionResponse(BaseModel):
    text: str
    language: str
    confidence: float = None
    
class HealthResponse(BaseModel):
    status: str
    message: str

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
    
    return HealthResponse(
        status="healthy",
        message="Service is ready to process transcriptions"
    )

@app.post("/transcribe/", response_model=TranscriptionResponse)
async def transcribe_audio(audio_file: UploadFile = File(...)):
    """
    Transcribes an uploaded audio file using OpenAI Whisper AI.
    
    Args:
        audio_file: The audio file to transcribe (supports various formats)
        
    Returns:
        TranscriptionResponse containing the transcribed text and detected language
        
    Raises:
        HTTPException: If transcription fails or invalid file is provided
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Service unavailable: Model not loaded")
    
    if not audio_file.filename:
        raise HTTPException(status_code=400, detail="No audio file provided.")

    # Validate file size (e.g., max 100MB)
    file_size = 0
    temp_audio_path = None
    
    try:
        # Create a temporary file to save the uploaded audio
        # Whisper's transcribe() method expects a file path
        with tempfile.NamedTemporaryFile(
            delete=False, 
            suffix=os.path.splitext(audio_file.filename)[1]
        ) as temp_audio:
            # Copy the uploaded file content to temporary file
            shutil.copyfileobj(audio_file.file, temp_audio)
            temp_audio_path = temp_audio.name
            file_size = os.path.getsize(temp_audio_path)
            
        # Check file size (100MB limit)
        if file_size > 100 * 1024 * 1024:  # 100MB
            raise HTTPException(status_code=413, detail="File too large. Maximum size is 100MB.")
        
        # Perform transcription using the loaded Whisper model
        # The transcribe() method reads the entire file and processes audio with a sliding 30-second window
        # It automatically detects the language by default
        logger.info(f"Starting transcription for {audio_file.filename} (size: {file_size} bytes)")
        
        result = model.transcribe(temp_audio_path)
        
        logger.info(f"Transcription completed for {audio_file.filename}")

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
            confidence=confidence
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Transcription failed for {audio_file.filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    finally:
        # Clean up the temporary file
        if temp_audio_path and os.path.exists(temp_audio_path):
            try:
                os.remove(temp_audio_path)
                logger.debug(f"Cleaned up temporary file: {temp_audio_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file {temp_audio_path}: {e}")

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