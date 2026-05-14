$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$python = Join-Path $root ".venv\Scripts\python.exe"
$runRoot = Join-Path $backend (".tmp\realistic-product-card-runs\" + [guid]::NewGuid().ToString("N"))
$tempRoot = Join-Path $runRoot "tmp"
$baseTemp = Join-Path $runRoot "basetemp"

if (-not (Test-Path $python)) {
  throw "Missing local Python venv. Run the dependency setup first."
}

$env:LLM_PROVIDER = "mock"
$env:RESEARCH_PROVIDER = "mock"
$env:SOURCE_PROVIDER = "mock"
$env:NOTIFICATION_PROVIDER = "mock"
$env:CMS_PROVIDER = "mock"
$env:PRICE_MONITOR_PROVIDER = "mock"
$env:ENABLE_REAL_PUBLISHING = "false"
$env:ENABLE_REAL_VIDEO_GENERATION = "false"
$env:ENABLE_GOOGLE_SMOKE_TESTS = "false"

New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null
$env:TEMP = (Resolve-Path $tempRoot).Path
$env:TMP = (Resolve-Path $tempRoot).Path

Push-Location $backend
try {
  & $python -m pytest tests/test_realistic_product_card_smoke.py --basetemp $baseTemp -p no:cacheprovider
  if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
  }
}
finally {
  Pop-Location
}
