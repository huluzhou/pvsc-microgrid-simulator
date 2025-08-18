@echo off
echo ================================
echo PandaPower Build Tool
echo ================================
echo.

echo Checking conda environment...
conda --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: conda not found. Please install Anaconda/Miniconda
    pause
    exit /b 1
)

echo Activating pandapower_sim environment...
call conda activate pandapower_sim
if errorlevel 1 (
    echo WARNING: Cannot activate pandapower_sim environment
    echo Please run: conda env create -f environment.yml
    echo Note: environment.yml includes PyInstaller and all dependencies
    echo.
)

echo Checking Python environment...
python --version
if errorlevel 1 (
    echo ERROR: Python not found
    pause
    exit /b 1
)

echo.
echo Starting build process...
python build.py

if errorlevel 1 (
    echo.
    echo Build FAILED. Please check error messages above.
) else (
    echo.
    echo Build SUCCESS!
    echo Executable location: dist\pandapower_sim.exe
)

echo.
echo Press any key to exit...
pause >nul