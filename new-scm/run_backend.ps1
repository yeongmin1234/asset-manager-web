$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$settings = Join-Path $root '.env'
if (!(Test-Path -LiteralPath $settings)) { throw '.env 파일이 없습니다.' }
foreach ($line in Get-Content -LiteralPath $settings) {
    if ($line -match '^(SCM_[A-Z0-9_]+)=(.*)$') {
        Set-Item -Path ("Env:" + $Matches[1]) -Value $Matches[2]
    }
}
$env:SCM_LOG_FILE = Join-Path $root 'runtime\logs\api.log'
$env:PYTHONDONTWRITEBYTECODE = '1'
Set-Location -LiteralPath (Join-Path $root 'backend')
python -m uvicorn app.main:app --host 127.0.0.1 --port 8012 --timeout-keep-alive 5
