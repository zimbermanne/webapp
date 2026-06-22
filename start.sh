#!/bin/bash

# Shop Management System - Startup Script

echo "========================================="
echo "Shop Management System - Startup"
echo "========================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env .env
    echo "⚠️  Please update the .env file with your database credentials!"
fi

# Initialize database
echo "Initializing database..."
python init_db.py

# Start the application
echo "Starting FastAPI server..."
echo "Application will be available at: http://localhost:8000"
echo "API Documentation: http://localhost:8000/docs"
echo ""
uvicorn main:app --reload --host 0.0.0.0 --port 8000