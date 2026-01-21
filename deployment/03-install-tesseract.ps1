# Download and install Tesseract OCR
$tesseractVersion = "5.3.3.20231005"
$installerUrl = "https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-$tesseractVersion.exe"
$installerPath = "$env:TEMP\tesseract-installer.exe"

Write-Host "Downloading Tesseract OCR $tesseractVersion..." -ForegroundColor Cyan
Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath

Write-Host "Installing Tesseract OCR..." -ForegroundColor Cyan
# Install with Spanish and English language data
Start-Process -FilePath $installerPath -ArgumentList @(
    "/S",  # Silent install
    "/D=C:\Program Files\Tesseract-OCR"
) -Wait

# Verify installation
$tesseractExe = "C:\Program Files\Tesseract-OCR\tesseract.exe"
if (Test-Path $tesseractExe) {
    Write-Host "`nTesseract installation successful:" -ForegroundColor Green
    & $tesseractExe --version

    # Verify Spanish language data
    $spaData = "C:\Program Files\Tesseract-OCR\tessdata\spa.traineddata"
    if (Test-Path $spaData) {
        Write-Host "`nSpanish language data found!" -ForegroundColor Green
    } else {
        Write-Host "`nWARNING: Spanish language data not found!" -ForegroundColor Yellow
        Write-Host "Download manually from:" -ForegroundColor Yellow
        Write-Host "https://github.com/tesseract-ocr/tessdata/raw/main/spa.traineddata" -ForegroundColor Yellow
        Write-Host "Place in: C:\Program Files\Tesseract-OCR\tessdata\" -ForegroundColor Yellow
    }
} else {
    Write-Host "`nERROR: Tesseract installation failed!" -ForegroundColor Red
}
