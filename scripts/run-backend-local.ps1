$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$python = Join-Path $root ".venv\Scripts\python.exe"
$localDb = Join-Path $backend "local.db"
$skillsRoot = Join-Path $root ".agents\skills"
$tempRoot = Join-Path $root ".tools\run-temp"

if (-not (Test-Path $python)) {
  throw "Missing local Python venv. Run scripts/test-backend.ps1 setup flow first."
}

New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null
$env:TEMP = (Resolve-Path $tempRoot).Path
$env:TMP = (Resolve-Path $tempRoot).Path
$env:APP_ENV = "local"
$env:DATABASE_URL = "sqlite:///$($localDb.Replace('\', '/'))"
$env:QUEUE_MODE = "sync"
$env:SKILL_REGISTRY_ROOT = $skillsRoot
$env:CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173,null"

Push-Location $backend
try {
  & $python -m app.cli init-db
  & $python -m app.cli seed-prompts
  & $python -m app.cli sync-skills
  $uvicornArgs = @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000")
  if ($env:UVICORN_RELOAD -eq "1") {
    $uvicornArgs += "--reload"
  }
  & $python @uvicornArgs
}
finally {
  Pop-Location
}
