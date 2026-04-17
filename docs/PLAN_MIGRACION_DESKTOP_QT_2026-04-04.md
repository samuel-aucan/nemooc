# Plan de Migracion Desktop a Qt

Fecha: 2026-04-04  
Decision asociada: [`DECISION_DESKTOP_UI_2026-04-04.md`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/DECISION_DESKTOP_UI_2026-04-04.md)  
Baseline Git: `2e22689`

## Estado actual de avance
### 2026-04-04
La Fase 0 queda iniciada con base tecnica real:
- creada la carpeta `app_qt`
- creado el entrypoint [`nemo_oc/app_qt/main.py`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/app_qt/main.py)
- creado el bootstrap minimo [`nemo_oc/app_qt/bootstrap.py`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/app_qt/bootstrap.py)
- creada una shell Qt funcional con sidebar, stack de paginas y status bar
- iniciada la Fase 1 con:
  - topbar contextual
  - branding lateral
  - tarjetas de estado
  - home con metricas reales de base
  - placeholders enriquecidos para los modulos futuros
- adelantada parcialmente la Fase 3 con una primera bandeja real en:
  [`nemo_oc/app_qt/pages/oc_list_page.py`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/app_qt/pages/oc_list_page.py)
  usando:
  [`nemo_oc/app_qt/models/oc_table_model.py`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/app_qt/models/oc_table_model.py)
  [`nemo_oc/app_qt/models/oc_table_proxy.py`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/app_qt/models/oc_table_proxy.py)
  [`nemo_oc/app_qt/models/lineas_table_model.py`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/app_qt/models/lineas_table_model.py)
- la bandeja ya incluye:
  - filtros compactos
  - `QSplitter` vertical
  - `QTableView` superior
  - detalle inferior con lineas reales
  - metricas de resumen
- la bandeja ya ejecuta acciones reales sobre la OC seleccionada:
  - cambio de `estado interno`
  - guardado de `notas internas`
  - accion `Copiar para SAP`
  - marcado manual de `Ingresada`
- mejora visual ya aplicada sobre la bandeja Qt:
  - badges pintados dentro de tablas para `estado interno`, `tipo`, `estado MP` y `estado homologacion`
  - panel inferior de inspeccion para la `linea seleccionada`
  - metadata de lineas visibles y seleccion automatica de la primera linea
- la Fase 4 ya tiene base funcional real en:
  [`nemo_oc/app_qt/pages/import_page.py`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/app_qt/pages/import_page.py)
  con:
  - rango de fechas
  - atajos `Hoy`, `7 dias`, `30 dias`, `90 dias`
  - tipos de OC `CM` y `Otras`
  - `Prueba rapida API`
  - sincronizacion Mercado Publico
  - sincronizacion Gmail para privados
  - progreso y bitacora en la misma vista
  - carga de log reciente desde `app.log`
- validacion tecnica actual:
  - `py_compile` correcto para la capa Qt activa
  - preview Qt iniciada en modo offscreen
  - lectura real de `493` OCs en la base local al momento de la prueba
  - detalle inferior cargando lineas y habilitando acciones segun la OC seleccionada
  - inspector de linea activo con `itemcode SAP` y descripciones reales de la linea seleccionada
  - modulo `Importaciones` iniciando correctamente en Qt
  - prueba rapida real de Mercado Publico devolviendo `API operativa`
- creados placeholders de modulos para `Ordenes`, `Importaciones`, `Estadisticas`, `Holdings`, `Usuarios` y `Configuracion`
- agregado `PySide6` a [`nemo_oc/requirements.txt`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/requirements.txt)
- validado arranque de la preview Qt en modo offscreen

### Lectura honesta contra el roadmap original
- La preview Qt ya esta **mucho mas avanzada que Fase 1**.
- Hoy existen primeras versiones funcionales de:
  - Fase 2 `Login y sesion local`
  - Fase 3 `Ordenes de compra`
  - Fase 4 `Importaciones`
  - Fase 5 `Configuracion`
  - Fase 6 `Holdings`
  - Fase 7 `Estadisticas y revision`
  - Fase 8 `Usuarios`
- La parte **todavia no cerrada** respecto al orden ideal del plan es:
  - Fase 9 `Empaquetado y distribucion`
