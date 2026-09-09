# Install, update, or switch coldsession agent integrations in a project.
#   .\install.ps1 [[-Target] <dir>] [-Agent claude|codex|both] [-Keep]
param(
    [Parameter(Position = 0)]
    [string]$Target,

    [ValidateSet("claude", "codex", "both")]
    [string]$Agent,

    [switch]$Keep
)
$ErrorActionPreference = "Stop"

function Write-Usage {
    [Console]::Error.WriteLine("usage: .\install.ps1 [[-Target] <dir>] [-Agent claude|codex|both] [-Keep]")
}

function Get-FullPath($Path) {
    return ([System.IO.Path]::GetFullPath((Resolve-Path $Path).ProviderPath)).TrimEnd('\')
}

function Find-PythonCommand {
    foreach ($name in @("python3", "python", "py")) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if (-not $cmd) { continue }
        try {
            & $cmd.Source -c "import sys" 2>$null
            if ($LASTEXITCODE -eq 0) { return $cmd.Source }
        } catch {}
    }
    return $null
}

function Get-PlanVersion($Python, $Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    try {
        $output = & $Python $Path version 2>$null
        if ($LASTEXITCODE -eq 0 -and $output) { return "$output".Trim() }
    } catch {}
    return $null
}

function Test-ExactKeys($Object, [string[]]$Names) {
    if ($null -eq $Object) { return $false }
    $actual = @($Object.PSObject.Properties.Name | Sort-Object)
    $expected = @($Names | Sort-Object)
    return $actual.Count -eq $expected.Count -and -not (Compare-Object $actual $expected)
}

# Hook wrappers ship as .sh/.cmd pairs, so a command is compared by name and
# not by path: this installer registers the .cmd, install.sh registers the .sh,
# and both are generated output. The surrounding quotes come off first --
# Write-ClaudeSettings quotes the executable path so a project directory with
# a space in it still launches, and this has to recognise what it writes.
$ExpectedHookSignature = (@(
    "PostToolUse::0::Edit|Write::cs-guard-lint",
    "PreToolUse::0::Read|Edit|Write::cs-guard-read",
    "PreToolUse::1::Edit|Write::cs-guard-write",
    "UserPromptSubmit::0::::cs-guard-stage"
) | Sort-Object) -join "`n"

function Get-HookSignature($Hooks) {
    if ($null -eq $Hooks) { return $null }
    $rows = @()
    foreach ($event in @($Hooks.PSObject.Properties.Name)) {
        $index = 0
        foreach ($entry in @($Hooks.$event)) {
            if ($null -eq $entry) { return $null }
            $shape = (Test-ExactKeys $entry @("matcher", "hooks")) -or (Test-ExactKeys $entry @("hooks"))
            if (-not $shape) { return $null }
            $specs = @($entry.hooks)
            if ($specs.Count -ne 1) { return $null }
            if ($specs[0].type -ne "command") { return $null }
            $command = [string]$specs[0].command
            if (-not $command) { return $null }
            $leaf = ($command.Trim().Trim('"') -replace '\\', '/').Split('/')[-1]
            $leaf = $leaf -replace '\.(sh|cmd)$', ''
            $matcher = ""
            if (@($entry.PSObject.Properties.Name) -contains "matcher") {
                $matcher = [string]$entry.matcher
            }
            $rows += "$event::$index::$matcher::$leaf"
            $index += 1
        }
    }
    return (($rows | Sort-Object) -join "`n")
}

# True when settings.json is this installer's own output and nobody has touched
# it. It decides both whether an uninstall may delete the file and whether an
# update may rewrite it, so it has to keep recognising the pre-hooks three-key
# default: a user upgrading from 2.2 never edited that file and must not be
# warned about it.
function Test-GeneratedClaudeSettings($Path) {
    try {
        $settings = [System.IO.File]::ReadAllText($Path) | ConvertFrom-Json
    } catch {
        return $false
    }

    $hasHooks = @($settings.PSObject.Properties.Name) -contains "hooks"
    if ($hasHooks) {
        if (-not (Test-ExactKeys $settings @("model", "env", "permissions", "hooks"))) { return $false }
        if ((Get-HookSignature $settings.hooks) -ne $ExpectedHookSignature) { return $false }
    } else {
        if (-not (Test-ExactKeys $settings @("model", "env", "permissions"))) { return $false }
    }
    if ($settings.model -ne "opusplan") { return $false }
    if (-not (Test-ExactKeys $settings.env @("CLAUDE_CODE_SUBAGENT_MODEL"))) { return $false }
    if ($settings.env.CLAUDE_CODE_SUBAGENT_MODEL -ne "sonnet") { return $false }
    if (-not (Test-ExactKeys $settings.permissions @("allow"))) { return $false }

    $rawAllow = @($settings.permissions.allow)
    $actual = @($rawAllow | Sort-Object -Unique)
    if ($rawAllow.Count -ne $actual.Count) { return $false }
    $current = @(
        "Bash(.claude/bin/plan:*)",
        "Bash(.claude/bin/plan.cmd:*)",
        "PowerShell(.claude/bin/plan.cmd:*)"
    ) | Sort-Object
    $legacy = @(
        "Bash(.claude/bin/plan:*)",
        "Bash(.claude/bin/plan.cmd:*)"
    ) | Sort-Object

    $matchesCurrent = $actual.Count -eq $current.Count -and -not (Compare-Object $actual $current)
    $matchesLegacy = $actual.Count -eq $legacy.Count -and -not (Compare-Object $actual $legacy)
    return $matchesCurrent -or $matchesLegacy
}

