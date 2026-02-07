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
set "ROOT=%~dp0"
pushd "%ROOT%src"
python -m gf_mobile.main
popd

REM Pausar para ver mensajes
pause
