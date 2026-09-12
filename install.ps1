# Shared recoverable upgrade flow. Default action is a saved preview.
param(
    [Parameter(Position = 0)][string]$Target = ".",
    [ValidateSet("claude", "codex", "both")][string]$Agent = "both",
    [switch]$Preview,
    [string]$Apply,
    [switch]$Recover,
    [string]$Baseline,
    [switch]$Keep
)
$ErrorActionPreference = "Stop"
$pythonCommand = $null
foreach ($candidate in @("python3", "python", "py")) {
    $found = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($found) {
        try {
            & $found.Source -c "import sys; assert sys.version_info >= (3, 9)" 2>$null
            if ($LASTEXITCODE -eq 0) { $pythonCommand = $found.Source; break }
        } catch {}
    }
}
if (-not $pythonCommand) { throw "Python 3.9+ is required" }
$installArgs = @((Join-Path $PSScriptRoot "bin/cs_install.py"), $Target, "--agent", $Agent, "--windows")
if ($Preview) { $installArgs += "--preview" }
if ($Apply) { $installArgs += @("--apply", $Apply) }
if ($Recover) { $installArgs += "--recover" }
if ($Baseline) { $installArgs += @("--baseline", $Baseline) }
if ($Keep) { $installArgs += "--keep" }
& $pythonCommand @installArgs
exit $LASTEXITCODE
