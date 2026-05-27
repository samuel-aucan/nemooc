# CLAUDE.md

Guidance for AI assistants working on **NemoOC** — the purchase-order (OC) ingestion system for Nemo Chile S.A.

## What this project is

NemoOC pulls Órdenes de Compra from Chile's **Mercado Público** portal (and private email channels) and prepares them for ingestion into **SAP Business One**. Two front-ends share the same Python business logic and the same SQLite database:

- **Desktop** (`nemo_oc/`) — CustomTkinter, packaged via PyInstaller
- **Web** (`nemo_oc_web/`) — FastAPI backend + React/TypeScript frontend

The web version is the active focus. The desktop app still works but receives fewer new features.

Documentation language is Spanish; code identifiers are Spanish + English mixed (e.g. `cantidad_sap`, `itemcode_sap`, `estado_homologacion`). Match the surrounding style — do not "translate" identifiers.

## Repository layout

```
nemooc/
├── nemo_oc/                 # Desktop app + shared Python business logic
│   ├── app/
│   │   ├── main.py          # Desktop entry point (initialize DB + catalogs + UI)
│   │   ├── config.py        # AppConfig dataclass, settings.json, path helpers
│   │   ├── db.py            # SQLite schema + migrations (single source of truth)
│   │   ├── models/          # @dataclass models (OrdenCompra, LineaOC, ...)
│   │   ├── repositories/    # SQL CRUD per table
│   │   ├── services/        # Business logic (sync, homologación, parsers, ...)
│   │   ├── utils/           # rut_utils, regex_utils, clipboard_utils, logger
│   │   └── ui/frames/       # Desktop UI (CustomTkinter)
│   ├── catalogs/            # HOMOLOGACION.xlsx, MAESTRA, CARTERA, HOMO RED SALUD, lic.xlsx
│   ├── config/settings.json # Persisted config (gitignored)
│   ├── data/app.db          # SQLite DB (gitignored; WAL mode)
│   └── requirements.txt
│
├── nemo_oc_web/             # Web (FastAPI + React)
│   ├── run.py               # Launches backend (uvicorn 8001) + frontend (vite 5173)
│   ├── backend/
│   │   ├── main.py          # FastAPI app, lifespan, session+CORS middleware
│   │   ├── core/
│   │   │   ├── startup.py   # initialize(): mirrors desktop main.py boot sequence
│   │   │   ├── auth.py      # PBKDF2 password hashing, session helpers, RBAC
│   │   │   ├── deps.py      # DI singletons (re-exports nemo_oc services)
│   │   │   └── tasks.py     # Auto-sync asyncio loop
│   │   └── api/             # Routers: auth, ocs, sync, config, catalog, holdings
│   └── frontend/            # React 18 + TS + Vite + Tailwind + TanStack Query
│       └── src/
│           ├── App.tsx      # Router (login + protected routes)
│           ├── api/         # Axios clients per resource
│           ├── components/  # Pages: auth, oc-list, oc-detail, import-page,
│           │                #        config-page, holdings-page, statistics-page,
│           │                #        users-page, layout, common
│           ├── hooks/        # useSyncSSE (EventSource wrapper)
│           ├── types/        # TS interfaces (auth.ts, oc.ts)
│           └── utils/        # formatters, clipboard
│
├── PROYECTO_COMPLETO.md     # Long-form technical doc (Mar 2026 snapshot — partially stale)
├── ESTADO_SISTEMA_2026-04-03.md  # Latest project-state notes (Apr 2026)
├── MANUAL_REENVIO_AUTOMATICO_OCS_PRIVADAS.md  # Outlook rule setup for private OCs
└── *.xlsx                   # Catalog source files (committed for bootstrap)
```

> `PROYECTO_COMPLETO.md` is the most detailed walkthrough but predates the holdings refactor and auth module. Treat it as background; the `ESTADO_SISTEMA_2026-04-03.md` corte and the current source are authoritative when they disagree.

## How the two apps share code

The web backend adds `nemo_oc/` to `sys.path` (see `nemo_oc_web/backend/main.py` and every `api/*.py`). Backend routes import `app.repositories.*`, `app.services.*`, `app.config.*` directly. **Both apps read/write the same `nemo_oc/data/app.db` and the same `nemo_oc/config/settings.json`** — never run them at the same time.

When adding new business logic, put it in `nemo_oc/app/services/` or `nemo_oc/app/repositories/` and expose it from the web backend via a route, rather than duplicating logic in `backend/`.

Singletons: services use a module-level `_instance` cached via `get_<service>_service()`. After mutating catalog data, call `svc.reload()` so the in-memory caches refresh.

## Running locally

### Web (preferred)

```bash
cd nemo_oc_web
pip install -r requirements.txt
cd frontend && npm install && cd ..
python run.py            # backend :8001, frontend :5173
```

