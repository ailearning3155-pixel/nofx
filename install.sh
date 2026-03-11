#!/bin/bash
# ============================================================
# APEX Trading OS — Installation Script
# Handles the packages that pip install -r requirements.txt
# can't install cleanly on its own.
#
# Usage:
#   chmod +x install.sh
#   ./install.sh
# ============================================================

set -e   # stop on first error

echo ""
echo "=========================================="
echo "  APEX Trading OS — Installing packages  "
echo "=========================================="
echo ""

# Check Python version
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Python version: $PYTHON_VERSION"

MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")

if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 10 ]); then
    echo ""
    echo "ERROR: APEX requires Python 3.10 or higher."
    echo "Your version: $PYTHON_VERSION"
    echo "Please upgrade Python and try again."
    echo ""
    exit 1
fi

echo ""
echo "Step 1/4 — Installing core packages..."
pip install -r requirements.txt

echo ""
echo "Step 2/4 — Installing pandas-ta (technical indicators)..."
# pandas-ta has a weird version string on PyPI — must specify exactly
pip install "pandas-ta==0.3.14b0" || {
    echo ""
    echo "  Note: pandas-ta failed (common on Python 3.12+)."
    echo "  Falling back to 'ta' package which is already installed."
    echo "  All indicators will still work via core/indicators.py"
    echo ""
}

echo ""
echo "Step 3/4 — Installing PyTorch (for FinBERT sentiment)..."
echo "  Installing CPU-only version (smaller download)..."
pip install torch --index-url https://download.pytorch.org/whl/cpu || {
    echo ""
    echo "  Note: PyTorch install failed or skipped."
    echo "  News sentiment will use VADER instead of FinBERT."
    echo "  This is fine — VADER works well for financial news."
    echo ""
}

echo ""
echo "Step 4/4 — Verifying critical imports..."
python3 -c "
packages = [
    ('fastapi',        'FastAPI web framework'),
    ('sqlalchemy',     'Database ORM'),
    ('oandapyV20',     'OANDA API client'),
    ('openai',         'OpenAI / DeepSeek / Grok client'),
    ('anthropic',      'Claude client'),
    ('google.generativeai', 'Gemini client'),
    ('pandas',         'Data processing'),
    ('ta',             'Technical indicators (ta)'),
    ('redis',          'Redis client'),
    ('telegram',       'Telegram bot'),
    ('loguru',         'Logging'),
    ('pydantic_settings', 'Settings management'),
]
ok = []
fail = []
for pkg, desc in packages:
    try:
        __import__(pkg)
        ok.append(f'  OK  {desc}')
    except ImportError:
        fail.append(f'  MISSING  {pkg} ({desc})')

for line in ok:
    print(line)
if fail:
    print()
    print('  WARNING — Some packages missing:')
    for line in fail:
        print(line)
else:
    print()
    print('  All critical packages installed successfully!')
"

echo ""
echo "=========================================="
echo "  Installation complete!"
echo ""
echo "  Next steps:"
echo "  1. cp .env.example .env"
echo "  2. Edit .env — add your OANDA key + AI key"
echo "  3. docker-compose up -d postgres redis"
echo "  4. python scripts/migrate.py"
echo "  5. uvicorn api.main:app --reload"
echo "  6. cd web && npm install && npm run dev"
echo ""
echo "  Full guide: GETTING_STARTED.md"
echo "=========================================="
echo ""
