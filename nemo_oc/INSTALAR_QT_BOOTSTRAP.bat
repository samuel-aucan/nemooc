@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
cd /d "%~dp0"

echo.
echo ============================================
echo  NemoOC Qt - Bootstrap portable
echo ============================================
echo.

if exist "python\python.exe" (
    set "PYTHON_CMD=%~dp0python\python.exe"
    set "PIP_CMD=%~dp0python\python.exe -m pip"
    goto :INSTALL_DEPS
)

python --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    set "PIP_CMD=python -m pip"
    goto :INSTALL_DEPS
)

echo [1/4] Python no detectado. Descargando runtime embebido...
set "PY_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
set "PY_ZIP=python_embed.zip"
set "PIP_URL=https://bootstrap.pypa.io/get-pip.py"

powershell -NoProfile -ExecutionPolicy Bypass -Command "try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%PY_URL%', '%PY_ZIP%'); } catch { exit 1 }"
if errorlevel 1 goto :ERROR_DOWNLOAD

mkdir python >nul 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path '%PY_ZIP%' -DestinationPath 'python' -Force"
del "%PY_ZIP%" >nul 2>&1

set "PTH_FILE=python\python311._pth"
if exist "%PTH_FILE%" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "(Get-Content '%PTH_FILE%') -replace '#import site','import site' | Set-Content '%PTH_FILE%'"
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%PIP_URL%', 'get-pip.py'); } catch { exit 1 }"
if errorlevel 1 goto :ERROR_DOWNLOAD

python\python.exe get-pip.py --no-warn-script-location
if errorlevel 1 goto :ERROR_DEPS
del get-pip.py >nul 2>&1

set "PYTHON_CMD=%~dp0python\python.exe"
set "PIP_CMD=%~dp0python\python.exe -m pip"

:INSTALL_DEPS
echo [2/4] Instalando dependencias...
%PIP_CMD% install -r requirements.txt
if errorlevel 1 goto :ERROR_DEPS

echo [3/4] Preparando carpetas locales...
if not exist "data" mkdir data
if not exist "config" mkdir config
if not exist "logs" mkdir logs
if not exist "catalogs" mkdir catalogs

(
echo @echo off
echo cd /d "%%~dp0"
echo if exist "python\python.exe" ^(
echo     python\python.exe app_qt\main.py
echo ^) else ^(
echo     python app_qt\main.py
echo ^)
echo if errorlevel 1 pause
) > NemoOC_Qt.bat

echo [4/4] Listo.
echo Ejecuta NemoOC_Qt.bat para abrir la app Qt.
echo.
exit /b 0

:ERROR_DOWNLOAD
echo ERROR: No se pudo descargar Python o pip.
exit /b 1

:ERROR_DEPS
echo ERROR: No se pudieron instalar las dependencias.
exit /b 1