- Por eso la UI **no debe seguir mostrando `Fase 1`**: el estado real es `Preview operativa`, con `Fase 2` cerrada y packaging aun pendiente.

### Matriz honesta por fases
- `Fase 0. Preparacion de arquitectura`: completada
- `Fase 1. Shell principal y sistema visual`: completada en base funcional
- `Fase 2. Login y sesion local`: implementada en primera version operativa
- `Fase 3. Ordenes de compra`: implementada en primera version operativa
- `Fase 4. Importaciones`: implementada en primera version operativa
- `Fase 5. Configuracion`: implementada en primera version operativa
- `Fase 6. Holdings`: implementada en primera version operativa
- `Fase 7. Estadisticas y revision experta`: implementada en primera version operativa
- `Fase 8. Usuarios y seguridad operativa`: implementada en primera version operativa
- `Fase 9. Empaquetado y distribucion`: iniciada con build real validada

### Conclusion de roadmap
- La migracion Qt **no esta en Fase 1**.
- Tampoco esta estrictamente "en orden" respecto al roadmap original.
- Lo que hicimos fue adelantar los modulos operativos mas valiosos primero.
- Eso explica por que hoy existen muchos detalles visuales y de consistencia: ya cerramos `Fase 2`, pero aun falta una pasada de estabilizacion transversal antes de `Fase 9` empaquetado.
- Ajuste de estabilizacion visual del 4 de abril de 2026:
  - `Ordenes` deja de mostrar metricas propias en la parte superior
  - la bandeja principal y la tabla de lineas pasan a usar anchos mas elasticos
  - `Holdings` y `Usuarios` pasan a usar paneles editables con scroll para evitar recortes verticales

### 2026-04-09
La Fase 9 deja de estar solo pendiente y pasa a tener base real:
- creado el spec Qt [`nemo_oc/NemoOC_Qt.spec`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/NemoOC_Qt.spec)
- creado el build recomendado [`nemo_oc/build_qt_release.bat`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/build_qt_release.bat)
- creado el bootstrap con Python embebido [`nemo_oc/INSTALAR_QT_BOOTSTRAP.bat`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/INSTALAR_QT_BOOTSTRAP.bat)
- creada la guia [`nemo_oc/PAQUETIZADO_QT_2026-04-09.md`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/PAQUETIZADO_QT_2026-04-09.md)
- se ejecuto una build real exitosa
  - salida portable: `dist_qt/NemoOC_Qt_portable/NemoOC.exe`
  - zip final: `release_qt/NemoOC_Qt_portable.zip`
  - workaround confirmado: compilar temporalmente fuera de OneDrive

### Cierre de Fase 2
- Se agrego acceso local para la preview Qt con:
  - `login` normal por usuario y contraseña
  - creacion del primer administrador si la base no tiene usuarios
  - activacion de acceso con token temporal
  - sesion en memoria dentro del contexto Qt
  - cierre de sesion y reingreso sin tocar la web
- Referencias:
  - [`nemo_oc/app_qt/auth/login_dialog.py`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/app_qt/auth/login_dialog.py)
  - [`nemo_oc/app/services/user_admin_service.py`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/app/services/user_admin_service.py)
  - [`nemo_oc/app_qt/bootstrap.py`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/app_qt/bootstrap.py)

Comando de arranque actual:

```bash
cd nemo_oc
python app_qt/main.py
```

Acceso rapido en Windows:
- [`nemo_oc/NemoOC_QtPreview.bat`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/NemoOC_QtPreview.bat)

## Objetivo
Crear una nueva version desktop de NemoOC con **PySide6 + Qt Widgets**, manteniendo:
- la logica de negocio actual
- la version web intacta
- la desktop actual en `CustomTkinter` como respaldo temporal

El resultado esperado es una app desktop con look mucho mejor, mas productiva y lista para operar como producto principal sin depender de hosting web.

## Restricciones duras
### No tocar la web
La carpeta [`nemo_oc_web`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc_web) se usa solo como referencia funcional y visual.

### No romper la desktop actual
La carpeta [`nemo_oc/app/ui`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/app/ui) debe seguir funcionando mientras se construye la nueva interfaz Qt.

