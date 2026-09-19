$ErrorActionPreference = 'Stop'

function SecurePlain([Security.SecureString]$s) {
  $b=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($s)
  try {[Runtime.InteropServices.Marshal]::PtrToStringBSTR($b)} finally {[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($b)}
}
function Basic([string]$user,[string]$token) {
  [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes(("{0}:{1}" -f $user,$token)))
}
$zip=(Read-Host 'Path of ZIP file (you can drag the ZIP into this window)').Trim().Trim('"')
$target=(Read-Host 'Target repository URL (example https://github.com/owner/repo.git)').Trim()
if (!(Test-Path $zip -PathType Leaf)) { throw 'ZIP file not found.' }
if (![IO.Path]::GetExtension($zip).Equals('.zip',[StringComparison]::OrdinalIgnoreCase)) { throw 'The selected file is not a ZIP.' }
if (!(Get-Command git -ErrorAction SilentlyContinue)) { throw 'Git for Windows is not installed.' }
$uri=[Uri]$target; $parts=$uri.AbsolutePath.Trim('/').Split('/'); $owner=$parts[0]
$token=SecurePlain (Read-Host "PAT for target account $owner (hidden)" -AsSecureString)
if ([string]::IsNullOrWhiteSpace($token)) { throw 'Target PAT is required.' }
$root=Join-Path ([IO.Path]::GetDirectoryName((Resolve-Path $zip).Path)) ('github-upload-'+[IO.Path]::GetFileNameWithoutExtension($zip)+'-'+(Get-Date -Format yyyyMMdd-HHmmss))
New-Item -ItemType Directory -Force $root | Out-Null
$extract=Join-Path $root 'extracted'; Expand-Archive -LiteralPath $zip -DestinationPath $extract -Force
$items=@(Get-ChildItem -LiteralPath $extract -Force)
if ($items.Count -eq 1 -and $items[0].PSIsContainer) { $project=$items[0].FullName } else { $project=$extract }
Set-Location $project
$ask=Join-Path $env:TEMP ('github-upload-'+[guid]::NewGuid()+'.cmd')
@('@echo off','echo %~1 | findstr /I "Username" >nul','if not errorlevel 1 ( echo %UPLOAD_USER% ) else ( echo %UPLOAD_TOKEN% )') | Set-Content $ask -Encoding ASCII
$env:GIT_ASKPASS=$ask; $env:GIT_TERMINAL_PROMPT='0'; $env:UPLOAD_USER=$owner; $env:UPLOAD_TOKEN=$token
try {
  git init
  $remotes = @(git remote)
  if ($remotes -contains 'origin') { git remote remove origin }
  git remote add origin $target
  git add -A
  git commit -m 'Import project from ZIP'
  git branch -M main
  Write-Host 'Uploading project contents to target...' -ForegroundColor Cyan
  $basic = Basic $owner $token
  git -c credential.helper= -c http.extraHeader="Authorization: Basic $basic" push -u origin main:main
  if ($LASTEXITCODE -ne 0) { throw 'Upload failed. Check the target PAT owner, repository access, and Contents read/write permission.' }
  Write-Host "Upload completed: $target" -ForegroundColor Green
  Write-Host "Local extracted copy: $project"
  Read-Host 'Press Enter to close'
} finally {
  Remove-Item Env:UPLOAD_USER,Env:UPLOAD_TOKEN,Env:GIT_ASKPASS,Env:GIT_TERMINAL_PROMPT -ErrorAction SilentlyContinue
  Remove-Item $ask -Force -ErrorAction SilentlyContinue
}
