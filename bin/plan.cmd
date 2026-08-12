@echo off
rem Windows entry point for the plan tool.
rem
rem `plan` itself is an extension-less Python file with a shebang. POSIX
rem shells and Git Bash run that directly; PowerShell cannot run an
rem extension-less file at all, and refuses with "Cannot run a document".
rem This shim is what the commands call on Windows, and it works from
rem PowerShell, cmd.exe, and Git Bash alike.
setlocal
set "PLAN_PY="
where python3 >nul 2>nul && set "PLAN_PY=python3"
if not defined PLAN_PY (
  where python >nul 2>nul && set "PLAN_PY=python"
)
if not defined PLAN_PY (
  where py >nul 2>nul && set "PLAN_PY=py"
)
if not defined PLAN_PY (
  echo python3 is required, and is not on PATH 1>&2
  exit /b 127
)
rem %ERRORLEVEL% is expanded at parse time inside a parenthesised block, so
rem the exit must stay on its own line. `plan lint` exits 1 on error and
rem scripts rely on that.
%PLAN_PY% "%~dp0plan" %*
exit /b %ERRORLEVEL%
