@echo off
cd /d "%~dp0"
echo ==========================================
echo   REGISTRO DE OPERATIVA - gabomondo
echo ==========================================
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no encontrado.
    pause & exit /b 1
)
rem Solo instala dependencias si faltan
python -c "import customtkinter, PIL" >nul 2>&1
if errorlevel 1 pip install -r requirements.txt --quiet
python registro_operativa.py %*
if errorlevel 1 pause