### No duplicar logica de negocio
La logica debe seguir viviendo en:
- [`nemo_oc/app/config.py`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/app/config.py)
- [`nemo_oc/app/db.py`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/app/db.py)
- [`nemo_oc/app/models`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/app/models)
- [`nemo_oc/app/repositories`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/app/repositories)
- [`nemo_oc/app/services`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/app/services)

## Mapa funcional actual
### Desktop actual
Hoy la desktop solo tiene shell y modulos visibles para:
- lista de OCs
- detalle de OC
- importacion
- configuracion

Archivos base actuales:
- [`nemo_oc/app/main.py`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/app/main.py)
- [`nemo_oc/app/ui/app_window.py`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/app/ui/app_window.py)
- [`nemo_oc/app/ui/frames/oc_list_frame.py`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/app/ui/frames/oc_list_frame.py)
- [`nemo_oc/app/ui/frames/oc_detail_frame.py`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/app/ui/frames/oc_detail_frame.py)
- [`nemo_oc/app/ui/frames/import_frame.py`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/app/ui/frames/import_frame.py)
- [`nemo_oc/app/ui/frames/config_frame.py`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/app/ui/frames/config_frame.py)

### Web como referencia
La web ya modela una estructura funcional mas completa:
- login
- bandeja principal
- detalle
- importaciones
- estadisticas y revision
- holdings
- usuarios
- configuracion

Referencias clave:
- [`nemo_oc_web/frontend/src/App.tsx`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc_web/frontend/src/App.tsx)
- [`nemo_oc_web/frontend/src/components/layout/Sidebar.tsx`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc_web/frontend/src/components/layout/Sidebar.tsx)
- [`nemo_oc_web/frontend/src/components/oc-list/OcListPage.tsx`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc_web/frontend/src/components/oc-list/OcListPage.tsx)
- [`nemo_oc_web/frontend/src/components/import-page/ImportPage.tsx`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc_web/frontend/src/components/import-page/ImportPage.tsx)
- [`nemo_oc_web/frontend/src/components/holdings-page/HoldingsPage.tsx`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc_web/frontend/src/components/holdings-page/HoldingsPage.tsx)
- [`nemo_oc_web/frontend/src/components/statistics-page/StatisticsPage.tsx`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc_web/frontend/src/components/statistics-page/StatisticsPage.tsx)
- [`nemo_oc_web/frontend/src/components/users-page/UsersPage.tsx`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc_web/frontend/src/components/users-page/UsersPage.tsx)

## Stack objetivo
### Tecnologia base
- `PySide6`
- `Qt Widgets`, no QML
- `QTableView` + `QAbstractTableModel`
- `QSortFilterProxyModel`
- `QSplitter`
- `QStackedWidget`
- `QThreadPool` o `QThread` para operaciones largas

### Librerias recomendadas
- `PySide6`
- `qtawesome` para iconografia
- `qdarktheme` como base de tema oscuro

Estas librerias son recomendadas, no obligatorias. Si el tema propio alcanza, se puede prescindir de dependencias extra.

## Estructura recomendada
Crear una nueva carpeta paralela:

```text
nemo_oc/
  app/
  app_qt/
    main.py
    bootstrap.py
    shell/
      main_window.py
      sidebar.py
      topbar.py
      statusbar.py
    pages/
      login/
      oc_list/
      importaciones/
      holdings/
      stats/
      users/
      config/
    widgets/
      chips.py
      badges.py
      cards.py
      tables.py
      splitters.py
      dialogs.py
    models/
      oc_table_model.py
      lineas_table_model.py
      suggestions_table_model.py
    viewmodels/
      session_vm.py
      oc_list_vm.py
      detail_vm.py
      import_vm.py
      holdings_vm.py
      stats_vm.py
      users_vm.py
      config_vm.py
    theme/
      palette.py
      tokens.py
      styles.py
```

## Estrategia de migracion
### Principio central
No migrar pantalla por pantalla copiando widgets viejos.  
Migrar primero la **arquitectura de shell y experiencia**, y luego los modulos funcionales.

### Principio de paridad
Cada modulo nuevo en Qt debe:
- cubrir el flujo funcional principal
- respetar la logica actual
- mejorar densidad y ergonomia

