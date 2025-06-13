# Whisper AI FastAPI Transcription Service

A high-performance FastAPI service that provides audio transcription using OpenAI Whisper. This service offers fast, accurate speech-to-text conversion with automatic language detection.

## Features

- 🚀 Fast transcription using OpenAI Whisper AI
- 🌍 Automatic language detection
- 📁 Support for multiple audio formats
- 🔄 Asynchronous processing
- 📊 Health checks and monitoring
- 🛡️ File size validation and error handling
- 📝 Comprehensive logging
- 🐳 Docker support ready

## Prerequisites

Before running this service, ensure you have:

- Python 3.8-3.11 (recommended: 3.9+)
- ffmpeg installed on your system
- Sufficient memory/VRAM for Whisper models:
  - `base`: ~1 GB VRAM, faster processing
  - `turbo`: ~6 GB VRAM, optimized for speed (default)
  - `medium`: ~5 GB VRAM, better quality
  - `large`: ~10 GB VRAM, highest quality

### Installing ffmpeg

#### macOS (using Homebrew)
```bash
brew install ffmpeg
```

#### Ubuntu/Debian
```bash
sudo apt update && sudo apt install ffmpeg
```

#### Windows (using Chocolatey)
```bash
choco install ffmpeg
```

## Installation & Setup

### 1. Clone the repository
```bash
git clone <repository-url>
cd transcript-generation-fastapi
```

### 2. Create and activate virtual environment
```bash
# Using virtualenvwrapper (recommended)
mkvirtualenv transcript-generation-fastapi
workon transcript-generation-fastapi

# OR using venv
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the application
```bash
# Development mode (with auto-reload)
python main.py

# OR using uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The service will be available at:
- **API**: http://localhost:8000
- **Interactive API Docs**: http://localhost:8000/docs
- **Alternative API Docs**: http://localhost:8000/redoc

## API Endpoints

### Health Check
- **GET** `/` - Basic service status
- **GET** `/health` - Detailed health check

### Transcription
- **POST** `/transcribe/` - Transcribe an audio file

#### Example Usage

Using curl:
```bash
curl -X POST "http://localhost:8000/transcribe/" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "audio_file=@your_audio_file.mp3"
```

Using Python requests:
```python
import requests

url = "http://localhost:8000/transcribe/"
files = {"audio_file": open("audio.mp3", "rb")}
response = requests.post(url, files=files)
result = response.json()

print(f"Transcribed text: {result['text']}")
print(f"Detected language: {result['language']}")
```

#### Response Format
```json
{
  "text": "Transcribed text content here...",
  "language": "en",
  "confidence": -0.234
}
```

## Configuration

### Model Selection
You can change the Whisper model in `main.py`:

```python
# In the startup_event function
model = whisper.load_model("turbo")  # Options: tiny, base, small, medium, large, turbo
```

### Performance Considerations

| Model  | Size | VRAM Required | Relative Speed | Use Case |
|--------|------|---------------|----------------|----------|
| tiny   | 39M  | ~1 GB         | ~10x          | Fast, basic quality |
| base   | 74M  | ~1 GB         | ~7x           | Good balance |
| small  | 244M | ~2 GB         | ~4x           | Better quality |
| medium | 769M | ~5 GB         | ~2x           | High quality |
| large  | 1550M| ~10 GB        | 1x            | Best quality |
| turbo  | 809M | ~6 GB         | ~8x           | Optimized speed |

## Docker Deployment

### 1. Create Dockerfile
```dockerfile
FROM python:3.9-slim-buster

WORKDIR /app

# Install system dependencies including ffmpeg
RUN apt update && apt install -y ffmpeg

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Build and run
```bash
# Build Docker image
docker build -t whisper-transcription .

# Run container
docker run -p 8000:8000 whisper-transcription
```

## Production Considerations

### Resource Management
- **Memory**: Ensure sufficient RAM/VRAM for your chosen model
- **Storage**: Consider disk space for temporary file handling
- **CPU**: Multi-core systems recommended for better performance

### Scaling
- Use multiple instances behind a load balancer
- Consider implementing async task queues for long audio files
- Monitor resource usage and scale accordingly

### Security
- Implement authentication (API keys, OAuth2)
- Add rate limiting
- Validate file types and sizes
- Use HTTPS in production
- Keep the service on a private network if possible

### Monitoring
- Use the `/health` endpoint for health checks
- Monitor logs for errors and performance metrics
- Set up alerts for service availability

## Supported Audio Formats

Whisper supports various audio formats through ffmpeg, including:
- MP3
- WAV
- M4A
- FLAC
- OGG
- AAC
- And many more...

## Troubleshooting

### Common Issues

1. **"No module named 'setuptools_rust'"**
   ```bash
   pip install setuptools-rust
   ```

2. **ffmpeg not found**
   - Install ffmpeg using your system's package manager
   - Ensure it's in your system PATH

3. **Out of memory errors**
   - Use a smaller model (e.g., `base` instead of `large`)
   - Reduce batch processing if implemented
   - Check available system memory

4. **Slow transcription**
   - Use GPU acceleration if available
   - Choose a faster model like `turbo`
   - Ensure sufficient system resources

## Development

### Running Tests
```bash
# Install test dependencies
pip install pytest httpx

# Run tests (when implemented)
pytest
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- OpenAI for the Whisper model
- FastAPI for the excellent web framework
- The open-source community for various dependencies 