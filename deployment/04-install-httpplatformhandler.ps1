# Download and install HttpPlatformHandler
$hphVersion = "1.2"
$installerUrl = "https://download.microsoft.com/download/C/F/F/CFF3A0B8-99D4-41A2-AE1A-496C08BEB904/HttpPlatformHandler_amd64.msi"
$installerPath = "$env:TEMP\HttpPlatformHandler.msi"

Write-Host "Downloading HttpPlatformHandler v$hphVersion..." -ForegroundColor Cyan
Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath

Write-Host "Installing HttpPlatformHandler..." -ForegroundColor Cyan
Start-Process msiexec.exe -ArgumentList "/i", $installerPath, "/quiet", "/norestart" -Wait

# Restart IIS to load the module
Write-Host "`nRestarting IIS..." -ForegroundColor Cyan
iisreset /restart

Write-Host "`nHttpPlatformHandler installation complete!" -ForegroundColor Green
