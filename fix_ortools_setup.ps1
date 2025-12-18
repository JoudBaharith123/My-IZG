# Fix OR-Tools Setup Script
# This script helps you set up Python 3.11 with OR-Tools

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "OR-Tools Setup Fix" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check current Python version
Write-Host "Checking current Python version..." -ForegroundColor Yellow
$currentVersion = python --version 2>&1
Write-Host "Current: $currentVersion" -ForegroundColor Gray

# Check if Python 3.11 is available
Write-Host ""
Write-Host "Checking for Python 3.11..." -ForegroundColor Yellow
$python311 = Get-Command py -ErrorAction SilentlyContinue
if ($python311) {
    $py311Version = py -3.11 --version 2>&1
    if ($py311Version -like "*3.11*") {
        Write-Host "[OK] Python 3.11 found: $py311Version" -ForegroundColor Green
        $hasPython311 = $true
    } else {
        Write-Host "[WARNING] Python 3.11 not found via 'py -3.11'" -ForegroundColor Yellow
        $hasPython311 = $false
    }
} else {
    Write-Host "[WARNING] 'py' launcher not found" -ForegroundColor Yellow
    $hasPython311 = $false
}

if (-not $hasPython311) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "Python 3.11 is required!" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "OR-Tools only supports Python 3.8-3.11" -ForegroundColor Yellow
    Write-Host "Your current version: $currentVersion" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please install Python 3.11:" -ForegroundColor Cyan
    Write-Host "1. Download from: https://www.python.org/downloads/release/python-3119/" -ForegroundColor White
    Write-Host "2. Install it (you can have multiple Python versions)" -ForegroundColor White
    Write-Host "3. Run this script again" -ForegroundColor White
    Write-Host ""
    Write-Host "After installing Python 3.11, this script will:" -ForegroundColor Gray
    Write-Host "  - Create a new virtual environment with Python 3.11" -ForegroundColor Gray
    Write-Host "  - Install all dependencies including OR-Tools" -ForegroundColor Gray
    Write-Host ""
    exit 1
}

# Ask for confirmation
Write-Host ""
Write-Host "This script will:" -ForegroundColor Yellow
Write-Host "  1. Remove the existing .venv (if it exists)" -ForegroundColor Gray
Write-Host "  2. Create a new virtual environment with Python 3.11" -ForegroundColor Gray
Write-Host "  3. Install all dependencies including OR-Tools" -ForegroundColor Gray
Write-Host ""
$confirm = Read-Host "Continue? (Y/N)"

if ($confirm -ne "Y" -and $confirm -ne "y") {
    Write-Host "Cancelled." -ForegroundColor Yellow
    exit 0
}

# Remove old venv
Write-Host ""
Write-Host "Removing old virtual environment..." -ForegroundColor Yellow
if (Test-Path .venv) {
    Remove-Item -Recurse -Force .venv
    Write-Host "[OK] Old virtual environment removed" -ForegroundColor Green
} else {
    Write-Host "[OK] No existing virtual environment to remove" -ForegroundColor Green
}

# Create new venv with Python 3.11
Write-Host ""
Write-Host "Creating new virtual environment with Python 3.11..." -ForegroundColor Yellow
py -3.11 -m venv .venv
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to create virtual environment" -ForegroundColor Red
    Write-Host "Make sure Python 3.11 is installed and accessible via 'py -3.11'" -ForegroundColor Yellow
    exit 1
}
Write-Host "[OK] Virtual environment created" -ForegroundColor Green

# Activate venv
Write-Host ""
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1

# Verify Python version
Write-Host ""
Write-Host "Verifying Python version..." -ForegroundColor Yellow
$venvVersion = python --version 2>&1
Write-Host "Virtual environment Python: $venvVersion" -ForegroundColor Gray
if ($venvVersion -notlike "*3.11*") {
    Write-Host "[WARNING] Virtual environment is not using Python 3.11!" -ForegroundColor Yellow
    Write-Host "This may cause issues with OR-Tools installation." -ForegroundColor Yellow
}

# Upgrade pip
Write-Host ""
Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet
Write-Host "[OK] pip upgraded" -ForegroundColor Green

# Install dependencies
Write-Host ""
Write-Host "Installing dependencies from requirements.txt..." -ForegroundColor Yellow
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to install dependencies" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Dependencies installed" -ForegroundColor Green

# Install OR-Tools
Write-Host ""
Write-Host "Installing OR-Tools..." -ForegroundColor Yellow
pip install ortools>=9.10.0
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to install OR-Tools" -ForegroundColor Red
    Write-Host "This may indicate a compatibility issue." -ForegroundColor Yellow
    exit 1
}
Write-Host "[OK] OR-Tools installed" -ForegroundColor Green

# Verify OR-Tools installation
Write-Host ""
Write-Host "Verifying OR-Tools installation..." -ForegroundColor Yellow
$ortoolsCheck = python -c "import ortools; print(ortools.__version__)" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] OR-Tools is installed: version $ortoolsCheck" -ForegroundColor Green
} else {
    Write-Host "[ERROR] OR-Tools verification failed" -ForegroundColor Red
    Write-Host "Output: $ortoolsCheck" -ForegroundColor Yellow
    exit 1
}

# Test import
Write-Host ""
Write-Host "Testing OR-Tools import..." -ForegroundColor Yellow
$importTest = python -c "from ortools.constraint_solver import pywrapcp; print('OK')" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] OR-Tools imports successfully" -ForegroundColor Green
} else {
    Write-Host "[ERROR] OR-Tools import failed" -ForegroundColor Red
    Write-Host "Output: $importTest" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Your virtual environment is now set up with:" -ForegroundColor Cyan
Write-Host "  - Python 3.11" -ForegroundColor White
Write-Host "  - All dependencies installed" -ForegroundColor White
Write-Host "  - OR-Tools ready to use" -ForegroundColor White
Write-Host ""
Write-Host "You can now start the backend:" -ForegroundColor Cyan
Write-Host "  .\start_backend_windows.ps1" -ForegroundColor White
Write-Host ""

