param(
  [string]$Query = "Starlink Mini for travel: buyer research",
  [string]$Model = ""
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$python = Join-Path $root ".venv\Scripts\python.exe"
$tempRoot = Join-Path $root ".tools\smoke-temp"

if (-not (Test-Path $python)) {
  throw "Missing local Python venv. Run powershell -ExecutionPolicy Bypass -File .\scripts\test-backend.ps1 first."
}

New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null
$env:TEMP = (Resolve-Path $tempRoot).Path
$env:TMP = (Resolve-Path $tempRoot).Path
$env:RESEARCH_PROVIDER = "gemini"
$env:ENABLE_GOOGLE_SMOKE_TESTS = "true"
if ($Model -ne "") {
  $env:GEMINI_RESEARCH_MODEL = $Model
}

Push-Location $backend
try {
  & $python -m app.cli smoke-gemini-research --query $Query
  if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
  }
}
finally {
  Pop-Location
  Remove-Item Env:\RESEARCH_PROVIDER -ErrorAction SilentlyContinue
  Remove-Item Env:\ENABLE_GOOGLE_SMOKE_TESTS -ErrorAction SilentlyContinue
  if ($Model -ne "") {
    Remove-Item Env:\GEMINI_RESEARCH_MODEL -ErrorAction SilentlyContinue
  }
}
