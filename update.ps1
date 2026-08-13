# Update an existing install of the planning workflow to this checkout's version.
#   .\update.ps1 [target-dir] [-Keep]   default target: $PWD
#
# Re-copies commands/*.md, bin/plan, and bin/plan.cmd over an existing
# .claude/ install -- the same files install.ps1 writes unconditionally, and
# repoints the copied commands at plan.cmd exactly as install.ps1 does.
# templates/ and .claude/settings.json are yours once installed, so this
# script never touches them; re-run install.ps1 if you want those refreshed
# too. Refuses a target with no existing install.
#
#   cd $HOME\my-project
#   git clone --depth 1 https://github.com/jeio-dev/coldsession.git .coldsession
#   .\.coldsession\update.ps1
param(
    [string]$Target,
    [switch]$Keep
)
$ErrorActionPreference = "Stop"

function Get-FullPath($p) {
    return ([System.IO.Path]::GetFullPath((Resolve-Path $p).ProviderPath)).TrimEnd('\')
}

$SRC = Get-FullPath (Split-Path -Parent $MyInvocation.MyCommand.Definition)
$DEST = if ($Target) { Get-FullPath $Target } else { Get-FullPath (Get-Location).Path }

if ($SRC -eq $DEST) {
    Write-Error "refusing to update the workflow repo itself"
    exit 1
}

$existingPlan = "$DEST\.claude\bin\plan"
if (-not (Test-Path $existingPlan)) {
    Write-Error "no existing install found at $existingPlan -- run install.ps1 instead"
    exit 1
}

function Get-PlanVersion($dest) {
    $cmd = Get-Command python3 -ErrorAction SilentlyContinue
    if (-not $cmd) { $cmd = Get-Command python -ErrorAction SilentlyContinue }
    if (-not $cmd) { return "unknown" }
    try {
        $out = & $cmd.Source "$dest\.claude\bin\plan" version 2>$null
        if ($LASTEXITCODE -eq 0 -and $out) { return $out.Trim() }
    } catch {}
    return "unknown"
}

$OLD_VERSION = Get-PlanVersion $DEST

Copy-Item -Path "$SRC\commands\*.md" -Destination "$DEST\.claude\commands\" -Force
Copy-Item -Path "$SRC\bin\plan" -Destination "$DEST\.claude\bin\plan" -Force
Copy-Item -Path "$SRC\bin\plan.cmd" -Destination "$DEST\.claude\bin\plan.cmd" -Force

$commandFiles = Get-ChildItem -Path "$DEST\.claude\commands\*.md"
foreach ($f in $commandFiles) {
    $text = [System.IO.File]::ReadAllText($f.FullName)
    # Negative lookahead so re-running this cannot produce plan.cmd.cmd
    $patched = [regex]::Replace($text, '\.claude/bin/plan(?!\.cmd)', '.claude/bin/plan.cmd')
    if ($patched -ne $text) {
        [System.IO.File]::WriteAllText($f.FullName, $patched)
    }
}

$NEW_VERSION = Get-PlanVersion $DEST

Write-Host ""
Write-Host "updated $DEST`: $OLD_VERSION -> $NEW_VERSION"
Write-Host "  .claude\commands\     10 commands, calling .claude/bin/plan.cmd"
Write-Host "  .claude\bin\plan      dependency + context tool"
Write-Host "  .claude\bin\plan.cmd  the entry point PowerShell can actually run"
Write-Host ""
Write-Host "templates\ and .claude\settings.json were left alone"
Write-Host "next: git diff .claude, review, then commit"

# Same disposable-clone cleanup as install.ps1. Only $DEST\.coldsession
# qualifies: a clone under another name, or a checkout outside the project,
# is something you chose to keep, and this script does not get to decide
# otherwise.
if ($SRC -eq "$DEST\.coldsession") {
    if ($Keep) {
        Write-Host ""
        Write-Host "kept $SRC (-Keep)"
    } else {
        Write-Host ""
        Write-Host "removing $SRC"
        Set-Location $DEST
        try {
            Remove-Item -LiteralPath $SRC -Recurse -Force -Confirm:$false
        } catch {
            Write-Host "could not remove $SRC - delete it yourself"
            Write-Host "  $($_.Exception.Message)"
        }
    }
} elseif ($SRC.StartsWith("$DEST\", [System.StringComparison]::OrdinalIgnoreCase)) {
    Write-Host ""
    Write-Host "note: $SRC is inside the project; remove it when you're done"
}
