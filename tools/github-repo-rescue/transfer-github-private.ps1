$ErrorActionPreference = 'Stop'

function Get-RepositorySlug([string]$url) {
    $uri = [Uri]$url
    $parts = $uri.AbsolutePath.Trim('/').Split('/') | Where-Object { $_ }
    if ($parts.Count -lt 2) { throw "Invalid repository URL: $url" }
    (($parts[0] + '--' + ($parts[1] -replace '\.git$', '')) -replace '[^A-Za-z0-9._-]', '_')
}
function Get-Owner([string]$url) { ([Uri]$url).AbsolutePath.Trim('/').Split('/')[0] }
function Convert-SecureToPlain([Security.SecureString]$value) {
    if ($null -eq $value) { return '' }
    $b = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($value)
    try { [Runtime.InteropServices.Marshal]::PtrToStringBSTR($b) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($b) }
}

Write-Host 'GitHub authenticated full repository transfer' -ForegroundColor Cyan
Write-Host 'Separate hidden tokens are used for source read and target write.'
$source = (Read-Host 'Source repository URL').Trim()
$target = (Read-Host 'Target repository URL').Trim()
if ([string]::IsNullOrWhiteSpace($source) -or [string]::IsNullOrWhiteSpace($target)) { throw 'Both URLs are required.' }
if ($source.TrimEnd('/') -eq $target.TrimEnd('/')) { throw 'Source and target must be different.' }
$sourceOwner = Get-Owner $source; $targetOwner = Get-Owner $target
$sourceToken = Convert-SecureToPlain (Read-Host "Source PAT for $sourceOwner (press Enter if truly public)" -AsSecureString)
$targetToken = Convert-SecureToPlain (Read-Host "Target PAT for $targetOwner" -AsSecureString)
if ([string]::IsNullOrWhiteSpace($targetToken)) { throw 'A target PAT is required for push.' }

$root = Join-Path $PSScriptRoot 'repository-mirrors'
$work = Join-Path $root ("mirror-{0}-to-{1}.git" -f (Get-RepositorySlug $source), (Get-RepositorySlug $target))
$bundle = Join-Path $root ("backup-{0}-to-{1}.bundle" -f (Get-RepositorySlug $source), (Get-RepositorySlug $target))
New-Item -ItemType Directory -Force $root | Out-Null
Write-Host "Local mirror: $work" -ForegroundColor DarkGray
if ((Read-Host 'Type TRANSFER to continue') -ne 'TRANSFER') { throw 'Transfer cancelled.' }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Git for Windows is not installed.' }

$askpass = Join-Path $env:TEMP ("github-transfer-askpass-{0}.cmd" -f ([guid]::NewGuid()))
@('@echo off','echo %~1 | findstr /I "Username" >nul','if not errorlevel 1 ( echo %TRANSFER_GIT_USERNAME% ) else ( echo %TRANSFER_GIT_TOKEN% )') | Set-Content -LiteralPath $askpass -Encoding ASCII
$env:GIT_ASKPASS = $askpass; $env:GIT_TERMINAL_PROMPT = '0'; $env:GIT_OPTIONAL_LOCKS = '0'
try {
    $validMirror = Test-Path (Join-Path $work 'HEAD')
    if (-not $validMirror) {
        if (Test-Path $work) { Remove-Item -LiteralPath $work -Recurse -Force }
        $ok = $false
        for ($attempt = 1; $attempt -le 3; $attempt++) {
            if (Test-Path $work) { Remove-Item -LiteralPath $work -Recurse -Force }
            Write-Host "Downloading complete history (attempt $attempt of 3)..." -ForegroundColor Cyan
            $env:TRANSFER_GIT_USERNAME = $sourceOwner; $env:TRANSFER_GIT_TOKEN = $sourceToken
            & git -c credential.helper= -c http.version=HTTP/1.1 -c http.maxRequests=1 clone --mirror $source $work
            if ($LASTEXITCODE -eq 0 -and (Test-Path (Join-Path $work 'HEAD'))) { $ok = $true; break }
            Write-Host 'Download interrupted or denied; retrying...' -ForegroundColor Yellow; Start-Sleep 3
        }
        if (-not $ok) { throw 'Source download failed. Check the source URL and source PAT permissions.' }
    } else { Write-Host 'Existing mirror found for this source/target pair; reusing it.' -ForegroundColor Green }

    Set-Location $work
    & git remote set-url origin $source
    & git remote set-url --push origin $target
    & git config remote.origin.mirror false
    if ($LASTEXITCODE -ne 0) { throw 'Could not configure remotes.' }

    Write-Host "Creating/verifying offline backup: $bundle" -ForegroundColor Cyan
    & git bundle create $bundle --all; if ($LASTEXITCODE -ne 0) { throw 'Bundle creation failed.' }
    & git bundle verify $bundle; if ($LASTEXITCODE -ne 0) { throw 'Bundle verification failed.' }

    Write-Host 'Pushing branches and tags to target...' -ForegroundColor Cyan
    $env:TRANSFER_GIT_USERNAME = $targetOwner; $env:TRANSFER_GIT_TOKEN = $targetToken
    & git -c credential.helper= push --prune origin '+refs/heads/*:refs/heads/*' '+refs/tags/*:refs/tags/*'
    if ($LASTEXITCODE -ne 0) { throw 'Target push failed. Check the target PAT Contents: Read and write permission.' }

    if (Get-Command git-lfs -ErrorAction SilentlyContinue) {
        Write-Host 'Git LFS detected; transferring LFS objects...' -ForegroundColor Cyan
        & git -c credential.helper= lfs fetch --all origin
        & git -c credential.helper= lfs push --all origin
        if ($LASTEXITCODE -ne 0) { throw 'Git LFS transfer failed.' }
    }
    Write-Host "`nFull authenticated transfer completed." -ForegroundColor Green
    Write-Host "Target: $target`nMirror: $work`nOffline backup: $bundle"
    Write-Host 'Actions secrets, environments, deploy keys, and branch protection are separate settings.' -ForegroundColor Yellow
    Read-Host 'Press Enter to close'
} finally {
    Remove-Item Env:TRANSFER_GIT_USERNAME -ErrorAction SilentlyContinue
    Remove-Item Env:TRANSFER_GIT_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:GIT_ASKPASS -ErrorAction SilentlyContinue
    Remove-Item Env:GIT_TERMINAL_PROMPT -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $askpass -Force -ErrorAction SilentlyContinue
}
