#!/usr/bin/env python3
"""
Test script to verify the FastAPI Whisper transcription service works correctly.
This script tests the basic endpoints without actually loading the Whisper model.
"""

import requests
import sys
from time import sleep
import subprocess
import signal
import os

def test_health_endpoints():
    """Test the health check endpoints"""
    base_url = "http://localhost:8000"
    
    try:
        # Test root endpoint
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            print("✅ Root endpoint working")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Root endpoint failed: {response.status_code}")
            return False
            
        # Test health endpoint
        response = requests.get(f"{base_url}/health")
        if response.status_code in [200, 503]:  # 503 if model not loaded yet
            print("✅ Health endpoint working")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
            return False
            
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the FastAPI server")
        print("   Make sure the server is running on http://localhost:8000")
        return False

if __name__ == "__main__":
    print("🧪 Testing FastAPI Whisper Transcription Service")
    print("=" * 50)
    
    if test_health_endpoints():
        print("\n✅ All basic tests passed!")
        print("\n📝 To test the transcription endpoint:")
        print("   1. Start the server: python main.py")
        print("   2. Upload an audio file to http://localhost:8000/transcribe/")
        print("   3. Check the interactive docs at http://localhost:8000/docs")
    else:
        print("\n❌ Some tests failed!")
        print("\n🚀 To start the server:")
        print("   python main.py")
        sys.exit(1) 