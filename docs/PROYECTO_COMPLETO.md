# NemoOC - Documentacion Completa del Proyecto

> Ultima actualizacion: 2026-03-30
> Generado automaticamente para contexto de desarrollo

---

## 1. Vision General

**NemoOC** es una aplicacion de escritorio + web para **Nemo Chile S.A.** que gestiona Ordenes de Compra (OCs) desde el portal **Mercado Publico** de Chile y las prepara para ingreso en **SAP Business One**.

### Versiones
- **Desktop**: Python + CustomTkinter + SQLite (app portable, se puede empaquetar con PyInstaller)
- **Web**: React 18 + TypeScript + Vite (frontend) + FastAPI (backend) — comparten la misma BD SQLite y servicios Python

### Stack Tecnico
| Capa | Tecnologia |
|------|-----------|
| Frontend Web | React 18, TypeScript, Vite, Tailwind CSS, TanStack Query, Axios, Lucide Icons |
| Backend Web | FastAPI, Uvicorn, SSE (sse-starlette) |
| Desktop UI | CustomTkinter |
| Logica de Negocio | Python 3.11+, openpyxl, requests, pdfplumber |
| Base de Datos | SQLite (WAL mode) en `nemo_oc/data/app.db` |
| Config | JSON en `nemo_oc/config/settings.json` |

### Puertos
- Backend: `http://127.0.0.1:8001`
- Frontend: `http://localhost:5173` (Vite dev server, proxy `/api` → backend)

---

## 2. Estructura de Directorios