First-time visit at http://localhost:5173 forces creating the initial admin user (see `auth.bootstrap_status` → `bootstrap`).

### Desktop

```bash
cd nemo_oc
pip install -r requirements.txt
python app/main.py
```

### Single-server dev

```bash
# from nemo_oc_web/
uvicorn backend.main:app --host 127.0.0.1 --port 8001 --reload
# in another shell, from nemo_oc_web/frontend/
npm run dev
```

Vite proxies `/api/*` → `http://127.0.0.1:8001` (`vite.config.ts`).

### Build checks

- Frontend type-check + production build: `cd nemo_oc_web/frontend && npm run build` (runs `tsc -b && vite build`)
- No automated Python test suite exists. Validate by running the app and exercising the touched flow.

## Database

SQLite at `nemo_oc/data/app.db`, **WAL mode**. Schema is defined entirely in `nemo_oc/app/db.py`:

- `_create_tables(conn)` — base tables (`oc_cabecera`, `oc_detalle`, `homologacion_productos`, `sap_articulos`, `homologacion_redsalud`, `cartera_clientes`, `vw_oc_detalle_sap`).
- `_apply_migrations(conn)` — versioned migrations keyed by `schema_version`. Current head is **v8**.

| Version | Adds |
|---------|------|
| v2 | `maestra_materiales`, `licitaciones_ref` |
| v3 | Recreate `licitaciones_ref` (schema change) |
| v4 | `holdings`, `holding_ruts`, `homologacion_privados` |
| v5/v6 | `holding_match_rules`, `holding_catalog_files`, `oc_privado_auditoria` |
| v7 | `usuarios` |
| v8 | `usuarios.must_reset_password`, `reset_token_hash`, `reset_token_expires_at` |

**When changing schema:** add a new migration entry to the `migrations` dict in `_apply_migrations` with the next version number. Use `CREATE TABLE IF NOT EXISTS` / `ALTER TABLE` and bump `schema_version`. Do **not** edit existing migration scripts.

If a new migration also needs default data, mirror the `_seed_holdings` / `_seed_holding_match_rules` pattern (called once when `current < 6`).

## Domain model: the OC flow

There are three OC sources, all converging on the same `oc_cabecera`/`oc_detalle` tables.

1. **CM (Convenio Marco)** — Mercado Público items whose `EspecificacionComprador` starts with `(codigo_mp)`. Parsed by `utils/regex_utils.py:extraer_codigo_mp` and looked up in `homologacion_productos` (loaded from `HOMOLOGACION.xlsx`). State → `homologado`.
2. **No-CM** (SE / AG / CC / Trato Directo / Licitación) — no direct code. Goes through `licitaciones_service.buscar_sugerencias(texto, rut_oc)`: a 4-phase weighted Jaccard match against `licitaciones_ref` (from `lic.xlsx`) then `maestra_materiales` as fallback. Auto-assigns when score ≥ 0.35; otherwise `manual`.
3. **Private (holdings)** — emails to `automatizacionnemo@gmail.com` with PDF OCs. `sync_privado_service` orchestrates IMAP → per-holding parser (`pdf_parser_redsalud`, `pdf_parser_indisa`, `pdf_parser_banmedica`, `pdf_parser_achs`) → `homologacion_privados` lookup. The `holdings` table drives parser routing, RUT recognition, and matching rules (`holding_match_rules`). Each OC gets a `prefijo`-prefixed code (`RS-…`, `IN-…`, `BM-…`, `AC-…`) and writes a row in `oc_privado_auditoria`.

Scoring constants live in `nemo_oc/app/services/licitaciones_service.py` (`_MIN_SCORE`, `_CANDIDATES_LIMIT`, `_STOPWORDS`, `_UNIT_RE`, `_token_weight`). When tuning, edit there; the rescoring runs in Python after a SQL `OR LIKE` candidate fetch.

## Authentication & RBAC

Added in v7/v8. Cookie-based sessions via Starlette's `SessionMiddleware`.

- All routers in `backend/main.py` are mounted behind `Depends(require_auth)` **except** `/api/auth/*` and `/api/health`.
- Bootstrap flow: `GET /api/auth/bootstrap-status` → if `requires_setup`, `POST /api/auth/bootstrap` creates the first admin. After that, registration is closed; admins create users via `Usuarios`.
- Roles: `admin` | `operador`. Admin-only endpoints use `Depends(require_admin)`.
- Password storage: PBKDF2-SHA256, 210k iterations, base64-encoded salt+digest (see `core/auth.py:hash_password`).
- Forgotten access: an admin calls `POST /api/auth/users/{id}/reset-access` to set `must_reset_password=1` and return a one-time `reset_token` (24h). The user posts it to `/api/auth/complete-reset` with a new password.
- Session secret resolution: `NEMOOC_SESSION_SECRET` env var → else `nemo_oc/data/session_secret.txt` (auto-generated, gitignored).
- Secure cookies behind HTTPS: set `NEMOOC_SECURE_COOKIES=1`.

