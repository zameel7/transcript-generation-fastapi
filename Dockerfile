# Dockerfile for Whisper AI FastAPI Transcription Service
# Supports both audio and video transcription with model pre-downloading

FROM python:3.9-slim-buster

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set working directory
WORKDIR /app

# Install system dependencies
# ffmpeg is essential for Whisper to process audio/video files
# git is required for installing packages from GitHub repositories
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Set up Python environment
ENV PATH="/home/app/.local/bin:$PATH"

# Copy requirements first for better Docker layer caching
COPY --chown=app:app requirements.txt .

# Install Python dependencies
RUN pip install --user --no-cache-dir -r requirements.txt

# Copy application files
COPY --chown=app:app main.py .
COPY --chown=app:app preload_models.py .
COPY --chown=app:app extract_audio.py .

# Configuration via build arguments and environment variables
ARG WHISPER_MODEL=turbo
ARG WHISPER_CACHE_DIR=/home/app/.cache/whisper
ENV WHISPER_MODEL=${WHISPER_MODEL}
ENV WHISPER_CACHE_DIR=${WHISPER_CACHE_DIR}

# Create cache directory with proper permissions
RUN mkdir -p ${WHISPER_CACHE_DIR}

# Pre-download the Whisper model during build (optional but recommended)
# This ensures the model is available immediately when the container starts
# Comment out the next line if you prefer to download on first use
RUN python preload_models.py --model ${WHISPER_MODEL} --cache-dir ${WHISPER_CACHE_DIR}

# Expose the port the app runs on
EXPOSE 8000

# Health check to ensure the service is running properly
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Default command to run the application
# Use uvicorn with proper configuration for production
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"] 