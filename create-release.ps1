# Script para crear paquete de release
$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$releaseDir = Join-Path $projectRoot "release\PlateDetector-Release-$timestamp"
$zipFile = Join-Path $projectRoot "release\PlateDetector-Release-$timestamp.zip"

Write-Host "=== Creando Release Package ===" -ForegroundColor Cyan

# Crear directorio
New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null

# Copiar archivos
Write-Host "Copiando archivos..." -ForegroundColor Cyan
Copy-Item -Path "$projectRoot\app" -Destination "$releaseDir\app" -Recurse -Force
Copy-Item -Path "$projectRoot\models" -Destination "$releaseDir\models" -Recurse -Force -ErrorAction SilentlyContinue
Copy-Item -Path "$projectRoot\deployment" -Destination "$releaseDir\deployment" -Recurse -Force
Copy-Item -Path "$projectRoot\web.config" -Destination "$releaseDir\" -Force
Copy-Item -Path "$projectRoot\requirements-windows.txt" -Destination "$releaseDir\" -Force
Copy-Item -Path "$projectRoot\CLAUDE.md" -Destination "$releaseDir\" -Force -ErrorAction SilentlyContinue

# Limpiar
Get-ChildItem -Path $releaseDir -Recurse -Include "__pycache__","*.pyc" -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Copiar README
$readmeTemplate = Get-Content "$projectRoot\deployment\README-TEMPLATE.txt" -Raw
$readmeContent = $readmeTemplate.Replace("VERSION_PLACEHOLDER", $timestamp).Replace("TIMESTAMP_PLACEHOLDER", $timestamp)
Set-Content -Path "$releaseDir\README.txt" -Value $readmeContent -Encoding UTF8

# version.json
$versionContent = @{
    version = "1.0.0"
    buildDate = $timestamp
} | ConvertTo-Json
Set-Content -Path "$releaseDir\version.json" -Value $versionContent

# Comprimir
Write-Host "Creando ZIP..." -ForegroundColor Cyan
Compress-Archive -Path $releaseDir -DestinationPath $zipFile -Force

# Resultado
$zipSize = (Get-Item $zipFile).Length / 1MB
Write-Host "`n=== RELEASE CREADO ===" -ForegroundColor Green
Write-Host "Archivo: $zipFile" -ForegroundColor White
Write-Host "Tamaño: $([math]::Round($zipSize, 2)) MB" -ForegroundColor White
