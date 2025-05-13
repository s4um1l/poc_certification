#!/bin/bash

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Please install it with:"
    echo "curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f "backend/.env" ]; then
    echo "Creating .env file in backend directory..."
    echo "# Add your API key here" > backend/.env
    echo "# OPENAI_API_KEY=your_api_key_here" >> backend/.env
    echo "# ANTHROPIC_API_KEY=your_api_key_here" >> backend/.env
    echo "Please edit backend/.env to add your API key"
fi

# Generate data if it doesn't exist
if [ ! -f "backend/data/products.csv" ]; then
    echo "Generating synthetic data..."
    cd backend && uv pip install pandas faker && python data_generator.py
    cd ..
fi

# Install backend dependencies and run the server
echo "Installing dependencies and starting FastAPI server..."
cd backend && uv pip install -r requirements.txt && uv run python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 