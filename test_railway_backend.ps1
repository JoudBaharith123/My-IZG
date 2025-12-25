# Railway Backend Diagnostic Script
$railwayUrl = "https://intelligentzonegenerator-production.up.railway.app"

Write-Host ""
Write-Host "Railway Backend Diagnostic Test" -ForegroundColor Cyan
Write-Host "Target URL: $railwayUrl"
Write-Host ""

function Test-Endpoint {
    param(
        [string]$Path,
        [string]$Description
    )
    
    $url = "$railwayUrl$Path"
    Write-Host "============================================================" -ForegroundColor Gray
    Write-Host "Testing: $Description" -ForegroundColor Yellow
    Write-Host "URL: $url" -ForegroundColor Yellow
    Write-Host "============================================================" -ForegroundColor Gray
    
    try {
        $response = Invoke-WebRequest -Uri $url -Method Get -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
        
        Write-Host "SUCCESS - Status Code: $($response.StatusCode)" -ForegroundColor Green
        
        try {
            $json = $response.Content | ConvertFrom-Json
            Write-Host "Response Body (JSON):" -ForegroundColor Green
            $response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 5
        } catch {
            Write-Host "Response Body (Text - first 500 chars):" -ForegroundColor Green
            if ($response.Content.Length -gt 500) {
                Write-Host $response.Content.Substring(0, 500)
            } else {
                Write-Host $response.Content
            }
        }
        
        return $true, $response.StatusCode
    }
    catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        $errorMessage = $_.Exception.Message
        
        if ($statusCode) {
            Write-Host "FAILED - HTTP Error: Status Code $statusCode" -ForegroundColor Red
            Write-Host "Error: $errorMessage" -ForegroundColor Red
            return $false, $statusCode
        }
        else {
            Write-Host "FAILED - Connection Error: $errorMessage" -ForegroundColor Red
            return $false, $null
        }
    }
}

# Test endpoints
$rootSuccess, $rootStatus = Test-Endpoint -Path "/" -Description "Root Endpoint"
$healthSuccess, $healthStatus = Test-Endpoint -Path "/api/health" -Description "Health Endpoint"
$osrmSuccess, $osrmStatus = Test-Endpoint -Path "/api/health/osrm" -Description "OSRM Health Endpoint"
$docsSuccess, $docsStatus = Test-Endpoint -Path "/docs" -Description "API Documentation"

# Summary
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "SUMMARY" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Root (/):            $(if ($rootSuccess) { 'PASS' } else { 'FAIL' }) - Status: $rootStatus"
Write-Host "Health (/api/health): $(if ($healthSuccess) { 'PASS' } else { 'FAIL' }) - Status: $healthStatus"
Write-Host "OSRM Health:         $(if ($osrmSuccess) { 'PASS' } else { 'FAIL' }) - Status: $osrmStatus"
Write-Host "Docs (/docs):        $(if ($docsSuccess) { 'PASS' } else { 'FAIL' }) - Status: $docsStatus"

if (-not ($rootSuccess -or $healthSuccess -or $osrmSuccess -or $docsSuccess)) {
    Write-Host ""
    Write-Host "ALL TESTS FAILED - Backend is not accessible" -ForegroundColor Red
    Write-Host ""
    Write-Host "Possible issues:" -ForegroundColor Yellow
    Write-Host "1. Backend is not running or crashed"
    Write-Host "2. Railway networking configuration issue"
    Write-Host "3. DNS/URL routing problem"
    Write-Host "4. Firewall or security group blocking access"
    Write-Host "5. Railway proxy configuration issue - 502 Bad Gateway"
}
elseif ($healthSuccess) {
    Write-Host ""
    Write-Host "Backend is accessible and responding!" -ForegroundColor Green
}
else {
    Write-Host ""
    Write-Host "Partial connectivity - some endpoints work, others do not" -ForegroundColor Yellow
}
