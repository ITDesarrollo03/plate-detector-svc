# Deploy application files to C:\PlateDetector
# Run this script from the project root directory
$sourceDir = "." # Current directory (project root)
$targetDir = "C:\inetpub\wwwroot\PlateDetector"

Write-Host "Deploying application files..." -ForegroundColor Cyan

# Copy application files
Write-Host "`nCopying app directory..." -ForegroundColor Cyan
if (Test-Path "$sourceDir\app") {
    Copy-Item -Path "$sourceDir\app\*" -Destination "$targetDir\app\" -Recurse -Force
    Write-Host "App directory copied" -ForegroundColor Green
} else {
    Write-Host "ERROR: app directory not found!" -ForegroundColor Red
    exit 1
}

# Copy models
Write-Host "`nCopying models directory..." -ForegroundColor Cyan
if (Test-Path "$sourceDir\models") {
    Copy-Item -Path "$sourceDir\models\*" -Destination "$targetDir\models\" -Force
    Write-Host "Models directory copied" -ForegroundColor Green
} else {
    Write-Host "WARNING: models directory not found!" -ForegroundColor Yellow
}

# Copy configuration files
Write-Host "`nCopying configuration files..." -ForegroundColor Cyan
$configFiles = @("requirements-windows.txt", "web.config")
foreach ($file in $configFiles) {
    if (Test-Path "$sourceDir\$file") {
        Copy-Item -Path "$sourceDir\$file" -Destination "$targetDir\" -Force
        Write-Host "Copied: $file" -ForegroundColor Green
    } else {
        Write-Host "WARNING: $file not found!" -ForegroundColor Yellow
    }
}

# Verify model file
$modelPath = "$targetDir\models\plate-detector.pt"
if (Test-Path $modelPath) {
    $modelSize = (Get-Item $modelPath).Length / 1MB
    Write-Host "`nModel file deployed: $([math]::Round($modelSize, 2)) MB" -ForegroundColor Green
} else {
    Write-Host "`nERROR: Model file missing!" -ForegroundColor Red
}

Write-Host "`nApplication deployment complete!" -ForegroundColor Green
