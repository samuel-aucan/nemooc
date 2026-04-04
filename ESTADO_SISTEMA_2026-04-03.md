# Estado del Sistema

Fecha: 2026-04-03  
Hora de corte: 19:05:00  
Documento relacionado: [RESPALDOS/2026-04-03_estado_actual/MANIFIESTO_RESPALDO.md](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/RESPALDOS/2026-04-03_estado_actual/MANIFIESTO_RESPALDO.md)

## Resumen ejecutivo
Al 3 de abril de 2026 el sistema web de NemoOC tiene un refactor UX/UI importante aplicado, con foco en velocidad operativa, claridad visual y mejor navegacion para usuarios de escritorio.

La pantalla principal mantiene la bandeja de OCs en la parte superior y el detalle en la parte inferior, mientras que los filtros quedaron archivados en un panel lateral plegable. El modulo Holdings ya concentra gran parte de la configuracion de privados, incluyendo RUTs, correos esperados y carga de catalogo por holding.

Tambien existe un modulo nuevo de `Estadisticas y revision`, orientado a trabajo experto. Este modulo muestra cobertura por lineas y monto, cantidad de pendientes con y sin sugerencia, y una cola de correccion inline para revisar lineas sin salir a otra pantalla.

Desde este mismo corte, la web queda preparada para acceso protegido por usuario y contraseña, con sesion por cookie. Si no existen usuarios, la primera entrada obliga a crear el administrador inicial.
Una vez creado ese primer admin, el control de accesos pasa al modulo `Usuarios`, sin registro publico.

## Estado visual y UX
- Look general renovado:
  tipografia mas legible, componentes mas consistentes, mejor espaciado y estados visuales mas claros.
- Sidebar redisenado:
  navegacion mas explicita, estado del sistema visible y firma `Desarrollado por Samuel Belmar`.
- Status bar mejorado:
  totales resumidos en chips mas legibles.
- Lista principal:
  bandeja arriba, detalle abajo, filtros laterales compactos y plegables.
- Importaciones:
  feedback mas claro para API, sincronizaciones y bitacora.
- Configuracion:
  separada por secciones de trabajo.
- Holdings:
  configuracion simplificada y mas centralizada.
- Usuarios:
  modulo administrativo para crear accesos, activar/desactivar usuarios, resetear contraseñas y reiniciar acceso con token temporal.
- Detalle de OC:
  mejor jerarquia visual, acciones mas claras y notas con guardado explicito.
- Estadisticas y revision:
  modulo nuevo con metricas operativas y cola de sugerencias/correcciones editable dentro de la misma tabla.
- Seguridad web:
  login propio con usuario/contraseña, sesion protegida y bootstrap del primer administrador.

## Estado operativo conocido
- Frontend web:
  [`nemo_oc_web/frontend`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc_web/frontend)
- Backend web:
  [`nemo_oc_web/backend`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc_web/backend)
- Logica principal app:
  [`nemo_oc/app`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/app)
- Base actual:
  [`nemo_oc/data/app.db`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/data/app.db)
- Puertos de trabajo:
  frontend `5173`, backend `8001`.

## Estado Git
- Desde el 4 de abril de 2026 el proyecto queda preparado para un repositorio Git raiz en:
  [`INGRESO OC`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC)
- El historial Git antiguo de la app desktop `nemo_oc` fue respaldado antes de la migracion en:
  [`RESPALDOS/2026-04-04_git_historial/nemo_oc_history.bundle`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/RESPALDOS/2026-04-04_git_historial/nemo_oc_history.bundle)
- Tambien se guardaron el estado y log del repo anterior en:
  [`RESPALDOS/2026-04-04_git_historial/nemo_oc_status_pre_migracion.txt`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/RESPALDOS/2026-04-04_git_historial/nemo_oc_status_pre_migracion.txt)
  [`RESPALDOS/2026-04-04_git_historial/nemo_oc_log_pre_migracion.txt`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/RESPALDOS/2026-04-04_git_historial/nemo_oc_log_pre_migracion.txt)
- Quedan fuera de versionado por seguridad o tamano:
  bases SQLite, logs, backups, `node_modules`, builds y la carpeta de muestras `ocs prueba`.

## Holdings en base al snapshot
Los datos siguientes salen de la base `app.db` congelada en este corte:

- `achs`
  nombre: Asociacion Chilena de Seguridad
  prefijo: `AC`
  parser: `achs`
  activo: `si`
  RUTs: `4`
  reglas: `3`
  catalogo privado: `0`

- `banmedica`
  nombre: Banmedica
  prefijo: `BM`
  parser: `banmedica`
  activo: `si`
  RUTs: `5`
  reglas: `7`
  catalogo privado: `1`

- `clinicas_regionales`
  nombre: Red de Clinicas Regionales
  prefijo: `CR`
  parser: vacio
  activo: `no`
  RUTs: `7`
  reglas: `0`
  catalogo privado: `0`

- `indisa`
  nombre: Clinica Indisa
  prefijo: `IN`
  parser: `indisa`
  activo: `si`
  RUTs: `1`
  reglas: `3`
  catalogo privado: `0`

- `redsalud`
  nombre: Red Salud
  prefijo: `RS`
  parser: `redsalud`
  activo: `si`
  RUTs: `9`
  reglas: `10`
  catalogo privado: `47`

## Observaciones importantes del corte
- El snapshot captura tambien la configuracion viva de holdings y reglas en la base.
- `clinicas_regionales` existe pero sigue inactivo.
- En este corte, `banmedica` aparece con solo `1` item en `homologacion_privados`.
- En este corte, `achs` no aparece aun con catalogo privado cargado dentro de `homologacion_privados`.
- `redsalud` conserva `47` registros en catalogo privado.
- El modulo `Estadisticas` ya consume un endpoint propio `/api/ocs/analytics`.
- La cola experta de Estadisticas permite:
  ver el detalle de la linea,
  cargar sugerencias historicas,
  buscar en maestra,
  asignar o limpiar itemcode SAP sin abrir el detalle completo de la OC.
- Ajuste del mismo dia `2026-04-03` sobre Estadisticas:
  la aceptacion directa de sugerencias ahora distingue `sugerencia` vs `manual` en el resumen optimista,
  y la correccion manual solo se habilita cuando el itemcode fue seleccionado desde la maestra.

## Documentos utiles asociados
- [README.md](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/README.md)
- [MANUAL_REENVIO_AUTOMATICO_OCS_PRIVADAS.md](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/MANUAL_REENVIO_AUTOMATICO_OCS_PRIVADAS.md)
- [RESPALDOS/INDICE_RESPALDOS.md](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/RESPALDOS/INDICE_RESPALDOS.md)

## Para buscar despues
Cuando quieras retomar este punto en el futuro, busca primero:
1. [`ESTADO_SISTEMA_2026-04-03.md`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/ESTADO_SISTEMA_2026-04-03.md)
2. [`RESPALDOS/INDICE_RESPALDOS.md`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/RESPALDOS/INDICE_RESPALDOS.md)
3. [`RESPALDOS/2026-04-03_estado_actual`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/RESPALDOS/2026-04-03_estado_actual)
