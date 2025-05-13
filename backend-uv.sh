#!/bin/bash

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Please install it with:"
    echo "curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Define directories relative to the script's execution location
# This script assumes it is run from the project root (e.g., poc_certification)
PROJECT_ROOT_DIR=$(pwd)
BACKEND_DIR="$PROJECT_ROOT_DIR/backend"

echo "Project root directory: $PROJECT_ROOT_DIR"
echo "Backend directory: $BACKEND_DIR"

if [ ! -d "$BACKEND_DIR" ]; then
    echo "Error: Backend directory not found at $BACKEND_DIR"
    echo "Please run this script from the project root directory (the one containing the 'backend' folder)."
    exit 1
fi

echo "Changing to backend directory: $BACKEND_DIR"
cd "$BACKEND_DIR"
if [ $? -ne 0 ]; then
    echo "Error: Failed to change directory to $BACKEND_DIR"
    exit 1
fi

echo "Current working directory before Uvicorn: $(pwd)"

# --- Operations within backend directory --- 

# Clear any existing virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Removing existing virtual environment..."
    rm -rf .venv
fi

# Create a new virtual environment
echo "Creating new virtual environment in $(pwd)..."
uv venv .venv --python 3.12
if [ $? -ne 0 ]; then
    echo "Error: Failed to create virtual environment."
    exit 1
fi

# Define path to venv python AFTER creating it
VENV_PYTHON_PATH="$(pwd)/.venv/bin/python"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    echo "# Add your API key here" > .env
    echo "# OPENAI_API_KEY=your_api_key_here" >> .env
    echo "# ANTHROPIC_API_KEY=your_api_key_here" >> .env
    echo "Please edit .env to add your API key"
fi

# Activate the virtual environment (Needed for uv pip install .? Maybe not, uv might detect venv)
# echo "Activating virtual environment (for dependency installation)..."
# source .venv/bin/activate 
# Using uv with venv might not require explicit activation for install command

# Install dependencies with the virtual environment
echo "Installing dependencies using uv pip install . (reads pyproject.toml in $(pwd))..."
if [ -f "pyproject.toml" ]; then
    # uv should automatically detect and use the .venv in the current directory
    uv pip install .
    if [ $? -ne 0 ]; then
        echo "Error: uv pip install failed."
        exit 1
    fi
else
    echo "Error: pyproject.toml not found in $(pwd). Cannot install dependencies."
    exit 1
    # echo "Warning: pyproject.toml not found in $(pwd). Falling back to requirements.txt"
    # uv pip install -r requirements.txt
fi

# Generate data if it doesn't exist
if [ ! -f "data/products.csv" ]; then
    echo "Generating synthetic data..."
    # Use the python from the created venv
    # Activate first or use direct path?
    # uv run might be better: uv run python data_generator.py
    # Or use direct path to venv python
    ".venv/bin/python" data_generator.py
    if [ $? -ne 0 ]; then
        echo "Error: Failed to generate data."
        # Decide if this is a fatal error
        # exit 1
    fi
fi

# --- REMOVED: Operations back in project root directory --- 
# echo "Changing back to project root directory: $PROJECT_ROOT_DIR"
# cd "$PROJECT_ROOT_DIR"
# if [ $? -ne 0 ]; then
#     echo "Error: Failed to change directory back to $PROJECT_ROOT_DIR"
#     exit 1
# fi

# Check if port 8000 is in use (run from within backend dir)
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "Warning: Port 8000 is already in use. Killing the existing process..."
    lsof -Pi :8000 -sTCP:LISTEN -t | xargs kill -9
fi

# Run the backend server from the backend directory
echo "Starting FastAPI server from $(pwd)..."
# Use uv run to ensure the correct environment is used
# The app path is relative to the current directory (backend)
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
# Removed specific reload dirs as --reload might handle it, or add them back relative to backend:
# uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000 --reload-dir . --reload-dir app --reload-dir tools


echo "Script finished." 