## Roadmap detallado
## Fase 0. Preparacion de arquitectura
### Objetivo
Preparar el terreno sin tocar la web ni romper la desktop actual.

### Tareas
- Agregar `PySide6` a las dependencias de desktop.
- Crear carpeta `app_qt`.
- Crear entrypoint nuevo `app_qt/main.py`.
- Definir convencion de carpetas.
- Definir tokens visuales: color, tipografia, espaciado, radios, sombras, estados.
- Definir politica de no duplicacion de logica.

### Entregables
- Estructura base de `app_qt`
- Lanzamiento de una ventana vacia Qt
- Documento de lineamientos visuales iniciales

### Criterio de salida
La app Qt abre y cierra correctamente, sin interferir con la desktop actual.

## Fase 1. Shell principal y sistema visual
### Objetivo
Construir la carcasa completa de la app Qt.

### Tareas
- Crear `MainWindow`
- Crear sidebar fija con:
  - logo
  - navegacion
  - estado del sistema
  - sesion
- Crear area de contenido con `QStackedWidget`
- Crear status bar operativa
- Crear tema oscuro serio
- Crear componentes base:
  - botones primarios/secundarios
  - cards
  - badges
  - labels de seccion
  - chips de estado

### Entregables
- Shell navegable sin contenido real
- Look general consistente y moderno

### Criterio de salida
La app ya se siente como producto, aunque los modulos aun esten vacios.

## Fase 2. Login y sesion local
### Objetivo
Llevar a desktop el modelo de acceso y control de usuarios.

### Tareas
- Consumir las tablas y reglas ya implementadas para usuarios
- Crear login Qt
- Crear bootstrap del primer admin si no existen usuarios
- Crear control de sesion local
- Bloquear vistas por sesion
- Exponer rol `admin` para mostrar u ocultar pantallas

### Entregables
- Pantalla de login
- Sesion local activa
- Inicio y cierre de sesion

### Criterio de salida
La app no se puede usar sin autenticacion, salvo bootstrap inicial.

## Fase 3. Bandeja principal de OCs y detalle
### Objetivo
Migrar el nucleo operativo.

### Tareas
- Crear pagina `Ordenes de compra`
- Usar `QSplitter` vertical:
  - bandeja arriba
  - detalle abajo
- Crear `QTableView` para la bandeja
- Implementar filtros compactos arriba
- Conectar acciones reales del detalle:
  - cambiar estado
  - guardar notas
  - copiar texto para SAP
  - marcar como ingresada
- Implementar seleccion de fila
- Implementar detalle de OC con tablas densas
- Implementar acciones rapidas:
  - copiar para SAP
  - exportar
  - cambiar estado
  - guardar notas
- Implementar persistencia de layout y anchos de columnas

### Entregables
- Bandeja con UX superior a la actual
- Detalle funcional completo

### Criterio de salida
La bandeja Qt reemplaza funcionalmente a la actual para trabajo diario.

### Checkpoint A
Si aqui Qt no supera claramente a `CustomTkinter`, se reevalua el camino.

## Fase 4. Importaciones
### Objetivo
Llevar el modulo de importacion a la nueva shell.

### Tareas
- Importacion MP con rango de fechas y atajos
- Importacion privadas
- Bitacora/log de sync
- Barra de progreso
- Estados de error claros
- Integracion con tareas largas en hilo
- ya conectado a:
  - [`start_sync_thread`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/app/services/sync_service.py)
  - [`start_sync_privado_thread`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/app/services/sync_privado_service.py)
  - [`MercadoPublicoAPI.probar_conexion_rapida`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/app/services/mp_api_service.py)

### Entregables
- Pagina de importaciones Qt completa

### Criterio de salida
La operacion de descarga y sync ya no depende de la UI vieja.

### Estado actual de la fase
- funcional para trabajo base
- pendiente de refinamiento en:
  - feedback visual por severidad
  - cancelacion/control mas fino de ejecuciones
  - exposicion de configuracion relevante sin salir del modulo

## Fase 5. Configuracion
### Objetivo
Llevar la configuracion tecnica y de catalogos.

### Tareas
- Credenciales MP
- SMTP e IMAP
- carga de catalogos
- preferencias visuales
- rutas y estado de archivos
- validaciones y pruebas de conexion

