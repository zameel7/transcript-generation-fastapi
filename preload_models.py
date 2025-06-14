#!/usr/bin/env python3
"""
Whisper Model Pre-loader

This utility script pre-downloads and caches Whisper models to ensure they're 
available locally before starting the FastAPI service. This is particularly useful 
for Docker container builds or deployment preparation.

Usage:
    python preload_models.py --model turbo
    python preload_models.py --model base --cache-dir ./models
    python preload_models.py --all  # Downloads all models
"""

import argparse
import os
import sys
import whisper
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Available Whisper models with their specifications
WHISPER_MODELS = {
    "tiny": {"size": "39M", "vram": "~1 GB", "speed": "~10x", "description": "Fastest, basic quality"},
    "base": {"size": "74M", "vram": "~1 GB", "speed": "~7x", "description": "Good balance of speed and quality"},
    "small": {"size": "244M", "vram": "~2 GB", "speed": "~4x", "description": "Better quality, moderate speed"},
    "medium": {"size": "769M", "vram": "~5 GB", "speed": "~2x", "description": "High quality, slower processing"},
    "large": {"size": "1550M", "vram": "~10 GB", "speed": "1x", "description": "Best quality, slowest processing"},
    "turbo": {"size": "809M", "vram": "~6 GB", "speed": "~8x", "description": "Optimized for speed with minimal quality loss"}
}

def preload_model(model_name: str, cache_dir: str = None) -> bool:
    """
    Pre-download and cache a specific Whisper model.
    
    Args:
        model_name: Name of the Whisper model to download
        cache_dir: Optional custom cache directory
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if model_name not in WHISPER_MODELS:
            logger.error(f"Unknown model '{model_name}'. Available models: {list(WHISPER_MODELS.keys())}")
            return False
            
        model_info = WHISPER_MODELS[model_name]
        logger.info(f"Downloading model '{model_name}' ({model_info['size']}, {model_info['description']})...")
        
        # Create cache directory if specified
        if cache_dir:
            cache_path = Path(cache_dir)
            cache_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Using cache directory: {cache_path.absolute()}")
        
        # Download/load the model (this will cache it locally)
        model = whisper.load_model(model_name, download_root=cache_dir)
        
        logger.info(f"✅ Model '{model_name}' successfully downloaded and cached!")
        logger.info(f"   Size: {model_info['size']}")
        logger.info(f"   VRAM: {model_info['vram']}")
        logger.info(f"   Speed: {model_info['speed']} relative to large model")
        
        # Clean up model from memory
        del model
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to download model '{model_name}': {e}")
        return False

def preload_all_models(cache_dir: str = None) -> dict:
    """
    Pre-download all available Whisper models.
    
    Args:
        cache_dir: Optional custom cache directory
        
    Returns:
        dict: Results for each model (True/False)
    """
    results = {}
    total_models = len(WHISPER_MODELS)
    
    logger.info(f"🚀 Starting download of all {total_models} Whisper models...")
    logger.info("⚠️  Warning: This will download several GB of data!")
    
    for i, model_name in enumerate(WHISPER_MODELS.keys(), 1):
        logger.info(f"\n📦 [{i}/{total_models}] Processing model: {model_name}")
        results[model_name] = preload_model(model_name, cache_dir)
    
    return results

def get_cache_info(cache_dir: str = None) -> dict:
    """
    Get information about cached models.
    
    Args:
        cache_dir: Optional custom cache directory
        
    Returns:
        dict: Information about cached models
    """
    if cache_dir:
        cache_path = Path(cache_dir)
    else:
        # Default Whisper cache directory
        cache_path = Path.home() / ".cache" / "whisper"
    
    info = {
        "cache_directory": str(cache_path.absolute()),
        "exists": cache_path.exists(),
        "cached_models": [],
        "total_size": 0
    }
    
    if cache_path.exists():
        # Look for .pt files (PyTorch model files)
        for model_file in cache_path.glob("*.pt"):
            size_bytes = model_file.stat().st_size
            size_mb = size_bytes / (1024 * 1024)
            
            info["cached_models"].append({
                "file": model_file.name,
                "size_mb": round(size_mb, 1),
                "size_bytes": size_bytes
            })
            info["total_size"] += size_bytes
    
    info["total_size_mb"] = round(info["total_size"] / (1024 * 1024), 1)
    
    return info

def main():
    parser = argparse.ArgumentParser(
        description="Pre-download Whisper models for the FastAPI transcription service",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=f"""
Available Models:
{chr(10).join([f"  {name:8} - {info['size']:>8} - {info['description']}" for name, info in WHISPER_MODELS.items()])}

Examples:
  python preload_models.py --model turbo
  python preload_models.py --model base --cache-dir ./models
  python preload_models.py --all
  python preload_models.py --info
"""
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--model", choices=list(WHISPER_MODELS.keys()),
                      help="Download a specific model")
    group.add_argument("--all", action="store_true",
                      help="Download all available models")
    group.add_argument("--info", action="store_true",
                      help="Show information about cached models")
    
    parser.add_argument("--cache-dir", type=str,
                       help="Custom cache directory (default: ~/.cache/whisper/)")
    
    args = parser.parse_args()
    
    try:
        if args.info:
            # Show cache information
            info = get_cache_info(args.cache_dir)
            print("\n📊 Whisper Model Cache Information:")
            print(f"   Cache Directory: {info['cache_directory']}")
            print(f"   Directory Exists: {info['exists']}")
            print(f"   Total Size: {info['total_size_mb']} MB")
            print(f"   Cached Models: {len(info['cached_models'])}")
            
            if info['cached_models']:
                print("\n   Details:")
                for model in info['cached_models']:
                    print(f"     {model['file']:30} - {model['size_mb']:>8.1f} MB")
            else:
                print("     No models cached yet.")
                
        elif args.model:
            # Download specific model
            success = preload_model(args.model, args.cache_dir)
            sys.exit(0 if success else 1)
            
        elif args.all:
            # Download all models
            results = preload_all_models(args.cache_dir)
            
            # Summary
            successful = sum(1 for success in results.values() if success)
            total = len(results)
            
            print(f"\n📊 Summary: {successful}/{total} models downloaded successfully")
            
            if successful < total:
                print("\n❌ Failed models:")
                for model, success in results.items():
                    if not success:
                        print(f"   - {model}")
                sys.exit(1)
            else:
                print("🎉 All models downloaded successfully!")
                
    except KeyboardInterrupt:
        logger.info("\n⚠️  Download cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 