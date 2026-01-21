# Setup virtual environment and install dependencies
$baseDir = "C:\inetpub\wwwroot\PlateDetector"
$venvDir = "$baseDir\venv"

# Create virtual environment
Write-Host "Creating Python virtual environment..." -ForegroundColor Cyan
python -m venv $venvDir

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Cyan
& "$venvDir\Scripts\Activate.ps1"

# Upgrade pip
Write-Host "`nUpgrading pip..." -ForegroundColor Cyan
& "$venvDir\Scripts\python.exe" -m pip install --upgrade pip

# Install dependencies
Write-Host "`nInstalling Python dependencies (this may take 5-10 minutes)..." -ForegroundColor Cyan
& "$venvDir\Scripts\pip.exe" install -r "$baseDir\requirements-windows.txt" --default-timeout=300 --retries=15

# Verify critical packages
Write-Host "`n=== Verifying installations ===" -ForegroundColor Green
& "$venvDir\Scripts\python.exe" -c @"
import torch
import cv2
import ultralytics
import pytesseract
import fastapi
import uvicorn

print(f'PyTorch: {torch.__version__} (CPU only: {not torch.cuda.is_available()})')
print(f'OpenCV: {cv2.__version__}')
print(f'Ultralytics: {ultralytics.__version__}')
print(f'pytesseract: OK')
print(f'FastAPI: {fastapi.__version__}')
print(f'Uvicorn: {uvicorn.__version__}')
"@

Write-Host "`nVirtual environment setup complete!" -ForegroundColor Green
