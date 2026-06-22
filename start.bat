@echo off
REM Shop Management System - Windows Startup Script

echo =========================================
echo Shop Management System - Startup
echo =========================================

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Check if .env exists
if not exist ".env" (
    echo .env file already exists (it was created during setup)
    echo Make sure to update it with your database credentials!
)

REM Initialize database
echo Initializing database...
python init_db.py

REM Start the application
echo Starting FastAPI server...
echo Application will be available at: http://localhost:8000
echo API Documentation: http://localhost:8000/docs
echo.
uvicorn main:app --reload --host 0.0.0.0 --port 8000