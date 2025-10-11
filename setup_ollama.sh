#!/bin/bash

echo "🎮 Agent Beats - Ollama Setup for M1 Mac"
echo "========================================"
echo ""

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama is not installed."
    echo "📥 Please install from: https://ollama.ai"
    echo "   Or run: brew install ollama"
    exit 1
fi

echo "✅ Ollama is installed"
echo ""

# Check if Ollama is running
if ! curl -s http://localhost:11434 > /dev/null 2>&1; then
    echo "⚠️  Ollama is not running"
    echo "🚀 Starting Ollama..."
    echo "   (You can also open the Ollama app)"
    echo ""
    echo "   Run in a separate terminal: ollama serve"
    echo ""
    echo "After starting Ollama, run this script again."
    exit 1
fi

echo "✅ Ollama is running"
echo ""

# Pull the recommended model
echo "📦 Pulling llama3.2:3b (recommended for M1 Mac)..."
echo "   This may take a few minutes..."
ollama pull llama3.2:3b

echo ""
echo "✅ Setup complete!"
echo ""
echo "🎮 Ready to play! Run: python run_game.py"
echo ""
echo "📝 Other models you can try:"
echo "   ollama pull qwen2.5:3b"
echo "   ollama pull phi3:mini"
echo "   ollama pull gemma2:2b"