### Entregables
- Pagina de configuracion Qt

### Criterio de salida
Todo lo necesario para operar puede configurarse desde Qt.

### Estado actual de la fase
- pagina `Configuracion` ya creada como modulo real en:
  [`nemo_oc/app_qt/pages/config_page.py`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/app_qt/pages/config_page.py)
- ya incluye:
  - credenciales de Mercado Publico con `Prueba rapida API`
  - configuracion SMTP y prueba de envio
  - configuracion IMAP / Gmail y automatizacion
  - rutas de catalogos con selector de archivo
  - cargas reales para CM, maestra, cartera, correos, RedSalud y licitaciones
  - apertura rapida de carpetas `catalogs`, `data` y `config`
  - resumen de conteos cargados y bitacora local
- validacion:
  - `py_compile` correcto
  - arranque Qt correcto en modo offscreen
  - modulo `Configuracion` cargando valores reales desde `settings.json`

## Fase 6. Holdings
### Objetivo
Llevar a desktop el nuevo modelo multi-holding.

### Tareas
- Crear pagina `Holdings`
- CRUD de holdings
- RUTs compradores
- correos esperados
- reglas avanzadas de reconocimiento
- catalogos por holding
- autocompletado desde cartera maestra

### Entregables
- Modulo holdings completo en Qt

### Criterio de salida
La administracion de privados ya puede hacerse desde la desktop.

### Estado actual de la fase
- pagina `Holdings` ya creada como modulo real en:
  [`nemo_oc/app_qt/pages/holdings_page.py`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/app_qt/pages/holdings_page.py)
- ya incluye:
  - listado de holdings con filtro local
  - alta y actualizacion de identidad del holding
  - administracion de RUTs compradores
  - busqueda en cartera maestra para completar RUT y nombre visible
  - gestion simplificada de `correos esperados`
  - reglas avanzadas de reconocimiento
  - importacion de catalogo privado por holding
- validacion:
  - `py_compile` correcto
  - arranque Qt correcto en modo offscreen
  - lectura real de `5` holdings desde la base local

## Fase 7. Estadisticas y revision experta
### Objetivo
Llevar el modulo de mayor valor operativo.

### Tareas
- indicadores superiores compactos y accionables
- cola de sugerencias y correcciones
- aceptar sugerencia en fila
- expandir inline
- asignacion manual desde maestra
- progreso de sesion
- filtros de cola
- atajos de teclado

### Entregables
- Mesa de trabajo experta en Qt

### Criterio de salida
Un usuario experto puede resolver lineas del dia sin depender de la web.

### Estado actual de la fase
- pagina `Estadisticas y revision` ya creada como modulo real en:
  [`nemo_oc/app_qt/pages/stats_page.py`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/app_qt/pages/stats_page.py)
- ya incluye:
  - rango de fechas con atajos `Hoy`, `7 dias` y `30 dias`
  - metricas superiores compactas con acceso rapido a filtros de cola
  - cola experta con tabla densa, busqueda local y modos `Pendientes`, `Con sugerencia`, `Sin sugerencia`, `Revisadas` y `Todos`
  - aceptacion directa de la sugerencia principal desde la fila
  - panel inferior de revision activa con contexto compacto de la linea
  - sugerencias del motor con estrellas y aceptacion directa
  - busqueda manual en maestra SAP con asignacion verificada desde resultados
  - limpieza de asignacion desde la misma pantalla
  - actualizacion local optimista de la cola y resumen, sin recargar toda la vista tras cada accion
- soporte local agregado en:
  [`nemo_oc/app/services/review_service.py`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/app/services/review_service.py)
  y nuevos helpers de escritura en:
  [`nemo_oc/app/repositories/oc_repository.py`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/app/repositories/oc_repository.py)
- validacion:
  - `py_compile` correcto para `stats_page.py`, `review_service.py`, `oc_repository.py` y `main_window.py`
  - arranque Qt correcto en modo offscreen
  - carga real de resumen y cola en la preview Qt
  - seleccion automatica de linea activa y detalle inferior operativo

## Fase 8. Usuarios y seguridad operativa
### Objetivo
Cerrar la administracion de accesos dentro de la desktop Qt.

