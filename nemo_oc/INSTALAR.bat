@echo off
chcp 65001 >nul 2>&1
title NemoOC - Instalador Automatico
color 1F
cd /d "%~dp0"

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║       NemoOC - Instalador Automatico         ║
echo  ║       Nemo Chile S.A.                        ║
echo  ╚══════════════════════════════════════════════╝
echo.

:: ── Verificar si ya existe Python local ───────────────────
if exist "python\python.exe" (
    echo  [OK] Python local ya instalado.
    goto :INSTALL_DEPS
)

:: ── Verificar si existe Python global ─────────────────────
python --version >nul 2>&1
if not errorlevel 1 (
    echo  [OK] Python del sistema detectado.
    set "PYTHON_CMD=python"
    set "PIP_CMD=pip"
    goto :INSTALL_DEPS_GLOBAL
)

:: ── Descargar Python embebido ─────────────────────────────
echo  [1/5] Python no detectado. Descargando Python portable...
echo         (solo se hace una vez, ~25 MB)
echo.

set "PY_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
set "PY_ZIP=python_embed.zip"
set "PIP_URL=https://bootstrap.pypa.io/get-pip.py"

:: Descargar Python embebido
powershell -Command "try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%PY_URL%', '%PY_ZIP%'); Write-Host '         Descarga completada' } catch { Write-Host '         ERROR: No se pudo descargar Python. Verifica tu conexion a internet.'; exit 1 }"
if errorlevel 1 goto :ERROR_DOWNLOAD
if not exist "%PY_ZIP%" goto :ERROR_DOWNLOAD

:: ── Extraer Python ────────────────────────────────────────
echo.
echo  [2/5] Extrayendo Python portable...
if not exist "python" mkdir python
powershell -Command "Expand-Archive -Path '%PY_ZIP%' -DestinationPath 'python' -Force"
del "%PY_ZIP%" >nul 2>&1
echo         Python extraido en carpeta local

:: ── Habilitar pip en Python embebido ──────────────────────
echo.
echo  [3/5] Configurando pip...

:: Modificar python311._pth para habilitar import site
set "PTH_FILE=python\python311._pth"
if exist "%PTH_FILE%" (
    powershell -Command "(Get-Content '%PTH_FILE%') -replace '#import site','import site' | Set-Content '%PTH_FILE%'"
)

:: Descargar e instalar pip
powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%PIP_URL%', 'get-pip.py')"
python\python.exe get-pip.py --no-warn-script-location >nul 2>&1
del get-pip.py >nul 2>&1
echo         pip instalado correctamente

:INSTALL_DEPS
set "PYTHON_CMD=%~dp0python\python.exe"
set "PIP_CMD=%~dp0python\python.exe -m pip"

:: ── Instalar dependencias ─────────────────────────────────
echo.
echo  [4/5] Instalando dependencias...
echo         (esto puede tardar 1-3 minutos la primera vez)
%PIP_CMD% install -r requirements.txt --no-warn-script-location --quiet 2>nul
if errorlevel 1 (
    echo         Reintentando con mas detalle...
    %PIP_CMD% install -r requirements.txt --no-warn-script-location
    if errorlevel 1 goto :ERROR_DEPS
)
echo         Dependencias instaladas
goto :SETUP_FOLDERS

:INSTALL_DEPS_GLOBAL
echo.
echo  [4/5] Instalando dependencias...
%PIP_CMD% install -r requirements.txt --quiet >nul 2>&1
if errorlevel 1 (
    %PIP_CMD% install -r requirements.txt --user --quiet >nul 2>&1
    if errorlevel 1 goto :ERROR_DEPS
)
echo         Dependencias instaladas

:SETUP_FOLDERS
:: ── Crear carpetas ────────────────────────────────────────
echo.
echo  [5/5] Preparando aplicacion...
if not exist "data" mkdir data
if not exist "config" mkdir config
if not exist "logs" mkdir logs
if not exist "catalogs" mkdir catalogs

:: ── Crear NemoOC.bat inteligente ──────────────────────────
:: Detecta si usar Python local o global
(
echo @echo off
echo cd /d "%%~dp0"
echo if exist "python\python.exe" ^(
echo     python\python.exe app/main.py
echo ^) else ^(
echo     python app/main.py
echo ^)
echo if errorlevel 1 pause
) > NemoOC.bat

:: ── Crear acceso directo en Escritorio ────────────────────
set "SCRIPT=%~dp0NemoOC.bat"
set "ICON=%~dp0assets\nemo_icon.ico"
set "WORKDIR=%~dp0"

powershell -Command "$desktop = [Environment]::GetFolderPath('Desktop'); $sc = (New-Object -ComObject WScript.Shell).CreateShortcut($desktop + '\NemoOC.lnk'); $sc.TargetPath = '%SCRIPT%'; $sc.WorkingDirectory = '%WORKDIR%'; $sc.IconLocation = '%ICON%'; $sc.WindowStyle = 1; $sc.Description = 'NemoOC - Gestion OC Mercado Publico'; $sc.Save()" >nul 2>&1

powershell -Command "Test-Path ([Environment]::GetFolderPath('Desktop') + '\NemoOC.lnk')" | findstr /i "true" >nul 2>&1
if not errorlevel 1 (
    echo         Acceso directo creado en el Escritorio (con icono)
) else (
    echo         Acceso directo: crear manualmente desde NemoOC.bat
)

:: ── Listo ─────────────────────────────────────────────────
echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║                                              ║
echo  ║   Instalacion completada exitosamente!       ║
echo  ║                                              ║
echo  ║   Ya puedes cerrar esta ventana.             ║
echo  ║   Abre NemoOC desde el Escritorio.           ║
echo  ║                                              ║
echo  ║   Primera vez?                               ║
echo  ║   1. Abre la app                             ║
echo  ║   2. Ve a Configuracion                      ║
echo  ║   3. Carga HOMOLOGACION.xlsx                 ║
echo  ║   4. Pega el ticket de API                   ║
echo  ║   5. Ve a Importar y descarga OCs            ║
echo  ║                                              ║
echo  ╚══════════════════════════════════════════════╝
echo.
pause
exit /b 0

:ERROR_DOWNLOAD
echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║  ERROR: No se pudo descargar Python.         ║
echo  ║  Verifica tu conexion a internet.            ║
echo  ╚══════════════════════════════════════════════╝
echo.
pause
exit /b 1

:ERROR_DEPS
echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║  ERROR: No se pudieron instalar las          ║
echo  ║  dependencias. Revisa el error arriba.       ║
echo  ║                                              ║
echo  ║  Posibles causas:                            ║
echo  ║  - Sin conexion a internet                   ║
echo  ║  - Python sin permisos de escritura          ║
echo  ╚══════════════════════════════════════════════╝
echo.
pause
exit /b 1
