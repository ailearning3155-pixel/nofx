@echo off
REM ============================================================
REM APEX Trading OS — Windows Installation Script
REM Run this instead of "pip install -r requirements.txt"
REM ============================================================

echo.
echo ==========================================
echo   APEX Trading OS - Installing packages
echo ==========================================
echo.

REM Check Python
python --version 2>NUL
if errorlevel 1 (
    echo ERROR: Python not found. Install from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo.
echo Step 1/4 - Installing core packages...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Core install failed. Check the error above.
    pause
    exit /b 1
)

echo.
echo Step 2/4 - Installing pandas-ta...
pip install "pandas-ta==0.3.14b0"
if errorlevel 1 (
    echo   Note: pandas-ta failed. The 'ta' package will be used instead.
    echo   All indicators still work via core/indicators.py
)

echo.
echo Step 3/4 - Installing PyTorch (CPU version)...
pip install torch --index-url https://download.pytorch.org/whl/cpu
if errorlevel 1 (
    echo   Note: PyTorch install failed. VADER will be used for news sentiment.
)

echo.
echo Step 4/4 - Checking imports...
python -c "import fastapi, sqlalchemy, oandapyV20, openai, anthropic, pandas, ta; print('  Core packages OK')"

echo.
echo ==========================================
echo   Installation complete!
echo.
echo   Next steps:
echo   1. copy .env.example .env
echo   2. Edit .env with your API keys
echo   3. docker-compose up -d postgres redis
echo   4. python scripts\migrate.py
echo   5. uvicorn api.main:app --reload
echo   6. cd web ^&^& npm install ^&^& npm run dev
echo.
echo   Full guide: GETTING_STARTED.md
echo ==========================================
echo.
pause
