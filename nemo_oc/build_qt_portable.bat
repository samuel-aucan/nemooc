@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
cd /d "%~dp0"

echo.
echo ============================================
echo  NemoOC Qt - Build portable
echo ============================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no encontrado en PATH.
    exit /b 1
)

echo [1/5] Instalando dependencias de build...
python -m pip install -r requirements-build.txt
if errorlevel 1 (
    echo ERROR: No se pudieron instalar las dependencias de build.
    exit /b 1
)
echo      OK
echo.

echo [2/5] Limpiando artefactos previos...
if exist build_qt rmdir /s /q build_qt
if exist dist_qt rmdir /s /q dist_qt
if exist release_qt rmdir /s /q release_qt
mkdir build_qt >nul 2>&1
mkdir dist_qt >nul 2>&1
mkdir release_qt >nul 2>&1
echo      OK
echo.

echo [3/5] Compilando ejecutable Qt con PyInstaller...
python -m PyInstaller --noconfirm --clean --distpath dist_qt --workpath build_qt NemoOC_Qt.spec
if errorlevel 1 (
    echo ERROR: Falló la compilación con PyInstaller.
    exit /b 1
)
echo      OK
echo.

echo [4/5] Armando carpeta portable...
set "PORTABLE=dist_qt\NemoOC_Qt_portable"
mkdir "%PORTABLE%" >nul 2>&1
mkdir "%PORTABLE%\data" >nul 2>&1
mkdir "%PORTABLE%\config" >nul 2>&1
mkdir "%PORTABLE%\logs" >nul 2>&1
mkdir "%PORTABLE%\catalogs" >nul 2>&1

copy /Y "dist_qt\NemoOC_Qt.exe" "%PORTABLE%\NemoOC.exe" >nul
copy /Y "assets\nemo_icon.ico" "%PORTABLE%\nemo_icon.ico" >nul

(
echo NemoOC Qt portable
echo.
echo 1. Ejecuta NemoOC.exe
echo 2. La app creará data, config y logs junto al ejecutable
echo 3. Carga tus catalogos desde el modulo Configuracion
echo 4. No requiere Python en el equipo cliente
) > "%PORTABLE%\LEEME.txt"

echo      OK
echo.

echo [5/5] Generando ZIP de distribucion...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path '%PORTABLE%\\*' -DestinationPath 'release_qt\\NemoOC_Qt_portable.zip' -Force"
if errorlevel 1 (
    echo ADVERTENCIA: no se pudo generar el ZIP final, pero la carpeta portable quedó lista.
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
