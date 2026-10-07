@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\pythonw.exe" goto run
echo Preparando el entorno (solo la primera vez)...
set PY=python
where python >nul 2>nul || set PY="%USERPROFILE%\miniconda3\python.exe"
%PY% -m venv .venv || goto fail
".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto fail
:run
start "" ".venv\Scripts\pythonw.exe" main.py
exit /b
:fail
echo No se pudo preparar el entorno. Instala Python 3.10+ y vuelve a intentarlo.
pause
