# Changelog - NemoOC

Historial de versiones del sistema.

Reglas:
- Cada version debe existir en `VERSION.json`.
- Cada version debe tener entrada en `RESPALDOS/INDICE_RESPALDOS.md`.
- Cada checkpoint debe guardarse en `RESPALDOS/YYYY-MM-DD_vX.Y.Z_descripcion/`.

Formato semantico:
- `Major (X)`: cambio fuerte de arquitectura o producto.
- `Minor (Y)`: bloque de funcionalidades nuevas.
- `Patch (Z)`: correcciones y ajustes sin cambio funcional grande.

## [v1.2.0] 2026-04-16 - Mejoras bandeja web: holdings, precio SAP y filtros

### Correcciones
- Fix critico en `save_oc`: el `INSERT` tenia 40 `?` para 39 columnas y el sync podia fallar silenciosamente.
- `estado_mp` vuelve a recuperarse correctamente al resincronizar desde la API.
- El filtro IMAP de OCs privadas paso de asunto a remitente (`ordenesdecompra@nemochile.cl`).

### Nuevas funcionalidades
- `precio_sap` se redondea a 2 decimales para evitar diferencias al exportar a SAP.
- La bandeja muestra el numero de OC privada sin prefijo, manteniendo el codigo completo en tooltip.
- Se agrega la columna opcional `Holding` para identificar el origen de OCs privadas.
- Se agrega filtro por `Holding` cuando existen OCs privadas con holding asignado.
- Se agrega columna opcional `Ingreso SAP` para mostrar la fecha de ingreso.
- Respaldo asociado: `RESPALDOS/2026-04-16_v1.2.0_mejoras-web-holdings/`

## [v1.1.0] 2026-04-13 - Web local portable sin autenticacion

### Cambios
- Build portable lista para uso local en navegador (`NemoOCWeb.exe`).
- Autenticacion deshabilitada por defecto para uso local unipersonal.
- El detalle de OC muestra neto, IVA y total bruto.
- Respaldo asociado: `RESPALDOS/2026-04-13_checkpoint_web_local_sin_auth/`

## [v1.0.0] 2026-04-03 - Consolidacion modulo Holdings y refactor UX/UI

### Cambios
- Refactor importante de UX/UI web.
- Modulo Holdings consolidado (Red Salud, Indisa, Banmedica, ACHS).
- Sincronizacion y homologacion de OCs privadas desde PDF.
- Respaldo asociado: `RESPALDOS/2026-04-03_estado_actual/`
