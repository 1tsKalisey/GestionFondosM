@echo off
REM Script para ejecutar GestionFondosM
echo ========================================
echo   GestionFondosM - Aplicacion Movil
echo ========================================
echo.

set "ROOT=%~dp0"
set "PYTHON_EXE=python"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "KIVY_NO_FILELOG=1"

REM Usar SIEMPRE el Python del .venv local si existe
if exist "%ROOT%.venv\Scripts\python.exe" (
    echo Usando Python del entorno virtual local...
    set "PYTHON_EXE=%ROOT%.venv\Scripts\python.exe"
) else (
    echo ADVERTENCIA: no se encontro .venv\Scripts\python.exe. Usando Python global.
)

REM Ejecutar aplicacion
echo Iniciando GestionFondosM...
pushd "%ROOT%src"
"%PYTHON_EXE%" -m gf_mobile.main
popd

REM Pausar para ver mensajes
pause
