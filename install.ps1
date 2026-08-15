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

function Test-GeneratedClaudeSettings($Path) {
    try {
        $settings = [System.IO.File]::ReadAllText($Path) | ConvertFrom-Json
    } catch {
        return $false
    }

    if (-not (Test-ExactKeys $settings @("model", "env", "permissions"))) { return $false }
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
    New-Item -ItemType Directory -Force -Path "$DestinationRoot\.claude\commands", "$DestinationRoot\.claude\bin" | Out-Null
    Get-ChildItem -LiteralPath "$SourceRoot\commands" -File -Filter "cs-*.md" | ForEach-Object {
        Copy-Command $_.FullName "$DestinationRoot\.claude\commands\$($_.Name)" ".claude/bin/plan"
    }
    Copy-Item -LiteralPath "$SourceRoot\bin\plan" -Destination "$DestinationRoot\.claude\bin\plan" -Force
    Copy-Item -LiteralPath "$SourceRoot\bin\plan.cmd" -Destination "$DestinationRoot\.claude\bin\plan.cmd" -Force

    $settingsPath = "$DestinationRoot\.claude\settings.json"
    if (-not (Test-Path -LiteralPath $settingsPath)) {
        $settingsJson = @"
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
  }
}
"@
        [System.IO.File]::WriteAllText($settingsPath, $settingsJson, (New-Object System.Text.UTF8Encoding($false)))
        Write-Host "wrote .claude/settings.json"
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
foreach ($template in @("PLAN.md", "phase.md")) {
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
if ($Agent -ne "codex") { Write-Host "  Claude: .claude\commands\cs-* and .claude\bin\plan" }
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