The frontend wraps protected routes with `<ProtectedApp>` which calls `/api/auth/me` and redirects to `/login` when unauthenticated.

## API surface (web)

All under `/api`. Authoritative source is the router files; this is a quick map:

| Prefix | File | What it does |
|--------|------|--------------|
| `/api/auth` | `api/auth_routes.py` | bootstrap, login, logout, me, users CRUD, password/access reset |
| `/api/ocs` | `api/oc_routes.py` | list/detail/stats/filtros, ingresada/estado/notas, sap-text, export, asignar itemcode, sugerencias, **analytics + review queue** |
| `/api/sync` | `api/sync_routes.py` | Mercado Público / Gmail sync + SSE progress + global logs |
| `/api/config` | `api/config_routes.py` | get/put settings.json fields, generate manual PDF |
| `/api/catalogs` | `api/catalog_routes.py` | upload xlsx (homologacion, maestra, cartera, correos, redsalud, licitaciones, private/{holding}), stats, search |
| `/api/holdings` | `api/holdings_routes.py` | CRUD holdings, RUTs, match rules |

Pydantic schemas live in `nemo_oc_web/backend/api/schemas.py` — check there for response shapes.

## Frontend conventions

- React Router v6 (`<BrowserRouter>` → `<ProtectedApp>` → `<AppLayout>` → page routes).
- TanStack Query for all data fetching; mutations invalidate query keys explicitly.
- Tailwind for styling. The look-and-feel was refactored Apr 2026 (`ESTADO_SISTEMA_2026-04-03.md`): split-screen list/detail, lateral collapsible filter panel, new Holdings/Estadísticas/Users pages, premium header on OC detail.
- SSE streamed through `useSyncSSE` (native `EventSource`).
- Column preferences (`ResizableTable`, SAP copy column order via `SapColumnConfigModal`) are persisted to `localStorage`.

## Key utilities to know

- `app/utils/rut_utils.py:rut_to_cliente_sap` — `"61.606.402-9"` → `"CN61606402"`.
- `app/utils/regex_utils.py:extraer_codigo_mp` — `"(2230498) ENVOLT…"` → `"2230498"`.
- `app/utils/clipboard_utils.py:generar_texto_sap` — tab-separated SAP B1 line text with comma decimal separator for Chile locale.
- `app/services/licitaciones_service.py` — Jaccard scoring engine (see "Domain model").
- `app/services/holding_admin_service.py` — read/write holdings, RUTs, rules; backs `/api/holdings`.

## Conventions and gotchas

- **Locale**: monetary/quantity output for SAP uses comma decimal (`,`). Don't change to dot.
- **Encoding**: Spanish identifiers and Spanish text in logs/UI. No emoji additions unless explicitly requested.
- **Concurrent DB access**: WAL mode handles read-while-write, but long-running scripts should still close connections (`finally: conn.close()`). Repositories already do this — mimic the pattern.
- **Catalog auto-import**: on first boot, if a table is empty and the corresponding xlsx exists in `nemo_oc/catalogs/`, the service auto-imports it. New catalogs should follow this same pattern (see `nemo_oc_web/backend/core/startup.py` and the parallel block in `nemo_oc/app/main.py:main`).
- **Don't commit** `app.db`, `settings.json`, `session_secret.txt`, `column_prefs.json`, logs, `node_modules`, dist/, the `RESPALDOS/` tree, or `ocs prueba/`. `.gitignore` already covers these.
- **PROYECTO_COMPLETO.md / ESTADO_SISTEMA_*.md** are docs in the repo root — they're updated by hand, not automatically. If you make material changes (new schema, new module, new API), update the relevant doc in the same commit.

## Git workflow for this assistant

- All development on this Claude session goes to branch `claude/claude-md-docs-C1IzS` (or the branch specified in the task brief).
- Commit with descriptive messages; create new commits rather than amending.
- After pushing, open a draft PR via the GitHub MCP tools (`mcp__github__create_pull_request`) targeting `main`.
- Repository is `samuel-aucan/nemooc` — do not touch any other repo.

## When in doubt

- **Schema/data question**: read `nemo_oc/app/db.py` end-to-end first.
- **API question**: open the relevant `nemo_oc_web/backend/api/*_routes.py`.
- **"Why does this OC have/lack X"**: trace through `sync_service.py` (public) or `sync_privado_service.py` (private) → `transform_service.py` → repositories.
- **Frontend behavior**: start in `nemo_oc_web/frontend/src/App.tsx` and follow the route.
