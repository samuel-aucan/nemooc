# Paquetizado Qt Desktop

Fecha: 2026-04-09

## Objetivo
Empaquetar la nueva desktop Qt de NemoOC como distribución Windows portable, sin tocar la web.

## Recomendación principal
Usar un ejecutable self-contained con `PyInstaller`.

Ventajas:
- no requiere Python instalado en el equipo cliente
- no requiere levantar servidor local
- mantiene `data`, `config`, `logs` y `catalogs` junto al `.exe`
- es la opción más limpia para distribución interna

## Opcion A: Portable final para usuarios
Archivos clave:
- [`build_qt_release.bat`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/build_qt_release.bat)
- [`NemoOC_Qt.spec`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/NemoOC_Qt.spec)
- [`requirements-build.txt`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/requirements-build.txt)

Salida esperada:
- `dist_qt/NemoOC_Qt_portable/NemoOC.exe`
- `release_qt/NemoOC_Qt_portable.zip`
- la compilacion se hace temporalmente en `%TEMP%` para evitar bloqueos de OneDrive sobre el `.exe`

## Opción B: Bootstrap con Python embebido
Archivo clave:
- [`INSTALAR_QT_BOOTSTRAP.bat`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/INSTALAR_QT_BOOTSTRAP.bat)

Este camino sí descarga Python si hace falta. Sirve como plan B para distribuir el código fuente con runtime local, pero no es la opción recomendada para usuarios finales si ya existe el `.exe`.

## Qué incluye el paquete portable
- ejecutable Qt
- carpetas vacías `data`, `config`, `logs`, `catalogs`
- icono y archivo `LEEME.txt`

## Qué no incluye por defecto
- base `app.db`
- credenciales
- catálogos sensibles
- archivos Excel de homologación privados

## Flujo recomendado de distribución
1. Ejecutar [`build_qt_release.bat`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/build_qt_release.bat)
2. Probar `dist_qt/NemoOC_Qt_portable/NemoOC.exe` en un equipo limpio
3. Entregar `release_qt/NemoOC_Qt_portable.zip`
4. Cargar catálogos y credenciales desde la propia app

## Validacion real realizada
Al 2026-04-09 ya se ejecuto una build real con:
- `NemoOC.exe` generado en `dist_qt/NemoOC_Qt_portable`
- ZIP final generado en `release_qt/NemoOC_Qt_portable.zip`
- tamano aproximado del `.exe`: `125 MB`
- tamano aproximado del `.zip`: `124 MB`

## Nota importante
En la versión desktop Qt no se necesita “levantar servidor” para operar. Esa necesidad solo aplicaría a la versión web.
