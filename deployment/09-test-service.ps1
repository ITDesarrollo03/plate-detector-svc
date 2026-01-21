# Test Plate Detector Service endpoints
$baseUrl = "http://localhost:8000"

Write-Host "=== Testing Plate Detector Service ===" -ForegroundColor Cyan

# Test 1: Health check (FastAPI docs)
Write-Host "`n[Test 1] Accessing API documentation..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/docs" -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "PASS: API docs accessible" -ForegroundColor Green
    }
} catch {
    Write-Host "FAIL: API docs not accessible - $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: Debug endpoint
Write-Host "`n[Test 2] Testing debug endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/debug/test" -Method Get
    if ($response.status -eq "ok") {
        Write-Host "PASS: Debug endpoint working" -ForegroundColor Green
        Write-Host "Response: $($response.message)" -ForegroundColor White
    }
} catch {
    Write-Host "FAIL: Debug endpoint failed - $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: Debug images list
Write-Host "`n[Test 3] Testing debug images list..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/debug/images" -Method Get
    Write-Host "PASS: Debug images endpoint working" -ForegroundColor Green
    Write-Host "Directory: $($response.directory)" -ForegroundColor White
    Write-Host "Files count: $($response.count)" -ForegroundColor White
} catch {
    Write-Host "FAIL: Debug images endpoint failed - $($_.Exception.Message)" -ForegroundColor Red
}

# Test 4: Root endpoint (redirect to docs)
Write-Host "`n[Test 4] Testing root endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri $baseUrl -UseBasicParsing -MaximumRedirection 0 -ErrorAction SilentlyContinue
    if ($response.StatusCode -in @(200, 307, 404)) {
        Write-Host "PASS: Root endpoint responding" -ForegroundColor Green
    }
} catch {
    if ($_.Exception.Response.StatusCode -eq 307) {
        Write-Host "PASS: Root endpoint redirecting to docs" -ForegroundColor Green
    } else {
        Write-Host "INFO: Root endpoint returned $($_.Exception.Response.StatusCode)" -ForegroundColor Yellow
    }
}

Write-Host "`n=== Testing Complete ===" -ForegroundColor Cyan
Write-Host "`nNOTE: To test plate detection endpoints, you need to provide test images." -ForegroundColor Yellow
Write-Host "Test images can be uploaded via:" -ForegroundColor Yellow
Write-Host "  - POST /detect" -ForegroundColor White
Write-Host "  - POST /ocr" -ForegroundColor White
Write-Host "  - POST /extract-info" -ForegroundColor White
Write-Host "  - POST /dni/extract" -ForegroundColor White
Write-Host "  - POST /license/extract" -ForegroundColor White
