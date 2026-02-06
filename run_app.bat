@echo off
REM Script para ejecutar GestionFondosM
echo ========================================
echo   GestionFondosM - Aplicacion Movil
echo ========================================
echo.

REM Activar entorno virtual si existe
if exist .venv\Scripts\activate.bat (
    echo Activando entorno virtual...
    call .venv\Scripts\activate.bat
)

REM Ejecutar aplicacion
echo Iniciando GestionFondosM...
python -m gf_mobile.main

REM Pausar para ver mensajes
pause
