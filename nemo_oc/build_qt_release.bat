@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ============================================
echo  NemoOC Qt - Build release
echo ============================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no encontrado en PATH.
    exit /b 1
)

set "TMPROOT=%TEMP%\NemoOC_Qt_build"
set "TMPDIST=%TMPROOT%\dist"
set "TMPBUILD=%TMPROOT%\build"
set "PORTABLE=dist_qt\NemoOC_Qt_portable"

echo [1/5] Instalando dependencias de build...
python -m pip install -r requirements-build.txt
if errorlevel 1 (
    echo ERROR: No se pudieron instalar las dependencias de build.
    exit /b 1
)
echo      OK
echo.

echo [2/5] Limpiando artefactos previos...
if exist "%TMPROOT%" rmdir /s /q "%TMPROOT%"
if exist dist_qt rmdir /s /q dist_qt
if exist release_qt rmdir /s /q release_qt
mkdir "%TMPROOT%" >nul 2>&1
mkdir dist_qt >nul 2>&1
mkdir release_qt >nul 2>&1
echo      OK
echo.

echo [3/5] Compilando ejecutable Qt con PyInstaller...
echo      Build temporal fuera de OneDrive: %TMPROOT%
python -m PyInstaller --noconfirm --clean --distpath "%TMPDIST%" --workpath "%TMPBUILD%" NemoOC_Qt.spec
if errorlevel 1 (
    echo ERROR: Fallo la compilacion con PyInstaller.
    exit /b 1
)
echo      OK
echo.

echo [4/5] Armando carpeta portable...
mkdir "%PORTABLE%" >nul 2>&1
mkdir "%PORTABLE%\data" >nul 2>&1
mkdir "%PORTABLE%\config" >nul 2>&1
mkdir "%PORTABLE%\logs" >nul 2>&1
mkdir "%PORTABLE%\catalogs" >nul 2>&1

copy /Y "%TMPDIST%\NemoOC_Qt.exe" "%PORTABLE%\NemoOC.exe" >nul
copy /Y "assets\nemo_icon.ico" "%PORTABLE%\nemo_icon.ico" >nul

(
echo NemoOC Qt portable
echo.
echo 1. Ejecuta NemoOC.exe
echo 2. La app creara data, config y logs junto al ejecutable
echo 3. Carga tus catalogos desde el modulo Configuracion
echo 4. No requiere Python en el equipo cliente
) > "%PORTABLE%\LEEME.txt"

echo      OK
echo.

echo [5/5] Generando ZIP de distribucion...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path '%PORTABLE%\\*' -DestinationPath 'release_qt\\NemoOC_Qt_portable.zip' -Force"
if errorlevel 1 (
    echo ADVERTENCIA: no se pudo generar el ZIP final, pero la carpeta portable quedo lista.
) else (
    echo      OK
)
echo.
echo ============================================
echo  Listo
echo ============================================
echo Ejecutable: dist_qt\NemoOC_Qt_portable\NemoOC.exe
echo ZIP final : release_qt\NemoOC_Qt_portable.zip
echo.
exit /b 0
