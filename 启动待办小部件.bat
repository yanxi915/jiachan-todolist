@echo off
rem PeekTodo launcher - start with pythonw (no console window)
setlocal
set "ROOT=%~dp0"
set "PYW="

rem 1) prefer the py launcher to locate pythonw.exe
for /f "delims=" %%i in ('py -3 -c "import sys,os;print(os.path.join(os.path.dirname(sys.executable),'pythonw.exe'))" 2^>nul') do set "PYW=%%i"

rem 2) fall back to PATH
if not defined PYW for /f "delims=" %%i in ('where pythonw 2^>nul') do set "PYW=%%i"

if not defined PYW (
    echo [ERROR] pythonw.exe not found. Install Python 3 and add it to PATH.
    pause
    exit /b 1
)

start "" "%PYW%" "%ROOT%app\main.py"
exit /b 0
