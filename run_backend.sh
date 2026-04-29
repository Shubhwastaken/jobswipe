#!/bin/bash
set -e

echo "========================================"
echo "JobSwipe Backend Setup (macOS/Linux)"
echo "========================================"

cd "$(dirname "$0")/backend"
echo "Current directory: $(pwd)"

echo ""
echo "Step 1: Creating virtual environment..."
python3 -m venv venv

echo ""
echo "Step 2: Activating virtual environment..."
source venv/bin/activate

echo ""
echo "Step 3: Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "Step 4: Downloading spacy model..."
python -m spacy download en_core_web_sm

echo ""
echo "Step 5: Running database seed..."
python scripts/seed_db.py

echo ""
echo "Step 6: Starting backend server..."
echo "Backend will run on http://localhost:8000"
echo ""
echo "API Documentation will be at:"
echo "  - http://localhost:8000/docs (Interactive Swagger UI)"
echo "  - http://localhost:8000/redoc (ReDoc)"
echo ""

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
