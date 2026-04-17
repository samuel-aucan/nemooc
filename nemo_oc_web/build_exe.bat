@echo off
cd /d "%~dp0"
echo.
echo ===================================================
echo   NemoOC Web -- Construyendo ejecutable
echo ===================================================
echo.

echo [1/3] Construyendo frontend React...
cd frontend
call npm run build
if errorlevel 1 (
    echo.
    echo ERROR: npm build fallo. Verifica que Node.js este instalado.
    pause
    exit /b 1
)
cd ..
echo     OK: frontend/dist listo

echo.
echo [2/3] Verificando PyInstaller...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo     Instalando PyInstaller...
    pip install "pyinstaller>=6.0"
    if errorlevel 1 (
        echo ERROR: No se pudo instalar PyInstaller.
        pause
        exit /b 1
    )
) else (
    echo     PyInstaller ya instalado.
)

echo.
echo [3/3] Empaquetando con PyInstaller (puede tardar 1-3 minutos)...
set "TEMP_BUILD=%TEMP%\NemoOCWeb_build"
set "TEMP_DIST=%TEMP%\NemoOCWeb_dist"
if exist "%TEMP_BUILD%" rmdir /s /q "%TEMP_BUILD%"
if exist "%TEMP_DIST%" rmdir /s /q "%TEMP_DIST%"
pyinstaller NemoOCWeb.spec --clean --workpath "%TEMP_BUILD%" --distpath "%TEMP_DIST%"
if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller fallo. Revisa los mensajes anteriores.
    pause
    exit /b 1
)

if not exist dist mkdir dist
copy /y "%TEMP_DIST%\NemoOCWeb.exe" "dist\NemoOCWeb.exe" >nul
if errorlevel 1 (
    echo.
    echo AVISO: NemoOCWeb.exe esta en uso. Guardando build alternativa...
    copy /y "%TEMP_DIST%\NemoOCWeb.exe" "dist\NemoOCWeb_new.exe" >nul
    if errorlevel 1 (
        echo ERROR: No se pudo copiar el ejecutable final ni como alternativo.
        pause
        exit /b 1
    )
)

if exist dist\data rmdir /s /q dist\data
if exist dist\config rmdir /s /q dist\config
if exist dist\logs rmdir /s /q dist\logs
if exist dist\catalogs rmdir /s /q dist\catalogs

mkdir dist\data
mkdir dist\config
mkdir dist\logs
mkdir dist\catalogs

copy /y "..\nemo_oc\config\default_settings.json" "dist\config\default_settings.json" >nul
copy /y "..\VERSION.json" "dist\VERSION.json" >nul

xcopy /e /i /y "..\nemo_oc\catalogs\*" "dist\catalogs\" >nul
if exist "..\lic.xlsx" copy /y "..\lic.xlsx" "dist\catalogs\lic.xlsx" >nul

echo.
echo ===================================================
echo   BUILD EXITOSO!
echo.
echo   Ejecutable principal: dist\NemoOCWeb.exe
echo   Si estaba en uso:      dist\NemoOCWeb_new.exe
echo.
echo   Para distribuir: copia la carpeta dist completa.
echo   Incluye el .exe, config\default_settings.json y
echo   catalogs\ para auto-configurar la primera ejecucion.
echo ===================================================
echo.
pause
