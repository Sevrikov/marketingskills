$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$python = Join-Path $root ".venv\Scripts\python.exe"
$runRoot = Join-Path $backend (".tmp\pytest-runs\" + [guid]::NewGuid().ToString("N"))
$tempRoot = Join-Path $runRoot "tmp"
$baseTemp = Join-Path $runRoot "basetemp"

if (-not (Test-Path $python)) {
  throw "Missing local Python venv. Run the dependency setup first."
}

New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null
$env:TEMP = (Resolve-Path $tempRoot).Path
$env:TMP = (Resolve-Path $tempRoot).Path

Push-Location $backend
try {
  & $python -m pytest tests --basetemp $baseTemp -p no:cacheprovider
  if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
  }
}
finally {
  Pop-Location
}
