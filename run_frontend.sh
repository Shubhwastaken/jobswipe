#!/bin/bash
set -e

echo "========================================"
echo "JobSwipe Frontend Setup (macOS/Linux)"
echo "========================================"

cd "$(dirname "$0")/frontend"
echo "Current directory: $(pwd)"

echo ""
echo "Step 1: Installing npm dependencies..."
npm install

echo ""
echo "Step 2: Starting development server..."
echo "Frontend will run on http://localhost:3000"
echo ""

npm run dev