```
INGRESO OC/
├── nemo_oc/                          # App desktop + logica compartida
│   ├── app/
│   │   ├── config.py                 # AppConfig dataclass, load/save settings.json
│   │   ├── db.py                     # SQLite: get_connection(), initialize_db(), migraciones
│   │   ├── main.py                   # Entry point desktop: init DB + catalogos + UI
│   │   ├── models/
│   │   │   ├── orden_compra.py       # @dataclass OrdenCompra (34 campos)
│   │   │   ├── linea_oc.py           # @dataclass LineaOC (23 campos)
│   │   │   ├── homologacion.py       # @dataclass HomologacionItem, SapArticulo
│   │   │   ├── cartera.py            # @dataclass CarteraCliente
│   │   │   ├── licitacion_ref.py     # @dataclass LicitacionRef, SugerenciaProducto
│   │   │   └── maestra_material.py   # @dataclass MaestraMaterial
│   │   ├── repositories/
│   │   │   ├── oc_repository.py      # CRUD OCs: save_oc, get_all_ocs, get_lineas, marcar_ingresada
│   │   │   ├── homologacion_repo.py  # count_homologacion, get_all_homologacion
│   │   │   ├── licitaciones_repo.py  # get_candidates (OR LIKE), get_exact_candidates, count
│   │   │   ├── maestra_repo.py       # search_maestra, search_by_keywords, lookup_by_old_code
│   │   │   └── cartera_repo.py       # count_cartera
│   │   ├── services/
│   │   │   ├── mp_api_service.py     # MercadoPublicoAPI: obtener_lista_oc, obtener_detalle_oc
│   │   │   ├── transform_service.py  # JSON API → modelos: parse_cabecera_oc, parse_detalle_oc, homologar_lineas
│   │   │   ├── sync_service.py       # Orquestador sync MP: descarga → transforma → homologa → persiste
│   │   │   ├── homologacion_service.py # HomologacionService: cargar HOMOLOGACION.xlsx, lookup codigo_mp → SAP
│   │   │   ├── licitaciones_service.py # LicitacionesService: importar lic.xlsx, buscar_sugerencias (Jaccard)
│   │   │   ├── maestra_service.py    # MaestraService: importar MAESTRA, lookup itemcode/codigo_historico
│   │   │   ├── cartera_service.py    # CarteraService: cargar CARTERA(PBI).xlsx, lookup cod_cliente
│   │   │   ├── email_service.py      # EmailService: SMTP Gmail, notificar vendedores por cartera
│   │   │   ├── imap_service.py       # buscar_ocs_gmail: IMAP SSL, descargar PDFs adjuntos
│   │   │   ├── sync_privado_service.py # Orquestador sync privado: Gmail → PDF → homologa → persiste
│   │   │   ├── pdf_parser_redsalud.py # Parsear PDFs de OCs RedSalud (formato SAP)
│   │   │   └── redsalud_homo_service.py # HomologacionRedSalud: codigo_cliente → itemcode_sap
│   │   ├── utils/
│   │   │   ├── rut_utils.py          # rut_to_cliente_sap: "61.606.402-9" → "CN61606402"
│   │   │   ├── regex_utils.py        # extraer_codigo_mp: "(2230498) ENVOLT..." → "2230498"
│   │   │   ├── clipboard_utils.py    # generar_texto_sap: lineas → texto TAB-separado para SAP
│   │   │   └── logger.py             # setup_logger
│   │   └── ui/frames/               # Desktop UI (CustomTkinter frames)
│   │       ├── oc_list_frame.py
│   │       ├── oc_detail_frame.py
│   │       ├── import_frame.py
│   │       └── config_frame.py
│   ├── config/
│   │   └── settings.json             # Configuracion persistente
│   ├── data/
│   │   └── app.db                    # SQLite database
│   ├── catalogs/                     # Archivos xlsx copiados al subir
│   └── scripts/
│       ├── auto_assign.py
│       └── check_kne.py
│
├── nemo_oc_web/                      # Version web
│   ├── run.py                        # Levanta backend + frontend en paralelo
│   ├── backend/
│   │   ├── main.py                   # FastAPI app, lifespan, CORS, routers
│   │   ├── core/
│   │   │   ├── startup.py            # initialize(): replica main.py desktop (DB + catalogos)
│   │   │   ├── deps.py               # Dependency injection: get_*_service()
│   │   │   └── tasks.py              # Auto-sync loop (asyncio + threading)
│   │   └── api/
│   │       ├── schemas.py            # Pydantic schemas (OrdenCompraOut, LineaOCOut, SugerenciaOut, etc.)
│   │       ├── oc_routes.py          # GET/PUT /api/ocs/*, sugerencias, asignar, SAP text, export
│   │       ├── sync_routes.py        # POST /api/sync/mercado-publico, /gmail + SSE progress
│   │       ├── config_routes.py      # GET/PUT /api/config, GET /api/config/manual
│   │       └── catalog_routes.py     # POST /api/catalogs/{tipo}, GET /stats, GET /maestra/search
│   └── frontend/
│       ├── vite.config.ts            # Proxy /api → localhost:8001
│       ├── src/
│       │   ├── main.tsx              # React root + QueryClientProvider
│       │   ├── App.tsx               # BrowserRouter: /, /oc/:codigo, /import, /config
│       │   ├── types/oc.ts           # TypeScript interfaces: OrdenCompra, LineaOC, Sugerencia, etc.
│       │   ├── api/
│       │   │   ├── client.ts         # Axios instance baseURL=/api
│       │   │   ├── ocs.ts            # getOcs, getOc, asignarItemcode, getSugerencias, exportAll
│       │   │   ├── sync.ts           # startSyncMp, startSyncGmail, testApi, getGlobalLogs
│       │   │   ├── config.ts         # getConfig, updateConfig
│       │   │   └── catalogs.ts       # getCatalogStats, upload*, searchMaestra
│       │   ├── hooks/
│       │   │   └── useSyncSSE.ts     # Hook SSE para progreso sync en tiempo real
│       │   ├── utils/
│       │   │   ├── formatters.ts     # fmtMoney, fmtDate, homoClass, estadoBadgeClass
│       │   │   └── clipboard.ts      # copyText (Clipboard API + fallback)
│       │   └── components/
│       │       ├── layout/
│       │       │   ├── AppLayout.tsx  # Sidebar + Outlet + StatusBar
│       │       │   ├── Sidebar.tsx    # Nav links + sync status indicator
│       │       │   └── StatusBar.tsx  # Total / Sin homologar / Ingresadas
│       │       ├── oc-list/
│       │       │   └── OcListPage.tsx # Split-screen: tabla arriba (38%), detalle abajo
│       │       ├── oc-detail/
│       │       │   ├── OcDetailPanel.tsx    # Panel embebido en split-screen
│       │       │   ├── OcDetailPage.tsx     # Pagina completa (ruta /oc/:codigo)
│       │       │   ├── ResizableTable.tsx   # Tabla con columnas redimensionables
│       │       │   └── SapColumnConfigModal.tsx # Modal drag-and-drop para columnas SAP
│       │       ├── import-page/
│       │       │   └── ImportPage.tsx       # Sync MP + Gmail, progreso SSE, logs
│       │       └── config-page/
│       │           └── ConfigPage.tsx       # API ticket, SMTP, IMAP, auto-sync, catalogos upload
│
├── lic.xlsx                          # Datos licitaciones (Sheet1: 8984 filas × 38 cols)
├── HOMOLOGACION.xlsx                 # Mapeo codigo_mp → itemcode_sap (CM)
├── MAESTRA DE MATERIALES (PBI).xlsx  # Catalogo completo SAP
└── CARTERA(PBI).xlsx                 # Clientes SAP con cartera/vendedor/region
```

