# Create IIS site and application pool for Plate Detector service
Import-Module WebAdministration

# Configuration
$siteName = "PlateDetectorService"
$appPoolName = "PlateDetectorAppPool"
$physicalPath = "C:\inetpub\wwwroot\PlateDetector"
$port = 8000

# Create Application Pool
Write-Host "Creating Application Pool: $appPoolName" -ForegroundColor Cyan
if (Test-Path "IIS:\AppPools\$appPoolName") {
    Write-Host "Application Pool already exists, removing..." -ForegroundColor Yellow
    Remove-WebAppPool -Name $appPoolName
}

New-WebAppPool -Name $appPoolName
Set-ItemProperty "IIS:\AppPools\$appPoolName" -Name managedRuntimeVersion -Value ""
Set-ItemProperty "IIS:\AppPools\$appPoolName" -Name managedPipelineMode -Value "Integrated"
Set-ItemProperty "IIS:\AppPools\$appPoolName" -Name startMode -Value "AlwaysRunning"
Set-ItemProperty "IIS:\AppPools\$appPoolName" -Name "processModel.idleTimeout" -Value ([TimeSpan]::FromMinutes(0))
Set-ItemProperty "IIS:\AppPools\$appPoolName" -Name "processModel.maxProcesses" -Value 1

Write-Host "Application Pool created successfully" -ForegroundColor Green

# Create Site
Write-Host "`nCreating IIS Site: $siteName" -ForegroundColor Cyan
if (Test-Path "IIS:\Sites\$siteName") {
    Write-Host "Site already exists, removing..." -ForegroundColor Yellow
    Remove-Website -Name $siteName
}

New-Website -Name $siteName `
    -PhysicalPath $physicalPath `
    -ApplicationPool $appPoolName `
    -Port $port `
    -HostHeader "" `
    -Protocol http `
    -IPAddress "127.0.0.1"

Write-Host "IIS Site created successfully" -ForegroundColor Green

# Configure request limits
Write-Host "`nConfiguring request limits..." -ForegroundColor Cyan
Set-WebConfigurationProperty -PSPath "IIS:\Sites\$siteName" `
    -Filter "system.webServer/security/requestFiltering/requestLimits" `
    -Name "maxAllowedContentLength" `
    -Value 52428800

# Start the site
Write-Host "`nStarting website..." -ForegroundColor Cyan
Start-Website -Name $siteName

Write-Host "`n=== IIS Site Configuration Complete ===" -ForegroundColor Green
Write-Host "Site Name: $siteName" -ForegroundColor White
Write-Host "Site URL: http://localhost:$port" -ForegroundColor White
Write-Host "Physical Path: $physicalPath" -ForegroundColor White
Write-Host "Application Pool: $appPoolName" -ForegroundColor White
