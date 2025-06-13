Building a Whisper AI FastAPI Transcription Service

Certainly, building upon our previous discussions about creating an external service for transcript generation to ensure resource isolation and manage asynchronous processing for your Open edX plugin [Conversation History], let's outline the steps for setting up a FastAPI service. This service will host OpenAI Whisper AI and expose an API endpoint for transcript generation.
FastAPI is an excellent choice for this purpose due to its high performance and ease of use. Please note that while the sources detail Whisper AI installation and usage, the specific steps for setting up FastAPI and Uvicorn are outside the provided sources and represent common best practices for web service deployment in Python.
Steps to Create a FastAPI Service for Whisper AI
This setup assumes you're preparing a Docker image for deployment (e.g., in Kubernetes) or directly on a Linux-based server.
1. Core Prerequisites and Python Environment Setup
Before setting up the FastAPI application, you need to ensure the underlying system has the necessary components for Whisper AI.
•
Python Installation: Whisper AI works with Python versions 3.8-3.11. The codebase is expected to be compatible with Python 3.8-3.11. When installing Python on a system (like a virtual machine or a base Docker image), ensure you add python.exe to the system's PATH, which allows running Python commands directly from the command prompt.
•
ffmpeg Installation: This is a crucial command-line tool that Whisper AI requires to "read the different audio files, so whether it's a WAV file or whether it's an MP3". ffmpeg is a system-level dependency, not a Python package installable via pip [Conversation History, 8].
◦
For Ubuntu or Debian-based systems (common in Docker environments), you would typically run:
◦
This command updates the package list and then installs ffmpeg.
•
PyTorch Installation: PyTorch is a machine learning library that Whisper AI depends on.
◦
You should install the current stable version.
◦
Choose your operating system (Linux, Mac, or Windows) and package type as PIP.
◦
For the compute platform, if your server has a high-end Nvidia graphics card (GPU), selecting CUDA (e.g., CUDA 11.8) is highly recommended for faster processing. Otherwise, choose CPU, although this will be slower.
◦
The PyTorch website provides the exact pip install command based on your selections.
•
Whisper AI Installation: Install the openai-whisper package using pip.
•
Alternatively, to install the latest commit from the GitHub repository along with its Python dependencies:
•
Rust Installation (Conditional): You may need Rust installed if tiktoken (Whisper's fast tokenizer implementation) does not provide a pre-built wheel for your platform. If you encounter a No module named 'setuptools_rust' error during the pip install command, you need to install setuptools-rust:
•
You might also need to configure the PATH environment variable for Rust.
2. FastAPI Application Structure (Example )
Here's a basic structure for your FastAPI application.
# main.py
import whisper
from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
import os
import shutil
import tempfile

# Initialize FastAPI application
app = FastAPI(title="Whisper AI Transcription Service")

# Load the Whisper model globally when the application starts
# This will download the model the first time it's used [9]
# Choose a model that balances speed and accuracy based on your needs [11, 12]
# 'turbo' is optimized for speed with minimal accuracy degradation (~6 GB VRAM, ~8x relative speed) [12]
# 'base' is smaller (~1 GB VRAM, ~7x relative speed) [12]
# 'medium' offers better quality but requires more VRAM (~5 GB VRAM, ~2x relative speed) [12-14]
try:
    # It's good practice to try loading a smaller model first if resources are limited,
    # or specify 'turbo' if speed is critical and VRAM is sufficient.
    # We'll use 'turbo' as it was mentioned as a good default [15].
    model = whisper.load_model("turbo")
except Exception as e:
    print(f"Failed to load Whisper model: {e}")
    # You might want to exit or handle this more gracefully depending on your deployment strategy
    # For a real service, you might want to log this error and potentially restart.

# Define the response model for consistent API output
class TranscriptionResponse(BaseModel):
    text: str
    language: str

@app.get("/")
async def root():
    return {"message": "Whisper AI Transcription Service is running!"}

@app.post("/transcribe/", response_model=TranscriptionResponse)
async def transcribe_audio(audio_file: UploadFile = File(...)):
    """
    Transcribes an uploaded audio file using OpenAI Whisper AI.
    """
    if not audio_file.filename:
        raise HTTPException(status_code=400, detail="No audio file provided.")

    # Create a temporary file to save the uploaded audio
    # Whisper's transcribe() method expects a file path [16]
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio_file.filename)[17]) as temp_audio:
            shutil.copyfileobj(audio_file.file, temp_audio)
            temp_audio_path = temp_audio.name
        
        # Perform transcription using the loaded Whisper model
        # The transcribe() method reads the entire file and processes audio with a sliding 30-second window [9, 16]
        # It automatically detects the language by default [9, 18]
        print(f"Transcribing {audio_file.filename}...")
        result = model.transcribe(temp_audio_path)
        print(f"Transcription complete for {audio_file.filename}.")

        # Whisper can automatically detect the language [18]
        detected_language = result.get("language", "unknown")
        
        return TranscriptionResponse(text=result["text"], language=detected_language)
    except Exception as e:
        print(f"Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")
    finally:
        # Clean up the temporary file
        if 'temp_audio_path' in locals() and os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)

