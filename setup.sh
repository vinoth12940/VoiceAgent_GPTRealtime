#!/bin/bash

# Voice Agent GPT Realtime - Setup Script
# This script sets up the project on a new machine

set -e  # Exit on any error

echo "============================================================"
echo "  Voice Agent GPT Realtime - Setup Script"
echo "============================================================"

# Check if Python is available
if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python is not installed. Please install Python 3.8+ first."
    exit 1
fi

# Use python3 if available, otherwise python
PYTHON_CMD="python"
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
fi

echo "🐍 Using Python: $($PYTHON_CMD --version)"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "🔧 Creating virtual environment..."
    $PYTHON_CMD -m venv .venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "❌ Error: Could not find virtual environment activation script"
    exit 1
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "✅ Dependencies installed"
else
    echo "⚠️  Warning: requirements.txt not found"
fi

# Initialize database
echo "🗄️  Initializing database..."
if [ -f "init_db.py" ]; then
    $PYTHON_CMD init_db.py
    echo "✅ Database initialized"
else
    echo "❌ Error: init_db.py not found"
    exit 1
fi

# Check if config file exists
echo "⚙️  Checking configuration..."
if [ -f "config.template" ] && [ ! -f "backend/config.py" ]; then
    echo "📝 Please copy config.template to backend/config.py and update with your settings:"
    echo "   cp config.template backend/config.py"
    echo "   # Then edit backend/config.py with your OpenAI API key"
elif [ -f "backend/config.py" ]; then
    echo "✅ Configuration file found"
else
    echo "⚠️  Warning: No configuration template found"
fi

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "📋 Next steps:"
echo "   1. Make sure your OpenAI API key is configured in backend/config.py"
echo "   2. Activate the virtual environment (if not already active):"
echo "      source .venv/bin/activate"
echo "   3. Start the backend server:"
echo "      cd backend && python -m uvicorn main:app --reload"
echo "   4. Open http://localhost:8000 in your browser"
echo ""
echo "💡 For more information, see README.md"
echo ""
echo "🔌 Virtual environment is currently activated. To deactivate later, run: deactivate"