---

## 3. Base de Datos SQLite

### Tablas principales

**oc_cabecera** — Cabecera de OC (PK: `codigo_oc`)
- Campos API: nombre_oc, estado_mp, tipo_oc, fechas, montos, comprador, proveedor
- Campos internos: `estado_interno` (Nueva/Ingresada/En proceso), `fecha_ingreso`, `notas`, `cliente_sap_sugerido`

**oc_detalle** — Lineas de OC (PK: `id`, UNIQUE: `codigo_oc + correlativo`)
- Campos API: producto, especificacion_comprador, cantidad, precio_neto, total
- Campos SAP: `itemcode_sap`, `descripcion_sap`, `factor_empaque`, `cantidad_sap`, `precio_sap`
- Estado: `estado_homologacion` (pendiente | homologado | sin_homologacion | manual | asignado_auto)

**homologacion_productos** — Mapeo CM: codigo_mp → itemcode_sap + factor_empaque

**sap_articulos** — Catalogo SAP: itemcode_sap → descripcion_sap

**maestra_materiales** — Maestra completa: itemcode, descripcion, codigo_historico, grupo, categoria

**cartera_clientes** — Clientes: cod_cliente (CN...), rut, razon, vendedor, cartera, region

**homologacion_redsalud** — Mapeo privado: codigo_cliente → itemcode_sap + precio_ref

**licitaciones_ref** — Historial licitaciones para sugerencias no-CM
- `descripcion_comprador`: texto original de la licitacion
- `descripcion_norm`: texto normalizado (lowercase, sin acentos)
- `itemcode_sap`: codigo SAP con el que se postulo (de `codigo final` en lic.xlsx)
- `descripcion_nemo`: descripcion del producto Nemo (ProductDesc en lic.xlsx)
- `frecuencia`: cuantas veces se postulo con esa combinacion
- `rut_comprador`: RUT convertido a formato SAP (CN...)
- UNIQUE: (descripcion_norm, rut_comprador, producto_code_old)

### Vista
**vw_oc_detalle_sap** — Join oc_detalle + sap_articulos para descripciones enriquecidas

### Migraciones
- v1: Tablas base
- v2: maestra_materiales + licitaciones_ref
- v3: Recrear licitaciones_ref (schema change)

---

## 4. Tipos de OC y Flujo de Homologacion

### OCs tipo CM (Convenio Marco)
```
API Mercado Publico → EspecificacionComprador contiene "(2230498) ENVOLT..."
                    → extraer_codigo_mp() → "2230498"
                    → homologacion_productos.lookup("2230498")
                    → itemcode_sap + factor_empaque + descripcion_sap
                    → estado_homologacion = "homologado"
```

### OCs tipo no-CM (SE, AG, CC, Trato Directo, Licitaciones)
```
API Mercado Publico → NO traen codigo_mp usable
                    → texto = especificacion_comprador + producto
                    → buscar_sugerencias(texto, rut_oc)
                    → Motor Jaccard 4 fases (ver seccion 5)
                    → Si score >= 0.35 → asignado_auto
                    → Si score < 0.35 → manual (usuario asigna)
```

### OCs Privadas (RedSalud via Gmail)
```
Gmail IMAP → emails con asunto "ORDEN DE COMPRA"
           → descargar PDFs adjuntos
           → pdf_parser_redsalud.parse_pdf()
           → homologacion_redsalud.lookup(codigo_cliente)
           → codigo_oc prefijado "RS-{numero}"
```

---

## 5. Motor de Sugerencias No-CM (Detalle Completo)

### Fuente de datos: lic.xlsx
- **Sheet1**: 8984 filas de licitaciones historicas
- Filtro: solo filas donde `CompetitorName = "NEMO CHILE S.A."` y `Estado Gestion = "Cotizada"`
- Columnas clave: `Description` (texto del comprador), `codigo final` (itemcode SAP directo), `ProductDesc` (descripcion Nemo), `Rut`
- Al importar, se normaliza y agrupa por `(descripcion_norm, cliente_sap, codigo_final)` contando frecuencia
- **Total en BD**: ~7941 referencias, todas con itemcode_sap