# To run this FastAPI application:
# 1. Save the code above as `main.py`.
# 2. Install FastAPI and Uvicorn (if not already installed):
#    pip install fastapi uvicorn
# 3. Run the application from your terminal:
#    uvicorn main:app --host 0.0.0.0 --port 8000
# The service will then be accessible at http://localhost:8000
# You can test the /transcribe endpoint by sending a POST request with an audio file.
Explanation of the FastAPI Application:
•
import whisper: Imports the Whisper AI library.
•
FastAPI: Initializes the web application framework.
•
Model Loading: The model = whisper.load_model("turbo") line loads the specified Whisper model. This happens once when the application starts, which is efficient as it avoids reloading the model for every request. The turbo model is a good choice for speed, offering minimal accuracy degradation.
•
/transcribe/ Endpoint:
◦
It's defined as a POST request, suitable for sending audio files.
◦
audio_file: UploadFile = File(...) tells FastAPI to expect an uploaded file in the request body.
◦
Temporary File Handling: Since whisper.transcribe() expects a file path, the uploaded UploadFile content is saved to a temporary file using tempfile and shutil. This temporary file is crucial because ffmpeg (which Whisper uses internally) operates on disk files. The finally block ensures the temporary file is cleaned up after processing.
◦
model.transcribe(temp_audio_path): This is the core call to Whisper AI, which performs the speech-to-text conversion. It "reads the entire file and processes the audio with a sliding 30-second window". It also automatically detects the language of the audio.
◦
Error Handling: Basic try-except blocks are included to catch potential issues during transcription or file handling.
◦
Response: The transcribed text and language are returned in a JSON format, adhering to the TranscriptionResponse Pydantic model for clear API schema.
3. Dockerfile Context File Example
To containerise this FastAPI service, you would create a Dockerfile. This Dockerfile bundles your application code, Python dependencies, and system-level dependencies like ffmpeg.
# Dockerfile
# Use a Python base image with Debian/Ubuntu (like slim-buster)
# This provides Python and a Linux environment where apt can be used.
FROM python:3.9-slim-buster

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies
# This includes ffmpeg, which is essential for Whisper AI to process audio files [3, 4]
RUN apt update && apt install -y ffmpeg

# Install Python dependencies
# FastAPI and Uvicorn are for the web service.
# openai-whisper is for the transcription.
# setuptools-rust is conditional if pre-built tiktoken wheels aren't available [10, 11]
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your application code into the container
COPY main.py .

# Expose the port that Uvicorn will run on
EXPOSE 8000

# Command to run the FastAPI application using Uvicorn
# The --host 0.0.0.0 makes the server accessible from outside the container.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
Corresponding requirements.txt:
fastapi
uvicorn
openai-whisper
# Optionally, if you encounter 'No module named 'setuptools_rust'' during build [10]:
# setuptools-rust
How to build and run the Docker image:
1.
Save the FastAPI code as main.py and the dependencies as requirements.txt in the same directory as your Dockerfile.
2.
Navigate to that directory in your terminal.
3.
Build the Docker image:
4.
Run the Docker container:
5.
Your service will then be accessible at http://localhost:8000.
Key Considerations for Production Deployment
•
Model Size and Resources: The chosen Whisper model (e.g., turbo, medium, large) directly impacts the Required VRAM and Relative speed. Larger models offer better quality but require more resources and take longer to process. Ensure your deployment environment (VM or Kubernetes node) has sufficient CPU, RAM, and especially GPU (VRAM) if you're using CUDA-enabled PyTorch for faster transcription.
•
Asynchronous Processing: For very long audio files, a direct synchronous API call might time out or block your Open edX plugin. Consider implementing an asynchronous pattern (e.g., a task queue like Celery that processes requests in the background and notifies Open edX via a webhook when complete) [Conversation History]. This is outside the provided sources but a critical architectural consideration.
•
Scalability: An external service allows you to scale the transcription component independently of your core Open edX platform [Conversation History]. You can run multiple instances of this FastAPI service to handle increased transcription load.
•
Security: Ensure your API endpoint is secured (e.g., with API keys or OAuth2) if exposed to the public internet, or keep it on a private network if only internal services will access it. This is outside the provided sources.
•
Docker Image Size: Incorporating ffmpeg and the Whisper models (which can be several gigabytes depending on the chosen size) will contribute to a larger size for your Docker image [Conversation History].