# Download and install Python 3.11.x
$pythonVersion = "3.11.9"
$installerUrl = "https://www.python.org/ftp/python/$pythonVersion/python-$pythonVersion-amd64.exe"
$installerPath = "$env:TEMP\python-installer.exe"

Write-Host "Downloading Python $pythonVersion..." -ForegroundColor Cyan
Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath

Write-Host "Installing Python $pythonVersion..." -ForegroundColor Cyan
Start-Process -FilePath $installerPath -ArgumentList @(
    "/quiet",
    "InstallAllUsers=1",
    "PrependPath=1",
    "Include_test=0",
    "Include_pip=1",
    "Include_doc=0"
) -Wait

# Verify installation
Write-Host "`nVerifying installation:" -ForegroundColor Green
python --version
pip --version

Write-Host "`nPython installation complete!" -ForegroundColor Green