### Flujo de busqueda: `buscar_sugerencias(texto, rut_oc)`

**Input**: texto de la linea OC (especificacion_comprador + producto)

**Fase 1 - Exact Match por RUT** (score = 1.0)
- Si el RUT de la OC coincide con un registro en licitaciones_ref
- Y la descripcion normalizada es IDENTICA
- → Retorna inmediatamente con score 1.0

**Fase 2 - Jaccard + RUT** (boost = +0.1)
- Busca candidatos con OR LIKE en licitaciones_ref filtrado por rut_comprador
- Rescoring con Jaccard ponderado
- Bonus de +0.1 al score por ser mismo comprador

**Fase 3 - Jaccard Global** (boost = 0.0)
- Busca candidatos en TODA la tabla licitaciones_ref (cualquier RUT)
- Rescoring con Jaccard ponderado

**Fase 4 - Maestra SAP Fallback** (penalizacion = -0.1)
- Solo si Fases 1-3 no producen resultados
- Busca en maestra_materiales por keywords
- Umbral mas bajo (0.20 en vez de 0.28)
- `descripcion_match = "[BD MAESTRA SAP]"` para identificar origen

### Tokenizacion y scoring

**Normalizacion** (`_normalize`): lowercase, sin acentos (NFKD), whitespace compacto

**Tokenizacion** (`_extract_tokens`): `re.findall(r"[a-z0-9]+")` → filtrar len >= 3, no stopwords

**Stopwords**: de, del, la, las, el, los, un, una, para, por, con, sin, que, como, mas, en, al, und, unidad, unidades, caja, cajas, sobre, paquete, pqte, set, kit, par, tipo, uso, marca, modelo, ref, referencia, numero, num, nro, cod, codigo, segun, especificacion, aprox, aproximado, similar, equivalente, descripcion, producto, articulo, item, material, und, cada

**Pesos por token** (`_token_weight`):
| Tipo | Ejemplo | Peso |
|------|---------|------|
| Numero + unidad (regex) | "500ml", "10cm", "250mg" | 2.5 |
| Numero puro | "500", "1000" | 2.0 |
| Palabra >= 8 chars | "fentanilo", "quirurgico" | 1.5 |
| Palabra 4-7 chars | "guante", "suero" | 1.0 |
| Palabra 3 chars | "tal", "uso" | 0.7 |

**Jaccard ponderado** (`_jaccard_weighted`):
```
score = sum_weights(intersection) / sum_weights(union)
```
- Bidireccional: penaliza si el historico tiene muchas palabras extra
- Ejemplo: query={"guante","nitrilo"} hist={"guante","nitrilo","desechable","talla","azul"}
  → intersec=2.5, union=4.9 → score=0.51

**Umbrales**:
- `_MIN_SCORE = 0.28` para licitaciones_ref
- `0.20` para maestra SAP fallback
- `0.35` para auto-asignacion durante sync (mas conservador)
- Scores capped at 0.99 (1.0 reservado para exact match)

**Limite SQL**: `_CANDIDATES_LIMIT = 80` filas con OR LIKE, luego rescoring en Python

### Deduplicacion
- Agrupa resultados por itemcode_sap, conserva el mejor score
- Ordena por (-score, -frecuencia)
- Retorna max 5 resultados

---

## 6. API REST (Backend Web)

### OCs
| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| GET | `/api/ocs` | Lista OCs con filtros (estado, estado_mp, tipo_oc, fechas, busqueda) |
| GET | `/api/ocs/stats` | Total, sin_homolog, ingresadas |
| GET | `/api/ocs/filtros` | Estados MP, tipos, carteras distintos |
| GET | `/api/ocs/export-all` | Excel con todas las OCs filtradas |
| GET | `/api/ocs/{codigo}` | Detalle: cabecera + lineas |
| PUT | `/api/ocs/{codigo}/estado` | Cambiar estado_interno |
| PUT | `/api/ocs/{codigo}/ingresada` | Marcar como ingresada (con fecha) |
| PUT | `/api/ocs/{codigo}/notas` | Guardar notas |
| GET | `/api/ocs/{codigo}/sap-text` | Texto TAB-separado para SAP |
| GET | `/api/ocs/{codigo}/export-excel` | Excel individual de la OC |
| PUT | `/api/ocs/{codigo}/lineas/{corr}/asignar` | Asignar itemcode_sap manualmente |
| DELETE | `/api/ocs/{codigo}/lineas/{corr}/asignar` | Limpiar asignacion |
| GET | `/api/ocs/{codigo}/lineas/{corr}/sugerencias` | Sugerencias Jaccard (top 5) |

