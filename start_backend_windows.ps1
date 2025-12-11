# Start IZG Backend on Windows
# Usage: .\start_backend_windows.ps1

Write-Host "🚀 Starting Intelligent Zone Generator Backend..." -ForegroundColor Cyan
Write-Host ""

# Check if venv exists
if (-not (Test-Path ".venv")) {
    Write-Host "❌ Virtual environment not found at .venv" -ForegroundColor Red
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
    Write-Host "✅ Virtual environment created" -ForegroundColor Green
}

# Activate venv
Write-Host "🔧 Activating virtual environment..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1

# Check if dependencies are installed
Write-Host "📦 Checking dependencies..." -ForegroundColor Yellow
$checkDeps = python -c "import fastapi, uvicorn, pydantic, numpy, sklearn, shapely, httpx, openpyxl; print('OK')" 2>&1

if ($checkDeps -notlike "*OK*") {
    Write-Host "⚙️ Installing dependencies..." -ForegroundColor Yellow
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    
    # Try to install ortools separately (optional, may fail on Python 3.12+)
    Write-Host "📦 Attempting to install OR-Tools (optional for routing)..." -ForegroundColor Yellow
    $ortoolsResult = python -m pip install ortools 2>&1
    if ($ortoolsResult -like "*ERROR*" -or $ortoolsResult -like "*No matching*") {
        Write-Host "⚠️  OR-Tools not installed (requires Python 3.8-3.11)" -ForegroundColor Yellow
        Write-Host "   Routing features will be unavailable, but zoning will work fine." -ForegroundColor Yellow
    } else {
        Write-Host "✅ OR-Tools installed successfully" -ForegroundColor Green
    }
    
    Write-Host "✅ Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "✅ Dependencies already installed" -ForegroundColor Green
}

# Set PYTHONPATH
$env:PYTHONPATH = "$PWD\src;$env:PYTHONPATH"
Write-Host "✅ PYTHONPATH set to: $env:PYTHONPATH" -ForegroundColor Green

# Start server on port 8001 (avoiding conflict with port 8000)
Write-Host ""
Write-Host "🌐 Starting uvicorn server on http://0.0.0.0:8001" -ForegroundColor Cyan
Write-Host "📡 API docs available at http://localhost:8001/docs" -ForegroundColor Cyan
Write-Host "📡 Frontend should use: http://localhost:8001/api" -ForegroundColor Cyan
Write-Host ""
Write-Host "⚠️ NOTE: Running on PORT 8001 (not 8000) to avoid conflicts" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Gray
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host ""

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

