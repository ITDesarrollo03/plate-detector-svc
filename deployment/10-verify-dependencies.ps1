# Verify all dependencies are installed correctly
Write-Host "=== Dependency Verification ===" -ForegroundColor Cyan

# Python
Write-Host "`n[Python]" -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Python not found!" -ForegroundColor Red
}

# Tesseract
Write-Host "`n[Tesseract OCR]" -ForegroundColor Yellow
$tesseractExe = "C:\Program Files\Tesseract-OCR\tesseract.exe"
if (Test-Path $tesseractExe) {
    $version = & $tesseractExe --version 2>&1 | Select-Object -First 1
    Write-Host "  $version" -ForegroundColor Green

    # Check language data
    $engData = "C:\Program Files\Tesseract-OCR\tessdata\eng.traineddata"
    $spaData = "C:\Program Files\Tesseract-OCR\tessdata\spa.traineddata"

    if (Test-Path $engData) {
        Write-Host "  English data: OK" -ForegroundColor Green
    } else {
        Write-Host "  English data: MISSING" -ForegroundColor Red
    }

    if (Test-Path $spaData) {
        Write-Host "  Spanish data: OK" -ForegroundColor Green
    } else {
        Write-Host "  Spanish data: MISSING" -ForegroundColor Red
        Write-Host "  Download from: https://github.com/tesseract-ocr/tessdata/raw/main/spa.traineddata" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ERROR: Tesseract not found!" -ForegroundColor Red
}

# Visual C++ Redistributable
Write-Host "`n[Visual C++ Redistributable]" -ForegroundColor Yellow
$vcRedist = Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" -ErrorAction SilentlyContinue
if ($vcRedist) {
    Write-Host "  Installed: Yes" -ForegroundColor Green
    Write-Host "  Version: $($vcRedist.Version)" -ForegroundColor White
} else {
    Write-Host "  Not found or not registered" -ForegroundColor Yellow
}

# HttpPlatformHandler
Write-Host "`n[HttpPlatformHandler]" -ForegroundColor Yellow
try {
    Import-Module WebAdministration -ErrorAction Stop
    $hphModule = Get-WebGlobalModule -Name httpPlatformHandler -ErrorAction SilentlyContinue
    if ($hphModule) {
        Write-Host "  Installed: OK" -ForegroundColor Green
    } else {
        Write-Host "  Not installed!" -ForegroundColor Red
    }
} catch {
    Write-Host "  ERROR: Cannot check (IIS not available?)" -ForegroundColor Red
}

# Python packages (in venv)
Write-Host "`n[Python Packages in Virtual Environment]" -ForegroundColor Yellow
$venvPython = "C:\inetpub\wwwroot\PlateDetector\venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    & $venvPython -c @"
import sys
packages = ['torch', 'cv2', 'ultralytics', 'pytesseract', 'fastapi', 'uvicorn', 'numpy']
for pkg in packages:
    try:
        mod = __import__(pkg)
        version = getattr(mod, '__version__', 'unknown')
        print(f'  {pkg}: {version}')
    except ImportError:
        print(f'  {pkg}: NOT INSTALLED')
"@
} else {
    Write-Host "  ERROR: Virtual environment not found!" -ForegroundColor Red
    Write-Host "  Expected at: C:\inetpub\wwwroot\PlateDetector\venv" -ForegroundColor Yellow
}

# Deployment directories
Write-Host "`n[Deployment Directories]" -ForegroundColor Yellow
$directories = @(
    "C:\inetpub\wwwroot\PlateDetector\app",
    "C:\inetpub\wwwroot\PlateDetector\models",
    "C:\inetpub\wwwroot\PlateDetector\logs",
    "C:\inetpub\wwwroot\PlateDetector\debug_plates",
    "C:\inetpub\wwwroot\PlateDetector\venv"
)
foreach ($dir in $directories) {
    if (Test-Path $dir) {
        Write-Host "  $dir : OK" -ForegroundColor Green
    } else {
        Write-Host "  $dir : MISSING" -ForegroundColor Red
    }
}

# YOLO Model
Write-Host "`n[YOLO Model]" -ForegroundColor Yellow
$modelPath = "C:\inetpub\wwwroot\PlateDetector\models\plate-detector.pt"
if (Test-Path $modelPath) {
    $modelSize = (Get-Item $modelPath).Length / 1MB
    Write-Host "  Model file: OK ($([math]::Round($modelSize, 2)) MB)" -ForegroundColor Green
} else {
    Write-Host "  Model file: MISSING" -ForegroundColor Red
}

Write-Host "`n=== Verification Complete ===" -ForegroundColor Cyan
