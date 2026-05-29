# NemoKey — Contexto para Claude Code

## Qué es este proyecto

Sistema de gestión de Órdenes de Compra (OC) de Mercado Público para Nemo Chile S.A.
Tiene 3 capas: core Python (`nemo_oc/`), backend web FastAPI (`nemo_oc_web/backend/`),
frontend React (`nemo_oc_web/frontend/`). Desplegado en Railway (backend) + Vercel (frontend).

**Stack:** Python 3.11 + FastAPI + React + TypeScript + Tailwind + Supabase PostgreSQL

## Arquitectura de despliegue

```
Browser → https://nemonkey.vercel.app (React SPA)
              ↓ proxy /api/* via vercel.json rewrites
          https://optimistic-courage-production-83bc.up.railway.app (FastAPI)
              ↓ lee/escribe
          Supabase PostgreSQL (mcluzxrzdldnvbsruyhp)
              ↑ también lee
          https://nemo-vendedores.vercel.app (Next.js PWA — app vendedores)
```

### Railway
- **Dockerfile** construye la imagen, pero `boot.py` parchea archivos desde GitHub
  `main` en cada arranque (workaround: webhook GitHub↔Railway está roto).
- `boot.py` descarga ~10 archivos de `https://raw.githubusercontent.com/samuel-aucan/nemooc/main/...`
- Start command: `python -c "import urllib.request as r; r.urlretrieve('https://raw.githubusercontent.com/samuel-aucan/nemooc/main/boot.py', '/app/boot.py'); exec(open('/app/boot.py').read())"`
- Env vars críticas: `DATA_SOURCE=supabase`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`,
  `SUPABASE_PAT`, `SUPABASE_PROJECT`, `NEMOOC_API_TICKET`, `NEMOOC_SMTP_PASSWORD`,
  `NEMOOC_SMTP_USER`, `NEMOOC_SESSION_SECRET`

### Vercel (frontend NemoKey)
- Deploy desde copia local: `cd nemo_oc_web/frontend && npx vercel deploy --prod --token <token>`
- `vercel.json` redirige `/api/*` al backend Railway
- Proyecto: `nemonkey` en scope `samuel-aucans-projects`

### Vercel (app vendedores)
- Deploy desde copia local: `cd "app vendedores" && npx vercel deploy --prod --token <token>`
- Proyecto: `nemo-vendedores`, URL: https://nemo-vendedores.vercel.app
- Env vars en Vercel: NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY,
  SUPABASE_SERVICE_ROLE_KEY, FASTAPI_URL (→Railway), MERCADO_PUBLICO_EMPRESA
- PENDIENTE: MERCADO_PUBLICO_TICKET (necesario para módulo GD admin)

## Capa de datos

### Supabase es la fuente de verdad en producción
- `DATA_SOURCE=supabase` en Railway → `repo_selector.py` usa `supabase_oc_repository.py`
- **NO usa el SDK Python de Supabase** (no instalado en Docker). Todo va por
  `_raw_sql()` → HTTP Management API (`requests` library).
- `_raw_sql()` definida en `supabase_oc_repository.py:50` y duplicada en
  `supabase_write_service.py:16`. Usa `SUPABASE_PAT` + `SUPABASE_PROJECT`.

### SQLite solo para desktop
- `nemo_oc/app/db.py` define esquema con 17 migraciones
- Desktop (tkinter `nemo_oc/app/ui/`) lee/escribe SQLite
- Web ignora SQLite en prod (protegido con try/except)

### Excel catalogs
- `HOMOLOGACION.xlsx`, `MAESTRA DE MATERIALES (PBI).xlsx`, etc.
- Copiados en la imagen Docker → `/app/nemo_oc/catalogs/`
- Usados por `sync_service.py` para homologar OCs al importar

## Tablas Supabase principales (proyecto mcluzxrzdldnvbsruyhp)

| Tabla | Dueño | Uso |
|-------|-------|-----|
| `oc_cabecera` | NemoKey (sync) | OCs importadas de MP |
| `oc_detalle` | NemoKey (sync) | Líneas de cada OC |
| `oc_estado_historial` | NemoKey | Log de cambios de estado |
| `oc_document_source` | NemoKey | Fuentes de documentos OC |
| `clientes` | app vendedores | Clientes con `codigo_sap` (prefijo "CN") |
| `carteras` | app vendedores | Carteras de vendedores |
| `profiles` | app vendedores | Usuarios (Supabase Auth) |
| `visitas` | app vendedores | Registro de visitas GPS |
| `gd_sesiones` / `gd_lineas` | app vendedores | Guías de despacho |

## Credenciales y tokens

**Archivo:** `.claude/tokens.md` (gitignored, local)
- Vercel token, Railway tokens (usar `claude-team`), URLs de despliegue
- Railway API: redeploy via GraphQL con token `claude-team`

**Seguridad resuelta:**
- `nemo_oc/config/default_settings.json` tenía secretos en repo público → LIMPIADO
- `config.py` ahora lee `NEMOOC_API_TICKET`, `NEMOOC_SMTP_PASSWORD`, etc. desde env-vars
- Las env-vars están seteadas en Railway

**Pendiente:** Rotar app-password Gmail (la vieja quedó en historial git del repo público)

## Auth
- NemoKey web: `auth_enabled=false` → sin login (decisión del usuario, documentada)
- app vendedores: Supabase Auth con roles `admin` / `vendedor`, RLS por cartera

## Flujo de sync de OCs
1. `sync_service.py` llama API Mercado Público → obtiene OCs
2. `oc_repository.save_oc()` guarda (en Supabase via `_raw_sql()`)
3. `supabase_write_service.upsert_oc()` hace INSERT/UPDATE con ON CONFLICT
4. `_lookup_cartera_id()` busca `clientes.codigo_sap` para asignar `cartera_id`

## Bugs resueltos en esta sesión

1. **OCs invisibles**: `sync_service.py` escribía a SQLite, web leía Supabase → cambiado
   a `repo_selector` con fallback
2. **500 en detalle OC tipo SE/AG/CC**: `sap_mode_service.py` usaba SQLite → try/except
3. **SDK Supabase no instalado**: todo migrado a `_raw_sql()` (Management API HTTP)
4. **Secretos en repo público**: `default_settings.json` limpiado, env-vars en Railway
5. **Cambios SAP no persistían**: `sync_homologacion` tenía UUID sin comillas en WHERE
   → `WHERE oc_id = 07b91bc4...` (aritmética) vs `WHERE oc_id = '07b91bc4...'` (correcto)
6. **Endpoint asignar retornaba solo `{ok:true}`**: frontend perdía datos → ahora retorna
   `itemcode_sap`, `descripcion_sap`, `estado_homologacion`
7. **Fallos silenciosos dual-write**: `except: pass` → `except as e: logger.warning()`

## Proyecto hermano: app vendedores

**Path:** `../app vendedores/` (ver su propio `CLAUDE.md`)
- PWA Next.js 16 + React 19 + Supabase (mismo proyecto)
- 3 módulos: Visitas (`/dashboard`), OC (`/oc`), GD (`/gd`)
- OC muta vía proxy `src/app/api/oc/[...path]/route.ts` → FastAPI Railway
- Deploy: https://nemo-vendedores.vercel.app (recién desplegada)
- Versión anterior de visitas: https://nemo-visitas.vercel.app (aún en uso, no archivar)

## Comandos útiles

```bash
# Redeploy Railway
curl -s -H "Authorization: Bearer <RAILWAY_TOKEN>" -H "Content-Type: application/json" \
  -X POST "https://backboard.railway.app/graphql/v2" \
  -d '{"query":"mutation { serviceInstanceRedeploy(serviceId: \"81f7c7cd-4e94-4827-b776-e0399fe20838\", environmentId: \"0bed9543-ee50-48d4-8c3b-2cfea0f776c1\") }"}'

# Deploy frontend NemoKey a Vercel
cd nemo_oc_web/frontend && npx vercel deploy --prod --token <VERCEL_TOKEN>

# Deploy app vendedores a Vercel  
cd "app vendedores" && npx vercel deploy --prod --token <VERCEL_TOKEN>

# Query Supabase directa (para debug)
curl -s -H "Authorization: Bearer <SUPABASE_PAT>" -H "Content-Type: application/json" \
  -X POST "https://api.supabase.com/v1/projects/<PROJECT>/database/query" \
  -d '{"query":"SELECT ... FROM oc_cabecera LIMIT 5"}'
```

## Pendientes para próxima sesión

### Bugs
1. **Textos amontonados** en campos "Cant SAP" / "P. SAP" del detalle OC en NemoKey
   (CSS/layout del formulario "Guardar y aprender")

### Features
2. **Indicador visual + auditoría de cambios SAP manuales**: badge "Editado"/"Manual"
   junto al itemcode + registro de quién/cuándo cambió. Visible en NemoKey y app vendedores.
   La tabla `oc_cambios_sap` ya existe en Supabase (app vendedores la usa para logging
   vía `/api/oc/cambios-sap`).

### Auditoría (Fases pendientes del plan)
3. **Fase 3 — Robustez**: quitar `supabase` de requirements.txt, mejorar logging de
   boot.py, documentar deploy Vercel
4. **Fase 4 — Optimización**: paginación server-side en app vendedores OcListPage
5. **Fase 5 — Documentación**: crear `PROYECTOS/AI_BRAIN.md` (mapa maestro), refrescar
   CLAUDE.md de cada repo, crear skills (`nemo-deploy`, `supabase-migrations`,
   `nemo-security-scan`)
6. **MERCADO_PUBLICO_TICKET** en Vercel para módulo GD de app vendedores
7. **Consolidar esquema Supabase** en un solo set de migraciones

### Archivado
8. Archivar `poc_railway/` y `poc_sse_standalone.py` (POCs completados)
9. `nemo_oc/app_qt/` es legacy muerto (PyQt) — marcar o archivar
10. `LOCALIZACION/nemo-visitas` NO archivar (sigue en producción en nemo-visitas.vercel.app)
