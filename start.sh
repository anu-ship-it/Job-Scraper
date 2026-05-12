#!/bin/bash
# start.sh — One-click launcher for AI Job Scraper

echo ""
echo "⚡ AI Job Scraper — Startup"
echo "=================================="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Install from https://python.org"
    exit 1
fi

# Create virtualenv if not exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate
source venv/bin/activate

# Install deps if needed
echo "📦 Installing/updating dependencies..."
pip install -r requirements.txt -q

# Check Ollama
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo ""
    echo "⚠️  Ollama is not running!"
    echo "   Start it with: ollama serve"
    echo "   Pull model with: ollama pull llama3"
    echo ""
    echo "   The app will still start but AI features won't work"
    echo "   until Ollama is running."
    echo ""
fi

# Launch
echo ""
echo "🚀 Starting server on http://localhost:5000"
echo "   Press Ctrl+C to stop"
echo ""
python app.py