### Sync
| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| POST | `/api/sync/mercado-publico` | Iniciar sync MP (retorna sync_id) |
| GET | `/api/sync/mercado-publico/{id}/progress` | SSE de progreso |
| POST | `/api/sync/gmail` | Iniciar sync Gmail |
| GET | `/api/sync/gmail/{id}/progress` | SSE de progreso |
| POST | `/api/sync/test-api` | Test conexion API MP |
| GET | `/api/sync/logs` | Logs globales (auto-sync + manual) |
| GET | `/api/sync/status` | Estado: running/idle |

### Config
| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| GET | `/api/config` | Leer toda la config |
| PUT | `/api/config` | Actualizar campos parciales |
| GET | `/api/config/manual` | Generar y descargar manual PDF |

### Catalogos
| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| GET | `/api/catalogs/stats` | Conteos de todos los catalogos |
| POST | `/api/catalogs/homologacion` | Subir HOMOLOGACION.xlsx |
| POST | `/api/catalogs/maestra` | Subir MAESTRA.xlsx |
| POST | `/api/catalogs/cartera` | Subir CARTERA.xlsx |
| POST | `/api/catalogs/correos` | Subir CORREOS.xlsx |
| POST | `/api/catalogs/redsalud` | Subir HOMO RED SALUD.xlsx |
| POST | `/api/catalogs/licitaciones` | Subir lic.xlsx |
| GET | `/api/catalogs/maestra/search?q=...` | Buscar en maestra (min 3 chars) |
| GET | `/api/health` | Health check |

---

## 7. Frontend Web

### Paginas
1. **OcListPage** (`/`): Split-screen vertical — tabla de OCs arriba (38%), detalle abajo
   - Filtros: Estado, Estado MP, Tipo, Solo hoy, Desde/Hasta, Busqueda
   - Acciones: Filtrar, Limpiar, Actualizar, Exportar Excel
   - Click en fila abre detalle abajo; click de nuevo cierra

2. **OcDetailPanel** (embebido en split): Header premium con Cliente SAP, Codigo OC, badges
   - Acciones: Copiar a SAP (configurable), Ajustes SAP, Exportar Excel, Ingresar en SAP
   - Tabla ResizableTable con columnas drag-to-resize persistidas en localStorage
   - Lineas: click expande panel de asignacion con sugerencias + busqueda manual

3. **ImportPage** (`/import`): Sync Mercado Publico + Gmail
   - Rango fechas, checkboxes CM/Otras, botones descarga con quick-date
   - Progreso SSE en tiempo real con barra y logs
   - Log historico global cuando no hay sync activo

4. **ConfigPage** (`/config`): Formularios API/SMTP/IMAP/Auto-sync + Catalogos upload

### Componentes auxiliares
- **SapColumnConfigModal**: Drag-and-drop para elegir y reordenar columnas de "Copiar a SAP"
- **ResizableTable**: `<table>` con columnas redimensionables (drag en borde de header)
- **StatusBar**: Barra inferior con estadisticas (total, sin homologar, ingresadas)
- **Sidebar**: Navegacion + indicador de sync activo

### Estado global
- TanStack Query para todo el data fetching (staleTime: 30s, retry: 1)
- Invalidacion granular por queryKey al mutar
- SSE via EventSource nativo (useSyncSSE hook)

---

## 8. Configuracion (settings.json)

```json
{
  "api_ticket": "82A7A181-C562-4ED2-84CF-CD631CEFCFB3",
  "codigo_empresa": "227926",
  "rut_proveedor": "76.215.260-6",
  "homologacion_path": "...",
  "maestra_path": "...",
  "cartera_path": "...",
  "correos_path": "...",
  "licitaciones_path": "...",
  "redsalud_homo_path": "...",
  "theme": "dark",
  "color_theme": "blue",
  "auto_sync": false,
  "auto_sync_days": 7,
  "auto_sync_interval": 0,
  "last_sync": "2026-03-27T09:32:41",
  "log_level": "INFO",
  "smtp_host": "smtp.gmail.com",
  "smtp_port": 587,
  "smtp_user": "automatizacionnemo@gmail.com",
  "smtp_password": "tuzp zurq pbln nlrb",
  "smtp_enabled": false,
  "imap_server": "imap.gmail.com",
  "imap_port": 993,
  "imap_folder": "INBOX",
  "imap_filter_subject": "ORDEN DE COMPRA",
  "sap_columns": ["itemcode", "descripcion", "cantidad", "precio"]
}
```

