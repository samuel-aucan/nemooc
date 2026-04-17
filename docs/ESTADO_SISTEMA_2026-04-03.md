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

Desde el 4 de abril de 2026 tambien queda tomada y documentada la decision de evolucionar la version desktop hacia una nueva interfaz en Qt, manteniendo la web intacta como referencia funcional y la desktop actual como respaldo temporal.

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

## Estado migracion desktop Qt
- Decision tomada y documentada en:
  [`DECISION_DESKTOP_UI_2026-04-04.md`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/DECISION_DESKTOP_UI_2026-04-04.md)
- Plan operativo detallado en:
  [`PLAN_MIGRACION_DESKTOP_QT_2026-04-04.md`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/PLAN_MIGRACION_DESKTOP_QT_2026-04-04.md)
- Base tecnica nueva creada en:
  [`nemo_oc/app_qt`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/app_qt)
- Preview de arranque disponible en:
  [`nemo_oc/app_qt/main.py`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/app_qt/main.py)
  [`nemo_oc/NemoOC_QtPreview.bat`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/NemoOC_QtPreview.bat)
- Fase 1 iniciada:
  shell Qt con sidebar, topbar, branding y home con metricas reales de la base.
- Bandeja Qt inicial ya disponible:
  filtros, `QTableView`, splitter vertical y detalle inferior con lineas reales.
- Ajuste del 4 de abril de 2026 sobre la bandeja Qt:
  el detalle inferior ya permite cambiar `estado interno`, guardar `notas internas`,
  marcar una OC como `Ingresada` y copiar el texto homologado para SAP.
- Validacion real de la preview Qt al 4 de abril de 2026:
  arranque correcto en modo offscreen, `493` OCs cargadas desde la base y
  detalle activo sobre la OC seleccionada.
- Mejora visual y operativa del mismo dia en Qt:
  badges dentro de las tablas para estados clave y un inspector inferior de linea
  seleccionada con `Codigo MP`, homologacion, cantidades, `ItemCode SAP` y descripciones.
- Avance adicional del 4 de abril de 2026 en Qt:
  el modulo `Importaciones` ya existe como pantalla real con rango de fechas,
  botones rapidos, `Prueba rapida API`, sync de Mercado Publico, sync privado por Gmail,
  barra de progreso y bitacora con carga de log reciente.
- Validacion funcional del modulo `Importaciones` en Qt:
  arranque correcto en modo offscreen y prueba rapida real de Mercado Publico
  devolviendo `API operativa`.
- Avance adicional del 4 de abril de 2026 en Qt:
  el modulo `Configuracion` ya existe como pantalla real con:
  credenciales MP, prueba rapida API, SMTP, prueba de correo, IMAP, auto-sync,
  rutas de catalogos, cargas reales de archivos y apertura de carpetas locales.
- Validacion funcional del modulo `Configuracion` en Qt:
  arranque correcto en modo offscreen, lectura real de `settings.json`,
  6 rutas de catalogos visibles y resumen cargado desde la base local.
- Avance adicional del 4 de abril de 2026 en Qt:
  el modulo `Holdings` ya existe como pantalla real con listado, identidad del holding,
  RUTs compradores, busqueda en cartera, correos esperados, reglas avanzadas
  e importacion de catalogo privado por holding.
- Validacion funcional del modulo `Holdings` en Qt:
  arranque correcto en modo offscreen, lectura real de `5` holdings desde la base
  y detalle activo sobre `achs` con `4` RUTs y `3` reglas.
- Avance adicional del 4 de abril de 2026 en Qt:
  el modulo `Estadisticas y revision` ya existe como pantalla real con:
  rango de fechas, metricas compactas, cola experta, aceptacion directa de sugerencias,
  revision activa de linea, sugerencias del motor con estrellas, busqueda manual en maestra
  y limpieza de asignacion en la misma vista.
- Validacion funcional del modulo `Estadisticas y revision` en Qt:
  arranque correcto en modo offscreen, carga real de resumen y cola,
  `17` lineas visibles bajo el filtro `Pendientes` en la prueba de humo,
  y detalle activo sobre la linea `899-198-SE26 / 1`.
- Avance adicional del 4 de abril de 2026 en Qt:
  el modulo `Usuarios` ya existe como pantalla real con:
  alta de usuarios, listado, edicion de rol y estado, reseteo directo de contraseña
  y reinicio de acceso con token temporal copiable.
- Validacion funcional del modulo `Usuarios` en Qt:
  arranque correcto en modo offscreen, lectura real del usuario `admin`
  desde la base local y editor cargando correctamente la cuenta seleccionada.
- Alineacion contra el plan Qt:
  la preview actual ya no corresponde a `Fase 1`.
  En realidad existe una preview operativa con modulos funcionales de las fases 2 a 8,
  mientras el `Empaquetado` ya inicia su base real pero aun no cierra del todo.
- Estado resumido por fases del roadmap Qt:
  `Fase 0` completada,
  `Fase 1` completada en base funcional,
  `Fase 2` implementada en primera version operativa,
  `Fases 3 a 8` implementadas en primera version operativa,
  `Fase 9` iniciada con build real validada.
- Avance adicional del 4 de abril de 2026 en Qt:
  la `Fase 2` ya existe como flujo local de acceso con:
  login por usuario y contraseña,
  creacion del primer administrador cuando la base no tiene usuarios,
  activacion de acceso por token temporal,
  sesion en memoria y cierre de sesion desde la propia shell Qt.

 - Ajuste adicional del 4 de abril de 2026 en Qt:
   saneamiento visual transversal sobre `Ordenes`, `Holdings` y `Usuarios` para reducir recortes.
   En concreto:
   - `Ordenes` deja de mostrar metricas superiores propias
   - la tabla principal y la tabla de lineas usan anchos mas flexibles
   - `Holdings` y `Usuarios` incorporan paneles scrolleables en sus zonas mas densas
- Avance adicional del 9 de abril de 2026 en Qt:
  arranca la Fase 9 de empaquetado con:
  - spec Qt dedicado
  - requirements de build separados
  - build release recomendado
  - bootstrap con Python embebido como plan B
  - guia propia de empaquetado
- Validacion real de empaquetado Qt al 9 de abril de 2026:
  build exitosa con salida:
  - [`nemo_oc/dist_qt/NemoOC_Qt_portable/NemoOC.exe`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/dist_qt/NemoOC_Qt_portable/NemoOC.exe)
  - [`nemo_oc/release_qt/NemoOC_Qt_portable.zip`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/release_qt/NemoOC_Qt_portable.zip)
  y workaround confirmado:
  la compilacion debe hacerse temporalmente fuera de OneDrive para evitar bloqueos de Windows sobre el `.exe`.

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
