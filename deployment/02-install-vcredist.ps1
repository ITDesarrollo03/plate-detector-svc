# Install Visual C++ Redistributable 2015-2022 (x64)
$vcRedistUrl = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
$vcRedistPath = "$env:TEMP\vc_redist.x64.exe"

Write-Host "Downloading Visual C++ Redistributable..." -ForegroundColor Cyan
Invoke-WebRequest -Uri $vcRedistUrl -OutFile $vcRedistPath

Write-Host "Installing Visual C++ Redistributable..." -ForegroundColor Cyan
Start-Process -FilePath $vcRedistPath -ArgumentList "/install", "/quiet", "/norestart" -Wait

Write-Host "`nVisual C++ Redistributable installation complete!" -ForegroundColor Green