---

## 9. Catalogos Excel

### HOMOLOGACION.xlsx
Mapeo Convenio Marco: ID (codigo_mp) → COD SAP (itemcode_sap) + MODELO (descripcion) + F.EMP (factor_empaque)

### MAESTRA DE MATERIALES (PBI).xlsx
Hoja MATERIALES: Numero de Articulo (itemcode_sap), Descripcion, Codigo Historico, Nombre Grupo, Categoria

### CARTERA(PBI).xlsx
Hoja CARTERA 2026: RUT, Razon, Comuna, Region, Vendedor, COD CLIENTE (CN...), Industria, Sector, Cartera, Region Nombre

### CORREOS.xlsx
Mapeo cartera → vendedores: CARTERA | NOMBRE | CORREO (para notificaciones email)

### HOMO RED SALUD.xlsx
Mapeo privado: Codigo Material (codigo_cliente) → Descripcion SAP → Codigo NEMO (itemcode_sap) → Precio

### lic.xlsx
- **Sheet1** (8984 filas): Licitaciones historicas con Description, CompetitorName, Estado Gestion, codigo final, ProductDesc, Rut
- Se filtran filas NEMO CHILE S.A. + Cotizada
- `codigo final` se usa directamente como itemcode_sap

---

## 10. Flujo de Sincronizacion

### Mercado Publico (sync_service.py)
1. `MercadoPublicoAPI.obtener_lista_oc()` — itera dia a dia con API publica
2. Filtrar OCs ya existentes en BD
3. Para cada OC nueva:
   - Obtener detalle si items no vienen en lista
   - `transform_service.parse_cabecera_oc()` + `parse_detalle_oc()`
   - Si CM: `homologar_lineas()` con catalogo
   - Si no-CM: `buscar_sugerencias()` por cada linea, auto-asignar si score >= 0.35
   - `oc_repository.save_oc()`
   - Email notificacion a vendedor (si habilitado y no es estado final)
4. Progreso via Queue → SSE al frontend

### Gmail (sync_privado_service.py)
1. IMAP: buscar emails no leidos con asunto "ORDEN DE COMPRA"
2. Descargar PDFs adjuntos a archivos temporales
3. `pdf_parser_redsalud.parse_pdf()` — extrae cabecera y lineas
4. Homologar con `homologacion_redsalud`
5. Persistir como OC con prefijo "RS-"
6. Limpiar temporales

### Auto-sync (tasks.py)
- Al arrancar servidor: sync inicial si `auto_sync=true`
- Loop periodico cada `auto_sync_interval` minutos
- Usa config.auto_sync_days para rango de fechas

---

## 11. Utilidades Clave

### rut_to_cliente_sap
`"61.606.402-9"` → quitar puntos → quitar guion+DV → anteponer "CN" → `"CN61606402"`

### extraer_codigo_mp
`"(2230498) ENVOLTURA NEMO..."` → regex `^\s*\((\d+)\)` → `"2230498"`

### generar_texto_sap
Lineas con itemcode_sap → TAB-separado (itemcode \t descripcion \t cantidad \t precio) + CRLF

---

## 12. Pendientes / Bugs Conocidos

### Bugs
- **Config save web**: El boton Guardar en ConfigPage hace PUT pero la respuesta no siempre persiste (investigar)

### Mejoras planeadas (plan activo)
- **Batch sugerencias**: Pre-cargar sugerencia top-1 para TODAS las lineas al abrir OC no-CM
- **Transparencia**: Mostrar descripcion historica que matcheo + score + frecuencia
- **Panel mejorado**: Tarjetas clickeables en vez de botones planos para sugerencias

### Features desktop que faltan en web
- Colores de homologacion por fila (HOMO_COLORS dict)
- Configurador de columnas visibles en tabla
- Banner de advertencia para OCs sin homologar
- Mas estados en dropdown (desktop tiene mas opciones)
- Boton test email en config
- Pre-carga de sugerencias en background thread (desktop hace esto)
