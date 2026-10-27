$ErrorActionPreference = 'Stop'
$envPath = Join-Path $PSScriptRoot '.env'
if (!(Test-Path -LiteralPath $envPath)) { throw 'new-scm/.env 파일이 없습니다.' }

$content = [System.IO.File]::ReadAllText($envPath)
$match = [regex]::Match($content, '(?m)^SCM_DATABASE_URL=[^\r\n]*')
if (!$match.Success) { throw 'SCM_DATABASE_URL 항목이 없습니다.' }

$secret = Read-Host 'new_scm_ro PostgreSQL 비밀번호' -AsSecureString
if ($secret.Length -eq 0) { throw '빈 비밀번호는 허용되지 않습니다.' }
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
try {
    $password = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    $encoded = [System.Uri]::EscapeDataString($password)
    $url = 'postgresql+psycopg://new_scm_ro:' + $encoded + '@127.0.0.1:5432/new_scm_dev'
    $replacement = 'SCM_DATABASE_URL=' + $url
    $updated = $content.Substring(0, $match.Index) + $replacement + $content.Substring($match.Index + $match.Length)
    [System.IO.File]::WriteAllText($envPath, $updated, [System.Text.UTF8Encoding]::new($false))
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    $password = $null
    $encoded = $null
    $url = $null
    $replacement = $null
    $updated = $null
}

Write-Host 'new-scm/.env의 SCM_DATABASE_URL 설정 완료 (비밀번호와 URL은 표시하지 않음).'
