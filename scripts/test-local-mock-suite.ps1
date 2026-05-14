$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$frontendApp = Join-Path $root "frontend\app.js"
$python = Join-Path $root ".venv\Scripts\python.exe"
$runRoot = Join-Path $backend (".tmp\mock-suite-runs\" + [guid]::NewGuid().ToString("N"))
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
  & $python -m ruff check .
  if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
  }

  & $python -m pytest tests --basetemp $baseTemp -p no:cacheprovider
  if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
  }
}
finally {
  Pop-Location
}

node --check $frontendApp
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}

$scanTargets = @(
  "backend",
  "frontend",
  "scripts",
  "README.md",
  "PROJECT_STATUS.md",
  ".env.example",
  "docker-compose.yml",
  "docs"
)
$scanFiles = foreach ($target in $scanTargets) {
  $path = Join-Path $root $target
  if (Test-Path $path -PathType Leaf) {
    Get-Item $path
  }
  elseif (Test-Path $path -PathType Container) {
    Get-ChildItem -LiteralPath $path -Recurse -File -ErrorAction SilentlyContinue
  }
}
$scanFiles = $scanFiles | Where-Object {
  $fullName = $_.FullName
  $fullName -notmatch "\\backend\\.pytest_cache\\" -and
  $fullName -notmatch "\\backend\\.tmp\\" -and
  $fullName -notmatch "\\backend\\pytest-cache-files-[^\\]*\\" -and
  $fullName -notmatch "\\.tools\\" -and
  $fullName -notmatch "\\.venv\\"
}
$secretPatterns = @(
  ("AI" + "za"),
  ("TAVILY_" + "API_KEY=.+\S"),
  ("VIBER_" + "AUTH_TOKEN=.+\S")
)
$secretMatches = $scanFiles | Select-String -Pattern $secretPatterns -CaseSensitive

if ($secretMatches) {
  $secretMatches
  exit 1
}
Write-Output "secret scan clean"