### Tareas
- pagina `Usuarios`
- alta, baja y activacion
- roles
- reinicio de acceso con token
- reseteo de clave

### Entregables
- Gestion de usuarios Qt completa

### Criterio de salida
La administracion de accesos ya no depende de la web.

### Estado actual de la fase
- pagina `Usuarios` ya creada como modulo real en:
  [`nemo_oc/app_qt/pages/users_page.py`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/app_qt/pages/users_page.py)
- capa local de seguridad administrativa creada en:
  [`nemo_oc/app/services/user_admin_service.py`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/nemo_oc/app/services/user_admin_service.py)
- ya incluye:
  - alta de usuarios con `username`, nombre completo, rol y contraseña
  - listado de usuarios existentes con conteos de activos y admins
  - edicion de nombre, rol y estado activo
  - proteccion para no dejar el sistema sin un administrador activo
  - reseteo directo de contraseña
  - reinicio de acceso con token temporal mostrado en pantalla y copiable
  - lectura del flag `must_reset_password`
- validacion:
  - `py_compile` correcto para el servicio y la pagina Qt
  - arranque Qt correcto en modo offscreen
  - lectura real del usuario `admin` desde la base local
  - editor cargando correctamente el usuario seleccionado

## Fase 9. Empaquetado y distribucion
### Objetivo
Preparar la nueva desktop para uso real.

### Tareas
- crear nuevo spec o flujo de empaquetado
- generar ejecutable de prueba
- definir estructura de datos local
- validar paths de base, logs y catalogos
- revisar rendimiento en equipos reales
- definir plan de actualizacion

### Entregables
- build distribuible
- instructivo de instalacion
- checklist de puesta en marcha

### Criterio de salida
La version Qt puede instalarse y operar de punta a punta.

## Normas de diseño visual
### Direccion visual
- oscura
- profesional
- densa pero legible
- fuerte jerarquia tipografica
- acentos de marca Nemo

### Patrones obligatorios
- sidebar con contexto permanente
- tablas densas
- badges de estado consistentes
- splitters ajustables
- formularios compactos
- toolbars claras
- cero ventanas emergentes innecesarias

### Patrones a evitar
- interfaces "vacías"
- dialogos excesivos
- colores de sistema sin unificar
- mezclas de estilos web y escritorio sin criterio

## Riesgos y mitigacion
### Riesgo 1
Duplicar logica de negocio dentro de Qt.

Mitigacion:
- usar viewmodels/adaptadores
- mantener repositorios y servicios como fuente unica

### Riesgo 2
Querer migrar demasiados modulos a la vez.

Mitigacion:
- cerrar cada fase antes de abrir la siguiente
- mantener Checkpoint A y B

### Riesgo 3
Perder continuidad operativa.

Mitigacion:
- no borrar la UI actual
- mantener entrypoint viejo funcional

### Riesgo 4
Volver a improvisar la UX.

Mitigacion:
- usar la web como referencia funcional fija
- conservar este plan como documento rector

## Como retomar este trabajo despues
Cuando se quiera volver a este punto:
1. Leer primero:
   [`DECISION_DESKTOP_UI_2026-04-04.md`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/DECISION_DESKTOP_UI_2026-04-04.md)
2. Leer este plan completo:
   [`PLAN_MIGRACION_DESKTOP_QT_2026-04-04.md`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/PLAN_MIGRACION_DESKTOP_QT_2026-04-04.md)
3. Revisar el baseline Git:
   `2e22689`
4. Confirmar que la web sigue en modo referencia, no en modo desarrollo
5. Retomar desde la ultima fase cerrada, no desde una fase intermedia a medias

## Orden recomendado de ejecucion real
1. Fase 0
2. Fase 1
3. Fase 2
4. Fase 3
5. Checkpoint A
6. Fase 4
7. Fase 5
8. Fase 6
9. Fase 7
10. Fase 8
11. Fase 9

## Definicion de exito
La migracion se considera exitosa cuando:
- la nueva desktop Qt cubre el flujo principal de trabajo
- se ve claramente mejor que la actual
- la bandeja y la revision experta son mas rapidas
- holdings, usuarios e importaciones existen en desktop
- ya no hace falta depender de la web para operar el sistema