# True for the generated default written before hooks existed: still ours,
# still untouched, and one rewrite short of having the gates.
function Test-SettingsPredateHooks($Path) {
    try {
        $settings = [System.IO.File]::ReadAllText($Path) | ConvertFrom-Json
    } catch {
        return $false
    }
    return -not (@($settings.PSObject.Properties.Name) -contains "hooks")
}

function Remove-ManagedFile($Path) {
    if (Test-Path -LiteralPath $Path -PathType Leaf) {
        Remove-Item -LiteralPath $Path -Force
        $script:Removed += 1
    }
}

function Remove-ManagedDirectory($Path) {
    if (Test-Path -LiteralPath $Path -PathType Container) {
        Remove-Item -LiteralPath $Path -Recurse -Force
        $script:Removed += 1
    }
}

# Only this installer's own wrappers, never the whole directory: a project may
# keep hooks of its own alongside them. The directory goes only if removing
# ours emptied it.
function Remove-ManagedHooks($Root) {
    $dir = "$Root\.claude\hooks"
    if (-not (Test-Path -LiteralPath $dir -PathType Container)) { return }
    Get-ChildItem -LiteralPath $dir -File -Filter "cs-guard-*" |
        ForEach-Object { Remove-ManagedFile $_.FullName }
    if (-not (Get-ChildItem -LiteralPath $dir -Force)) {
        Remove-Item -LiteralPath $dir -Force
    }
}

function Write-ClaudeSettings($Path) {
    # Single-quoted here-string: $CLAUDE_PROJECT_DIR is Claude Code's own
    # placeholder and must survive into the file unexpanded.
    $settingsJson = @'
{
  "model": "opusplan",
  "env": {
    "CLAUDE_CODE_SUBAGENT_MODEL": "sonnet"
  },
  "permissions": {
    "allow": [
      "Bash(.claude/bin/plan:*)",
      "Bash(.claude/bin/plan.cmd:*)",
      "PowerShell(.claude/bin/plan.cmd:*)"
    ]
  },
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR/.claude/hooks/cs-guard-stage.cmd\""
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Read|Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR/.claude/hooks/cs-guard-read.cmd\""
          }
        ]
      },
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR/.claude/hooks/cs-guard-write.cmd\""
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR/.claude/hooks/cs-guard-lint.cmd\""
          }
        ]
      }
    ]
  }
}
'@
    [System.IO.File]::WriteAllText($Path, $settingsJson, (New-Object System.Text.UTF8Encoding($false)))
}

function Copy-Command($Source, $Destination, $RuntimePath) {
    $content = [System.IO.File]::ReadAllText($Source)
    $content = $content.Replace('.claude/bin/plan', $RuntimePath)
    $content = [regex]::Replace($content, [regex]::Escape($RuntimePath) + '(?!\.cmd)', $RuntimePath + '.cmd')
    [System.IO.File]::WriteAllText(
        $Destination,
        $content,
        (New-Object System.Text.UTF8Encoding($false))
    )
}

if (-not $Agent) {
    if ([Console]::IsInputRedirected) {
        [Console]::Error.WriteLine("-Agent is required when input is not interactive")
        Write-Usage
        exit 2
    }
    Write-Host "Install coldsession for:"
    Write-Host "  1) Claude Code"
    Write-Host "  2) Codex"
    Write-Host "  3) Both"
    while (-not $Agent) {
        $choice = Read-Host "Choose 1, 2, or 3"
        switch ($choice.ToLowerInvariant()) {
            { $_ -in @("1", "claude") } { $Agent = "claude"; break }
            { $_ -in @("2", "codex") } { $Agent = "codex"; break }
            { $_ -in @("3", "both") } { $Agent = "both"; break }
            default { Write-Host "enter 1, 2, or 3" }
        }
    }
}

