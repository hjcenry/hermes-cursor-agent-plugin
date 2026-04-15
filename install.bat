@echo off
setlocal EnableExtensions
REM Install Hermes cursor_agent plugin into %USERPROFILE%\.hermes\plugins\cursor-agent
REM Optionally create %USERPROFILE%\.hermes\cursor_agent.json from example if missing.
REM Usage: install.bat   (run from this directory)

set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
if not defined HERMES_HOME set "HERMES_HOME=%USERPROFILE%\.hermes"
set "DEST=%HERMES_HOME%\plugins\cursor-agent"
set "CFG=%HERMES_HOME%\cursor_agent.json"
set "EXAMPLE=%SCRIPT_DIR%\cursor_agent.example.json"

if not exist "%SCRIPT_DIR%\plugin.yaml" (
  echo error: plugin.yaml not found under %SCRIPT_DIR% >&2
  exit /b 1
)
if not exist "%SCRIPT_DIR%\__init__.py" (
  echo error: __init__.py not found under %SCRIPT_DIR% >&2
  exit /b 1
)

if not exist "%HERMES_HOME%" mkdir "%HERMES_HOME%"
if not exist "%DEST%" mkdir "%DEST%"

for %%F in (
  plugin.yaml __init__.py config.py parser.py formatter.py
  resolve_binary.py process_registry.py runner.py
  TECHNICAL_DESIGN.md .gitignore cursor_agent.example.json
) do (
  if exist "%SCRIPT_DIR%\%%F" copy /Y "%SCRIPT_DIR%\%%F" "%DEST%\" >nul
)

echo Installed plugin to: %DEST%

if exist "%CFG%" (
  echo Config already exists (not overwritten^): %CFG%
) else (
  if exist "%EXAMPLE%" (
    copy /Y "%EXAMPLE%" "%CFG%" >nul
    echo Created config from example: %CFG%
    echo   Edit "projects" and paths before use.
  ) else (
    echo No example JSON found; create manually: %CFG%
  )
)

echo Restart Hermes Gateway / CLI to load the plugin.
endlocal
exit /b 0
