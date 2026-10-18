# Starts the LeRobot Plug & Play backend + frontend together (Windows).
# Run via start.bat, or: powershell -ExecutionPolicy Bypass -File start.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# Prefer the "py" launcher; plain "python" may be the Microsoft Store stub that just opens the Store.
$python = $null
$pythonArgs = @()
if (Get-Command py -ErrorAction SilentlyContinue) {
    $python = "py"; $pythonArgs = @("-3")
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    try { if ((& python -c "print(1)") -eq "1") { $python = "python" } } catch {}
}

$missing = $false
if (-not $python) { Write-Host "Python not found - install Python 3.10+ from https://www.python.org/downloads/ (tick 'Add python.exe to PATH')." -ForegroundColor Red; $missing = $true }
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { Write-Host "node not found - install Node.js 18+ from https://nodejs.org/ first." -ForegroundColor Red; $missing = $true }
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) { Write-Host "npm not found - it ships with Node.js, install Node.js 18+ from https://nodejs.org/ first." -ForegroundColor Red; $missing = $true }
if ($missing) { exit 1 }

$venvPython = "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "Setting up backend\.venv (first run only)..."
    & $python @pythonArgs -m venv backend\.venv
    if ($LASTEXITCODE -ne 0) { exit 1 }
    & $venvPython -m pip install -q --upgrade pip
    & $venvPython -m pip install -q -r backend\requirements.txt
    if ($LASTEXITCODE -ne 0) { Remove-Item -Recurse -Force backend\.venv; exit 1 }
}

if (-not (Test-Path frontend\node_modules)) {
    Write-Host "Installing frontend dependencies (first run only)..."
    Push-Location frontend
    & npm.cmd install
    $npmStatus = $LASTEXITCODE
    Pop-Location
    if ($npmStatus -ne 0) { exit 1 }
}

$backend = Start-Process -FilePath (Resolve-Path $venvPython) -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8420" `
    -WorkingDirectory backend -NoNewWindow -PassThru
$frontend = Start-Process -FilePath "npm.cmd" -ArgumentList "run", "dev", "--", "--port", "5173" `
    -WorkingDirectory frontend -NoNewWindow -PassThru

Write-Host ""
Write-Host "  Backend:  http://127.0.0.1:8420"
Write-Host "  Frontend: http://127.0.0.1:5173   <-- open this in your browser"
Write-Host "  Press Ctrl+C to stop."
Write-Host ""

try {
    while (-not $backend.HasExited -and -not $frontend.HasExited) { Start-Sleep -Milliseconds 500 }
} finally {
    Write-Host "Stopping..."
    foreach ($p in @($backend, $frontend)) {
        if ($p -and -not $p.HasExited) { & taskkill /T /F /PID $p.Id 2>&1 | Out-Null }
    }
}
