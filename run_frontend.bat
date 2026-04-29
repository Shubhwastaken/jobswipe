@echo off
echo ========================================
echo JobSwipe Frontend Setup (Windows)
echo ========================================

cd /d "%~dp0frontend"
echo Current directory: %cd%

echo.
echo Step 1: Installing npm dependencies...
call npm install
if errorlevel 1 (
    echo ERROR: Failed to install npm packages
    exit /b 1
)

echo.
echo Step 2: Starting development server...
echo Frontend will run on http://localhost:3000
echo.

call npm run dev

pause
