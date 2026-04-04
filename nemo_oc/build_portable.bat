@echo off
REM ================================================================
REM  NemoOC - Build Portable para Windows 11
REM  Genera un .exe portable en la carpeta dist/NemoOC_portable/
REM ================================================================
SETLOCAL ENABLEDELAYEDEXPANSION

echo.
echo  ============================================
echo   NemoOC - Generando version portable...
echo  ============================================
echo.

REM -- Verificar Python
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo  ERROR: Python no encontrado en PATH.
    echo  Instale Python 3.11+ desde https://www.python.org
    pause
    exit /b 1
)

REM -- Instalar dependencias
echo  [1/4] Instalando dependencias...
pip install -r requirements.txt --quiet
IF ERRORLEVEL 1 (
    echo  ERROR: Fallo la instalacion de dependencias.
    pause
    exit /b 1
)
echo       OK.
echo.

REM -- Limpiar builds previos
echo  [2/4] Limpiando builds previos...
IF EXIST build RMDIR /S /Q build
IF EXIST dist RMDIR /S /Q dist
IF EXIST NemoOC.spec DEL NemoOC.spec
echo       OK.
echo.

REM -- Generar ejecutable con PyInstaller
echo  [3/4] Compilando con PyInstaller...
python -m PyInstaller ^
    --name NemoOC ^
    --onefile ^
    --windowed ^
    --collect-all customtkinter ^
    --hidden-import tkcalendar ^
    --hidden-import openpyxl ^
    --hidden-import requests ^
    --hidden-import sqlite3 ^
    --add-data "assets;assets" ^
    app/main.py

IF ERRORLEVEL 1 (
    echo.
    echo  ERROR: Fallo la compilacion. Revise los mensajes anteriores.
    pause
    exit /b 1
)
echo       OK.
echo.

REM -- Crear estructura portable
echo  [4/4] Preparando carpeta portable...
SET PORTABLE=dist\NemoOC_portable
MKDIR "%PORTABLE%\data"    2>nul
MKDIR "%PORTABLE%\config"  2>nul
MKDIR "%PORTABLE%\logs"    2>nul

COPY dist\NemoOC.exe "%PORTABLE%\NemoOC.exe" >nul

echo       OK.
echo.
echo  ============================================
echo   Listo! Carpeta portable:
echo   %PORTABLE%\
echo.
echo   Contenido:
echo     NemoOC.exe     <- Ejecutable principal
echo     data/          <- Base de datos SQLite (auto-creada)
echo     config/        <- Configuracion y ticket API
echo     logs/          <- Logs de la aplicacion
echo.
echo   Instrucciones:
echo   1. Copie la carpeta NemoOC_portable a su pendrive
echo   2. Coloque HOMOLOGACION.xlsx junto al ejecutable
echo   3. Ejecute NemoOC.exe
echo   4. Vaya a Configuracion y configure su ticket API
echo  ============================================
echo.
pause
