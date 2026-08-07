# Install the planning workflow into the current project.
#   .\install.ps1 [target-dir]   default: $PWD
$ErrorActionPreference = "Stop"

$SRC = Split-Path -Parent $MyInvocation.MyCommand.Definition | Resolve-Path
$DEST = if ($args[0]) { Resolve-Path $args[0] } else { Get-Location }

if ((Resolve-Path $SRC) -eq (Resolve-Path $DEST)) {
    Write-Error "refusing to install into the workflow repo itself"
    exit 1
}

# Check for python3 (or python)
if (-not (Get-Command python3 -ErrorAction SilentlyContinue)) {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Error "python3 is required"
        exit 1
    }
}

# Create directories
$dirs = @(
    "$DEST\.claude\commands",
    "$DEST\.claude\bin",
    "$DEST\docs\plans"
)
foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

# Copy commands
Copy-Item -Path "$SRC\commands\*.md" -Destination "$DEST\.claude\commands\" -Force

# Copy plan binary
Copy-Item -Path "$SRC\bin\plan" -Destination "$DEST\.claude\bin\plan" -Force

# Note: chmod +x is not needed on Windows

# Copy templates (only if they don't exist)
$templates = @("PLAN.md", "phase.md")
foreach ($t in $templates) {
    $destPath = Join-Path $DEST "templates\$t"
    if (-not (Test-Path $destPath)) {
        Copy-Item -Path "$SRC\templates\$t" -Destination $destPath
    }
}

# Settings
$SETTINGS = "$DEST\.claude\settings.json"
if (-not (Test-Path $SETTINGS)) {
    $json = @"
{
  "model": "opusplan",
  "env": {
    "CLAUDE_CODE_SUBAGENT_MODEL": "sonnet"
  },
  "permissions": {
    "allow": ["Bash(.claude/bin/plan:*)"]
  }
}
"@
    $json | Set-Content -Path $SETTINGS -Encoding UTF8
    Write-Host "wrote .claude/settings.json"
} else {
    Write-Host "kept existing .claude/settings.json - add this yourself:"
    Write-Host '  "model": "opusplan"'
    Write-Host '  "permissions": { "allow": ["Bash(.claude/bin/plan:*)"] }'
}

Write-Host ""
Write-Host "installed into $DEST"
Write-Host "  .claude\commands\   10 commands"
Write-Host "  .claude\bin\plan    dependency + context tool"
Write-Host "  templates\          PLAN.md, phase.md"
Write-Host ""
Write-Host 'next: claude, then /define <your idea>'