$SourceRoot = Get-FullPath (Split-Path -Parent $MyInvocation.MyCommand.Definition)
$DestinationRoot = if ($Target) { Get-FullPath $Target } else { Get-FullPath (Get-Location).Path }

if ($SourceRoot -eq $DestinationRoot) {
    [Console]::Error.WriteLine("refusing to install into the workflow repo itself")
    exit 1
}

$Python = Find-PythonCommand
if (-not $Python) {
    [Console]::Error.WriteLine("python3 is required")
    exit 1
}

$OldClaudeVersion = Get-PlanVersion $Python "$DestinationRoot\.claude\bin\plan"
$OldCodexVersion = Get-PlanVersion $Python "$DestinationRoot\.agents\coldsession\bin\plan"
$KnownInstall = [bool]($OldClaudeVersion -or $OldCodexVersion)
$LegacyInstall = [bool]($OldClaudeVersion -match '^1\.')
$NewVersion = Get-PlanVersion $Python "$SourceRoot\bin\plan"
$Removed = 0
$SettingsWarning = $false
$LegacyCommands = @("approve", "build", "close", "define", "groundwork", "plan", "recheck", "review", "revise", "status")

if ($LegacyInstall) {
    foreach ($name in $LegacyCommands) {
        Remove-ManagedFile "$DestinationRoot\.claude\commands\$name.md"
    }
    if (Test-Path -LiteralPath "$DestinationRoot\.agents\skills") {
        Get-ChildItem -LiteralPath "$DestinationRoot\.agents\skills" -Directory -Filter "coldsession-*" |
            ForEach-Object { Remove-ManagedDirectory $_.FullName }
    }
}

if ($Agent -eq "codex") {
    if ($KnownInstall) {
        if (Test-Path -LiteralPath "$DestinationRoot\.claude\commands") {
            Get-ChildItem -LiteralPath "$DestinationRoot\.claude\commands" -File -Filter "cs-*.md" |
                ForEach-Object { Remove-ManagedFile $_.FullName }
        }
        Remove-ManagedFile "$DestinationRoot\.claude\bin\plan"
        Remove-ManagedFile "$DestinationRoot\.claude\bin\plan.cmd"
        Remove-ManagedHooks $DestinationRoot
        $settingsPath = "$DestinationRoot\.claude\settings.json"
        if (Test-Path -LiteralPath $settingsPath -PathType Leaf) {
            if (Test-GeneratedClaudeSettings $settingsPath) {
                Remove-ManagedFile $settingsPath
            } else {
                $SettingsWarning = $true
            }
        }
    }
} else {
    if ($KnownInstall -and (Test-Path -LiteralPath "$DestinationRoot\.claude\commands")) {
        Get-ChildItem -LiteralPath "$DestinationRoot\.claude\commands" -File -Filter "cs-*.md" |
            ForEach-Object { Remove-ManagedFile $_.FullName }
    }
    Remove-ManagedHooks $DestinationRoot
    New-Item -ItemType Directory -Force -Path "$DestinationRoot\.claude\commands", "$DestinationRoot\.claude\bin", "$DestinationRoot\.claude\hooks" | Out-Null
    Get-ChildItem -LiteralPath "$SourceRoot\commands" -File -Filter "cs-*.md" | ForEach-Object {
        Copy-Command $_.FullName "$DestinationRoot\.claude\commands\$($_.Name)" ".claude/bin/plan"
    }
    Copy-Item -LiteralPath "$SourceRoot\bin\plan" -Destination "$DestinationRoot\.claude\bin\plan" -Force
    Copy-Item -LiteralPath "$SourceRoot\bin\plan.cmd" -Destination "$DestinationRoot\.claude\bin\plan.cmd" -Force
    Get-ChildItem -LiteralPath "$SourceRoot\hooks" -File -Filter "cs-guard-*" | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination "$DestinationRoot\.claude\hooks\$($_.Name)" -Force
    }

    $settingsPath = "$DestinationRoot\.claude\settings.json"
    if (-not (Test-Path -LiteralPath $settingsPath)) {
        Write-ClaudeSettings $settingsPath
        Write-Host "wrote .claude/settings.json"
    } elseif ((Test-GeneratedClaudeSettings $settingsPath) -and (Test-SettingsPredateHooks $settingsPath)) {
        # Untouched output of an installer that predates the gates. Rewriting
        # it is the only way an upgrade delivers them, and there is nothing of
        # the user's in there to lose.
        Write-ClaudeSettings $settingsPath
        Write-Host "updated .claude/settings.json with the hook gates"
    } else {
        Write-Host "kept existing .claude/settings.json"
    }
}

