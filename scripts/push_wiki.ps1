# ==============================================================================
# Jev Harness — GitHub Wiki Quad-Sync Script (PowerShell)
# Synchronizes all 17 bilingual wiki pages from .wiki/ to GitHub Wiki Git repo
# ==============================================================================
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$wikiSrc = Join-Path $repoRoot ".wiki"
$wikiRemote = "https://github.com/ismaelsoilet/jev-harness.wiki.git"
$tmpDir = Join-Path $env:TEMP "jev-harness-wiki-sync"

Write-Host "⚡ Jev Harness — Synchronizing Wiki..." -ForegroundColor Cyan

if (-not (Test-Path $wikiSrc)) {
    Write-Error "❌ Error: Wiki source directory '$wikiSrc' not found."
}

if (Test-Path $tmpDir) {
    Remove-Item -Path $tmpDir -Recurse -Force
}

# Ensure git is in PATH
$gitCmd = Get-Command git -ErrorAction SilentlyContinue
if (-not $gitCmd) {
    if (Test-Path "C:\Users\Ismael\bin\mingit\cmd\git.exe") {
        $env:Path = "C:\Users\Ismael\bin\mingit\cmd;" + $env:Path
    }
}

Write-Host "📥 Cloning GitHub Wiki repository..." -ForegroundColor Yellow
try {
    & git clone $wikiRemote $tmpDir 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Clone failed" }
}
catch {
    Write-Host ""
    Write-Host "⚠️  The GitHub Wiki git repository is not yet initialized on GitHub." -ForegroundColor Yellow
    Write-Host "👉 Please visit https://github.com/ismaelsoilet/jev-harness/wiki" -ForegroundColor Cyan
    Write-Host "   and click 'Create the first page' (or Save page) once to initialize the git repo."
    Write-Host "   Then run this script again."
    exit 1
}

Write-Host "📋 Copying 17 bilingual pages to working tree..." -ForegroundColor Yellow
Copy-Item -Path "$wikiSrc\*" -Destination $tmpDir -Recurse -Force

Set-Location $tmpDir
& git add .

$status = & git status --porcelain
if (-not $status) {
    Write-Host "✅ Wiki is already up to date. No changes to commit." -ForegroundColor Green
    exit 0
}

Write-Host "💾 Committing changes..." -ForegroundColor Yellow
& git commit -m "docs(wiki): synchronize complete bilingual documentation (17 pages)"

Write-Host "🚀 Pushing to GitHub Wiki..." -ForegroundColor Yellow
& git push origin master 2>&1
if ($LASTEXITCODE -ne 0) {
    & git push origin main 2>&1
}

Write-Host "✨ GitHub Wiki synchronization complete! Visit: https://github.com/ismaelsoilet/jev-harness/wiki" -ForegroundColor Green
