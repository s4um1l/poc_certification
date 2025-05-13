#!/bin/bash

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "Installing requirements..."
pip install -r backend/requirements.txt

# Generate data if it doesn't exist
if [ ! -f "backend/data/products.csv" ]; then
    echo "Generating synthetic data..."
    cd backend && python data_generator.py
    cd ..
fi

# Run the backend server
echo "Starting FastAPI server..."
cd backend && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 