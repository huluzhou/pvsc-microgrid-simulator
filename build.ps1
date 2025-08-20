# PandaPower Build Tool - PowerShell Version
Write-Host "================================" -ForegroundColor Cyan
Write-Host " PandaPower Build Tool" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Checking conda environment..." -ForegroundColor Yellow

# Test if conda is available
try {
    $condaVersion = conda --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Found conda version: $condaVersion" -ForegroundColor Green
    } else {
        throw "Conda command failed"
    }
} catch {
    Write-Host "ERROR: conda command not found or failed." -ForegroundColor Red
    Write-Host ""
    Write-Host "This usually happens when conda is not installed or not properly configured." -ForegroundColor Yellow
    Write-Host "You can try one of the following solutions:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "1. Install miniforge (recommended, lightweight conda distribution):" -ForegroundColor White
    Write-Host "   Download from: https://github.com/conda-forge/miniforge/releases" -ForegroundColor Cyan
    Write-Host "   After installation, restart PowerShell and run:" -ForegroundColor Gray
    Write-Host "   conda env create -f environment.yml" -ForegroundColor Cyan
    Write-Host "   conda activate pandapower_sim" -ForegroundColor Cyan
    Write-Host "   Note: Virtual environment installation may take 10-15 minutes" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "2. Alternative: Use Anaconda/Miniconda:" -ForegroundColor White
    Write-Host "   https://www.anaconda.com/products/distribution" -ForegroundColor Cyan
    Write-Host "   https://docs.conda.io/en/latest/miniconda.html" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "3. Run this script from Anaconda PowerShell Prompt" -ForegroundColor White
    Write-Host ""
    Write-Host "4. Initialize conda for PowerShell by running:" -ForegroundColor White
    Write-Host "   conda init powershell" -ForegroundColor Cyan
    Write-Host "   (then restart PowerShell)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Press any key to exit..." -ForegroundColor Yellow
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

Write-Host ""
Write-Host "Activating pandapower_sim environment..." -ForegroundColor Yellow

try {
    conda activate pandapower_sim 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "WARNING: Cannot activate pandapower_sim environment" -ForegroundColor Yellow
        Write-Host "Please run: conda env create -f environment.yml" -ForegroundColor Cyan
        Write-Host "Note: environment.yml includes PyInstaller and all dependencies" -ForegroundColor Gray
        Write-Host ""
    }
} catch {
    Write-Host "WARNING: Failed to activate environment" -ForegroundColor Yellow
}

Write-Host "Checking Python environment..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Found Python: $pythonVersion" -ForegroundColor Green
    } else {
        throw "Python command failed"
    }
} catch {
    Write-Host "ERROR: Python not found" -ForegroundColor Red
    Write-Host "Press any key to exit..." -ForegroundColor Yellow
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

Write-Host ""
Write-Host "Starting build process..." -ForegroundColor Yellow

try {
    python build.py
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "Build SUCCESS!" -ForegroundColor Green
        Write-Host "Executable location: dist\pandapower_sim.exe" -ForegroundColor Cyan
    } else {
        Write-Host ""
        Write-Host "Build FAILED. Please check error messages above." -ForegroundColor Red
    }
} catch {
    Write-Host ""
    Write-Host "Build FAILED. Please check error messages above." -ForegroundColor Red
}

Write-Host ""
Write-Host "Press any key to exit..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")