if ($Agent -eq "claude") {
    if ($KnownInstall) {
        Remove-ManagedDirectory "$DestinationRoot\.agents\coldsession"
        if (Test-Path -LiteralPath "$DestinationRoot\.agents\skills") {
            Get-ChildItem -LiteralPath "$DestinationRoot\.agents\skills" -Directory -Filter "cs-*" |
                ForEach-Object { Remove-ManagedDirectory $_.FullName }
        }
    }
} else {
    if ($KnownInstall) {
        Remove-ManagedDirectory "$DestinationRoot\.agents\coldsession"
        if (Test-Path -LiteralPath "$DestinationRoot\.agents\skills") {
            Get-ChildItem -LiteralPath "$DestinationRoot\.agents\skills" -Directory -Filter "cs-*" |
                ForEach-Object { Remove-ManagedDirectory $_.FullName }
        }
    }
    $codexDirectories = @(
        "$DestinationRoot\.agents\skills",
        "$DestinationRoot\.agents\coldsession\commands",
        "$DestinationRoot\.agents\coldsession\bin"
    )
    New-Item -ItemType Directory -Force -Path $codexDirectories | Out-Null

    Get-ChildItem -LiteralPath "$SourceRoot\skills" -Directory -Filter "cs-*" | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination "$DestinationRoot\.agents\skills" -Recurse -Force
    }
    Get-ChildItem -LiteralPath "$SourceRoot\commands" -File -Filter "cs-*.md" | ForEach-Object {
        Copy-Command $_.FullName "$DestinationRoot\.agents\coldsession\commands\$($_.Name)" ".agents/coldsession/bin/plan"
    }
    Copy-Item -LiteralPath "$SourceRoot\bin\plan" -Destination "$DestinationRoot\.agents\coldsession\bin\plan" -Force
    Copy-Item -LiteralPath "$SourceRoot\bin\plan.cmd" -Destination "$DestinationRoot\.agents\coldsession\bin\plan.cmd" -Force
}

New-Item -ItemType Directory -Force -Path "$DestinationRoot\docs\plans", "$DestinationRoot\templates" | Out-Null
foreach ($template in @("OBJECTIVE.md", "PLAN.md", "phase.md")) {
    $targetPath = "$DestinationRoot\templates\$template"
    if (-not (Test-Path -LiteralPath $targetPath)) {
        Copy-Item -LiteralPath "$SourceRoot\templates\$template" -Destination $targetPath
    }
}

Write-Host ""
if ($KnownInstall) {
    $oldClaude = if ($OldClaudeVersion) { $OldClaudeVersion } else { "none" }
    $oldCodex = if ($OldCodexVersion) { $OldCodexVersion } else { "none" }
    Write-Host "updated $DestinationRoot`: $oldClaude/$oldCodex -> $NewVersion"
} else {
    Write-Host "installed coldsession $NewVersion into $DestinationRoot"
}
Write-Host "  agents: $Agent"
if ($Agent -ne "codex") { Write-Host "  Claude: .claude\commands\cs-*, .claude\bin\plan, .claude\hooks\cs-guard-*" }
if ($Agent -ne "claude") { Write-Host "  Codex:  .agents\skills\cs-* and .agents\coldsession\" }
Write-Host "  shared: templates\ and docs\plans\"
if ($Removed -gt 0) { Write-Host "  replaced/removed $Removed managed item(s)" }
if ($SettingsWarning) {
    Write-Host "  kept modified .claude\settings.json; remove stale coldsession permissions manually"
}
Write-Host ""
switch ($Agent) {
    "claude" {
        Write-Host 'next: /cs-define <your idea>'
        Write-Host 'review: git diff -- .claude templates'
    }
    "codex" {
        Write-Host 'next: $cs-define <your idea>'
        Write-Host 'review: git diff -- .agents templates'
    }
    "both" {
        Write-Host 'next: Claude Code /cs-define or Codex $cs-define'
        Write-Host 'review: git diff -- .claude .agents templates'
    }
}

if ($SourceRoot -eq "$DestinationRoot\.coldsession") {
    if ($Keep) {
        Write-Host ""
        Write-Host "kept $SourceRoot (-Keep)"
    } else {
        Write-Host ""
        Write-Host "removing $SourceRoot"
        Set-Location $DestinationRoot
        try {
            Remove-Item -LiteralPath $SourceRoot -Recurse -Force -Confirm:$false
        } catch {
            Write-Host "could not remove $SourceRoot - delete it yourself"
            Write-Host "  $($_.Exception.Message)"
        }
    }
} elseif ($SourceRoot.StartsWith("$DestinationRoot\", [System.StringComparison]::OrdinalIgnoreCase)) {
    Write-Host ""
    Write-Host "note: $SourceRoot is inside the project; remove it when you're done"
}
