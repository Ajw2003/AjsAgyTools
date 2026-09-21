@echo off
setlocal EnableDelayedExpansion

:: 1. Check user override
if defined AGY_PYTHON (
    "%AGY_PYTHON%" "%~dp0hook.py" %*
    exit /b %ERRORLEVEL%
)

:: 2. Check Windows Python Launcher (py.exe)
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    py -3 "%~dp0hook.py" %*
    exit /b %ERRORLEVEL%
)

:: 3. Check python on PATH (verifying it is not a 0-byte Windows Store shim)
where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python -c "import sys; sys.exit(0 if sys.version_info[0] >= 3 else 1)" >nul 2>nul
    if !ERRORLEVEL! EQU 0 (
        python "%~dp0hook.py" %*
        exit /b !ERRORLEVEL!
    )
)

echo house-rules error: Python 3.8+ interpreter not found. >&2
exit /b 1
