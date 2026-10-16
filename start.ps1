param(
  [int]$BackendPort = 8015,
  [int]$FrontendPort = 3025,
  [switch]$OpenBrowser
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$python = Join-Path $backend ".venv\Scripts\python.exe"

foreach ($port in @($BackendPort, $FrontendPort)) {
  if (Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue) {
    throw "Port $port is already in use. Choose another port with -BackendPort or -FrontendPort."
  }
}

if (-not (Test-Path $python)) {
  $creator = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
  Push-Location $backend
  try {
    if ($creator -eq "py") { & py -3.12 -m venv .venv } else { & python -m venv .venv }
    if ($LASTEXITCODE -ne 0) { throw "Python 3.12 virtual environment creation failed." }
  } finally { Pop-Location }
}

& $python -c "import fastapi, docx, pypdf, openpyxl" 2>$null
if ($LASTEXITCODE -ne 0) {
  & $python -m pip install -r (Join-Path $backend "requirements.txt")
  if ($LASTEXITCODE -ne 0) { throw "Backend dependency installation failed." }
}

Push-Location $frontend
try {
  if (-not (Test-Path "node_modules")) {
    npm.cmd ci
    if ($LASTEXITCODE -ne 0) { throw "Frontend dependency installation failed." }
  }
  $env:NEXT_PUBLIC_API_BASE_URL = "http://127.0.0.1:$BackendPort"
  if (-not (Test-Path (Join-Path $frontend ".next\BUILD_ID"))) {
    npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw "Frontend build failed." }
  }
} finally { Pop-Location }

$env:TALENTNET_DATABASE_URL = "sqlite:///./talentnet-local-demo.db"
$backendProcess = Start-Process -FilePath $python -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$BackendPort" -WorkingDirectory $backend -PassThru -WindowStyle Hidden
$frontendProcess = $null
Write-Host "TalentNet: http://127.0.0.1:$FrontendPort"
Write-Host "API health: http://127.0.0.1:$BackendPort/api/health"
Write-Host "Press Ctrl+C to stop both services."

try {
  $frontendProcess = Start-Process -FilePath "npm.cmd" -ArgumentList "run", "start", "--", "--hostname", "127.0.0.1", "--port", "$FrontendPort" -WorkingDirectory $frontend -PassThru -WindowStyle Hidden

  $deadline = (Get-Date).AddSeconds(30)
  $frontendReady = $false
  while ((Get-Date) -lt $deadline) {
    try {
      $response = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$FrontendPort" -TimeoutSec 2
      if ($response.StatusCode -eq 200) {
        $frontendReady = $true
        break
      }
    } catch { }
    Start-Sleep -Milliseconds 500
  }
  if (-not $frontendReady) { throw "Frontend did not become ready on port $FrontendPort." }

  if ($OpenBrowser) {
    Start-Process "http://127.0.0.1:$FrontendPort"
  }

  Wait-Process -Id $frontendProcess.Id
} finally {
  if ($frontendProcess) { Stop-Process -Id $frontendProcess.Id -Force -ErrorAction SilentlyContinue }
  Stop-Process -Id $backendProcess.Id -Force -ErrorAction SilentlyContinue
}
