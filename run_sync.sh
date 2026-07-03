#!/bin/bash
set -e

# Get the directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
VENV_DIR="$DIR/venv"

# Intercept the --cleanup flag
if [[ "$1" == "--cleanup" ]]; then
    if [ -d "$VENV_DIR" ]; then
        echo "🗑️  Removing virtual environment at $VENV_DIR..."
        rm -rf "$VENV_DIR"
        echo "✅ Cleanup complete!"
    else
        echo "[-] No virtual environment found to clean up."
    fi
    exit 0
fi

# Ensure the virtual environment exists, build it if it doesn't
if [ ! -d "$VENV_DIR" ]; then
    echo "⚙️  First-time setup detected. Checking system dependencies..."
    
    if ! command -v python3 &> /dev/null; then
        echo "[-] Error: python3 is not installed."
        exit 1
    fi
    
    if ! command -v ffmpeg &> /dev/null; then
        echo "[-] Error: ffmpeg is not installed. Please install it (e.g., sudo apt install ffmpeg)."
        exit 1
    fi
    
    echo "📦 Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    
    echo "⬇️  Installing required dependencies (faster-whisper)..."
    "$VENV_DIR/bin/pip" install --upgrade pip
    "$VENV_DIR/bin/pip" install faster-whisper
    "$VENV_DIR/bin/pip" install requests
    
    echo "✨ Initial setup complete!"
    echo "--------------------------------------------------------"
fi

# Execute the python script using the venv interpreter 
# while passing along all CLI arguments ("$@")
"$VENV_DIR/bin/python" "$DIR/subtitle_sync.py" "$@"
