# ============================================
# PHOBICS — Automated Build Script
# Creates a portable EXE with full asset support
# Saves are created next to the EXE (not bundled)
# ============================================

Write-Host "=== PHOBICS BUILD SCRIPT STARTED ===" -ForegroundColor Cyan

# Ensure script runs from its own directory
Set-Location -Path $PSScriptRoot

# ---------------------------
# 1. Clean old build folders
# ---------------------------
Write-Host "Cleaning old build directories..." -ForegroundColor Yellow
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "__pycache__") { Remove-Item -Recurse -Force "__pycache__" }

# ---------------------------
# 2. Ensure PyInstaller exists
# ---------------------------
Write-Host "Checking PyInstaller..." -ForegroundColor Yellow
pip show pyinstaller > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller not found. Installing..." -ForegroundColor Green
    pip install pyinstaller
}

# ---------------------------
# 3. Run PyInstaller Build
# ---------------------------
Write-Host "Building EXE..." -ForegroundColor Yellow

pyinstaller --noconfirm --onefile --windowed `
    --add-data "assets;assets" `
    phobics_rebuilt.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed. See PyInstaller errors." -ForegroundColor Red
    exit
}

# ---------------------------
# 4. Create release folder
# ---------------------------
Write-Host "Creating release package..." -ForegroundColor Yellow

$release = "PHOBICS_Release"
if (Test-Path $release) { Remove-Item -Recurse -Force $release }

New-Item -ItemType Directory -Path $release | Out-Null

# Copy EXE
Copy-Item "dist\phobics_rebuilt.exe" -Destination $release

# Copy assets for the game to use
Copy-Item "assets" -Destination $release -Recurse

# Saves folder will be created automatically when game runs

Write-Host "Release folder created: $release" -ForegroundColor Green

Write-Host "=== BUILD COMPLETE ===" -ForegroundColor Cyan
