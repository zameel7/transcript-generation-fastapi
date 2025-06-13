#!/usr/bin/env python3
"""
Audio Extraction Utility for Whisper AI Transcription Service

This script extracts audio from video files using ffmpeg, making them
ready for transcription via the FastAPI Whisper service.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def extract_audio(video_path, output_path=None, audio_format="mp3", bitrate="128k", sample_rate="44100"):
    """
    Extract audio from a video file using ffmpeg.
    
    Args:
        video_path (str): Path to the input video file
        output_path (str): Path for the output audio file (optional)
        audio_format (str): Output audio format (mp3, wav, etc.)
        bitrate (str): Audio bitrate (e.g., "128k", "192k")
        sample_rate (str): Audio sample rate (e.g., "44100", "48000")
    
    Returns:
        str: Path to the extracted audio file
    """
    video_path = Path(video_path)
    
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    # Generate output path if not provided
    if output_path is None:
        output_path = video_path.parent / f"{video_path.stem}_audio.{audio_format}"
    else:
        output_path = Path(output_path)
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Build ffmpeg command
    cmd = [
        "ffmpeg",
        "-i", str(video_path),  # Input video
        "-vn",                  # No video output
        "-acodec", f"lib{audio_format}lame" if audio_format == "mp3" else "copy",
        "-ab", bitrate,         # Audio bitrate
        "-ar", sample_rate,     # Audio sample rate
        "-y",                   # Overwrite output file
        str(output_path)        # Output audio file
    ]
    
    # For WAV format, use different codec
    if audio_format == "wav":
        cmd[cmd.index(f"lib{audio_format}lame")] = "pcm_s16le"
    
    try:
        print(f"🎵 Extracting audio from: {video_path.name}")
        print(f"📁 Output: {output_path}")
        
        # Run ffmpeg command
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        print(f"✅ Audio extraction completed successfully!")
        print(f"📊 Output size: {output_path.stat().st_size / (1024*1024):.1f} MB")
        
        return str(output_path)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error extracting audio: {e}")
        print(f"Command: {' '.join(cmd)}")
        if e.stderr:
            print(f"Error details: {e.stderr}")
        raise
    except FileNotFoundError:
        print("❌ ffmpeg not found. Please install ffmpeg first:")
        print("   macOS: brew install ffmpeg")
        print("   Ubuntu: sudo apt update && sudo apt install ffmpeg")
        raise

def main():
    parser = argparse.ArgumentParser(
        description="Extract audio from video files for Whisper transcription"
    )
    parser.add_argument("video_path", help="Path to the input video file")
    parser.add_argument("-o", "--output", help="Output audio file path")
    parser.add_argument("-f", "--format", default="mp3", choices=["mp3", "wav"], 
                      help="Output audio format (default: mp3)")
    parser.add_argument("-b", "--bitrate", default="128k", 
                      help="Audio bitrate (default: 128k)")
    parser.add_argument("-r", "--sample-rate", default="44100", 
                      help="Audio sample rate (default: 44100)")
    
    args = parser.parse_args()
    
    try:
        output_file = extract_audio(
            video_path=args.video_path,
            output_path=args.output,
            audio_format=args.format,
            bitrate=args.bitrate,
            sample_rate=args.sample_rate
        )
        
        print(f"\n🎯 Audio ready for transcription!")
        print(f"Now you can test it with the FastAPI service:")
        print(f"   curl -X POST 'http://localhost:8000/transcribe/' \\")
        print(f"        -F 'audio_file=@{output_file}'")
        
    except Exception as e:
        print(f"❌ Failed to extract audio: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 