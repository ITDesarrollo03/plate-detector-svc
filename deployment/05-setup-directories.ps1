# Create directory structure for Plate Detector service
$baseDir = "C:\inetpub\wwwroot\PlateDetector"

# Create directory structure
$directories = @(
    $baseDir,
    "$baseDir\app",
    "$baseDir\app\adapters",
    "$baseDir\app\adapters\detector",
    "$baseDir\app\adapters\extraction",
    "$baseDir\app\adapters\ocr",
    "$baseDir\app\api",
    "$baseDir\app\core",
    "$baseDir\app\domain",
    "$baseDir\app\ports",
    "$baseDir\models",
    "$baseDir\logs",
    "$baseDir\debug_plates",
    "$baseDir\venv"
)

Write-Host "Creating directory structure..." -ForegroundColor Cyan
foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "Created: $dir" -ForegroundColor Green
    } else {
        Write-Host "Exists: $dir" -ForegroundColor Yellow
    }
}

# Set permissions for IIS AppPool identity
Write-Host "`nSetting permissions for IIS AppPool identity..." -ForegroundColor Cyan
$acl = Get-Acl $baseDir
$identity = "IIS AppPool\PlateDetectorAppPool"
$permission = $identity, "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow"
$accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule $permission
$acl.SetAccessRule($accessRule)
Set-Acl $baseDir $acl

Write-Host "`nDirectory structure created and permissions set!" -ForegroundColor Green
