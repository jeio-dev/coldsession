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
    "$DEST\docs\plans",
    "$DEST\templates"
)
foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

# Copy commands
Copy-Item -Path "$SRC\commands\*.md" -Destination "$DEST\.claude\commands\" -Force

# Copy the tool and its Windows entry point.
# `plan` is an extension-less Python file with a shebang. Git Bash runs it,
# but PowerShell cannot run an extension-less file at all - it refuses with
# "Cannot run a document" - and PowerShell does not apply PATHEXT to an
# explicit path, so a .cmd sitting next to it is not found either. The
# commands installed here are repointed at plan.cmd, which works from
# PowerShell, cmd.exe, and Git Bash alike. Both files are installed, so the
# repo still works for a teammate who runs install.sh.
Copy-Item -Path "$SRC\bin\plan" -Destination "$DEST\.claude\bin\plan" -Force
Copy-Item -Path "$SRC\bin\plan.cmd" -Destination "$DEST\.claude\bin\plan.cmd" -Force

$commandFiles = Get-ChildItem -Path "$DEST\.claude\commands\*.md"
foreach ($f in $commandFiles) {
    $text = [System.IO.File]::ReadAllText($f.FullName)
    # Negative lookahead so re-running the installer cannot produce plan.cmd.cmd
    $patched = [regex]::Replace($text, '\.claude/bin/plan(?!\.cmd)', '.claude/bin/plan.cmd')
    if ($patched -ne $text) {
        [System.IO.File]::WriteAllText($f.FullName, $patched)
    }
}
Write-Host "pointed $($commandFiles.Count) commands at .claude/bin/plan.cmd"

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
    "allow": [
      "Bash(.claude/bin/plan.cmd:*)",
      "Bash(.claude/bin/plan:*)",
      "PowerShell(.claude/bin/plan.cmd:*)"
    ]
  }
}
"@
    # No BOM: Windows PowerShell's UTF8 encoding writes one, and a BOM ahead
    # of the opening brace is not something every JSON reader tolerates.
    [System.IO.File]::WriteAllText($SETTINGS, $json, (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "wrote .claude/settings.json"
} else {
    Write-Host "kept existing .claude/settings.json - add this yourself:"
    Write-Host '  "model": "opusplan"'
    Write-Host '  "permissions": { "allow": ["Bash(.claude/bin/plan.cmd:*)", "PowerShell(.claude/bin/plan.cmd:*)"] }'
}

Write-Host ""
Write-Host "installed into $DEST"
Write-Host "  .claude\commands\     10 commands, calling .claude/bin/plan.cmd"
Write-Host "  .claude\bin\plan      dependency + context tool"
Write-Host "  .claude\bin\plan.cmd  the entry point PowerShell can actually run"
Write-Host "  templates\            PLAN.md, phase.md"
Write-Host ""
Write-Host 'next: claude, then /define <your idea>'
