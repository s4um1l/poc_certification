#!/bin/bash

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Please install it with:"
    echo "curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "Setting up virtual environment..."
cd backend

# Clear any existing virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Removing existing virtual environment..."
    rm -rf .venv
fi

# Create a new virtual environment
echo "Creating new virtual environment..."
uv venv .venv

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    echo "# Add your API key here" > .env
    echo "# OPENAI_API_KEY=your_api_key_here" >> .env
    echo "# ANTHROPIC_API_KEY=your_api_key_here" >> .env
    echo "Please edit .env to add your API key"
fi

# Activate the virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies with the virtual environment
echo "Installing dependencies..."
uv pip install -r requirements.txt

# Generate data if it doesn't exist
if [ ! -f "data/products.csv" ]; then
    echo "Generating synthetic data..."
    python data_generator.py
fi

# Check if port 8000 is in use
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "Warning: Port 8000 is already in use. Killing the existing process..."
    lsof -Pi :8000 -sTCP:LISTEN -t | xargs kill -9
fi

# Run the backend server
echo "Starting FastAPI server..."
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 