@echo off
rem PostToolUse Edit|Write -- surface a phase-file shape error on the
rem write that caused it, rather than at the next review round.
rem
rem Windows half of the pair, and the one this project's installer registers
rem there. Same contract as the .sh: forward the event JSON on stdin to
rem `plan guard` and return its exit code. PowerShell cannot run the
rem extension-less `plan`, so this calls plan.cmd, exactly as the installed
rem commands do, from the project root so that `plan` resolves PLAN.md
rem relative to it rather than from an exported path.
setlocal
for %%I in ("%~dp0..\..") do set "PROJECT=%%~fI"
if not exist "%PROJECT%\.claude\bin\plan.cmd" exit /b 0
cd /d "%PROJECT%" || exit /b 0
rem %ERRORLEVEL% is expanded at parse time inside a parenthesised block, so
rem the exit must stay on its own line. `plan guard` exits 2 to block and 0
rem to allow, and the hook relies on that reaching Claude Code intact.
call ".claude\bin\plan.cmd" guard lint
exit /b %ERRORLEVEL%
