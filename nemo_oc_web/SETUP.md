# Setup NemoOC Web

## Variables de Entorno (.env)

Copia `.env.example` a `.env` y configura:

```bash
cp .env.example .env
```

**CRÍTICO para producción:**
- `NEMOOC_SESSION_SECRET`: Genera con `python -c "import secrets; print(secrets.token_urlsafe(48))"`
- `NEMOOC_SECURE_COOKIES=true` en HTTPS
- `NEMOOC_SYNC_MAX_DAYS=90` para evitar DoS
- `NEMOOC_LOGIN_MAX_ATTEMPTS=5` y `NEMOOC_LOGIN_BLOCK_MINUTES=15`

## Estructura de Catálogos

Formatos Excel aceptados:

| Catálogo | Columnas Obligatorias |
|----------|----------------------|
| Homologación | codigo_cm, descripcion_cm, itemcode_sap, descripcion_sap, familia, subfamilia, unidad_medida |
| Maestra SAP | itemcode_sap, descripcion_sap, familia, subfamilia, unidad_medida, precio_referencia |
| Cartera | cod_cliente, rut, razon, comuna, region_nombre, cartera, vendedor |
| Correos | email, nombre, holding, activo |
| RedSalud | codigo_redsalud, descripcion_redsalud, itemcode_sap, descripcion_sap |
| Licitaciones | descripcion_comprador, descripcion_norm, itemcode_sap, descripcion_nemo, rut_comprador, frecuencia |

## Seguridad

1. **No guardar secretos en git**: `.env` está en `.gitignore`
2. **API Ticket**: Nunca se devuelve completo, solo últimos 4 caracteres en UI
3. **Rate Limiting**: 5 intentos fallidos = 15 min bloqueado
4. **SMTP/IMAP**: Credenciales se guardan pero nunca se devuelven al frontend
5. **Sincronización**: Máximo 90 días por solicitud (evita DoS)

## Desarrollo

```bash
# Backend
cd nemo_oc_web/backend
uvicorn main:app --reload

# Frontend
cd nemo_oc_web/frontend
npm run dev
```

## Producción

1. Generar `.env` con claves aleatorias seguras
2. Construir frontend: `npm run build`
3. Empaquetar con PyInstaller
4. Configurar HTTPS

## API Endpoints

**Auth:**
- `POST /api/auth/login` - Login
- `POST /api/auth/bootstrap` - Setup inicial
- `GET /api/auth/me` - Usuario actual

**OCs:**
- `GET /api/ocs` - Listar OCs
- `GET /api/ocs/{codigo}` - Detalle OC
- `POST /api/sync/mercado-publico` - Sincronizar (max 90 días)

**Catálogos:**
- `GET /api/catalogs/stats` - Conteos
- `POST /api/catalogs/{tipo}` - Subir catálogo
- `GET /api/catalogs/template/{tipo}` - Descargar template
- `GET /api/catalogs/aprendizaje/export` - Exportar aprendizaje
- `POST /api/catalogs/aprendizaje/import` - Importar aprendizaje

**Config:**
- `GET /api/config` - Configuración (credenciales enmascaradas)
- `PUT /api/config` - Actualizar configuración

## Troubleshooting

**"API ticket no configurado"**: Ir a Configuración > Mercado Público y poner el ticket

**"Demasiados intentos fallidos"**: Esperar 15 minutos o reiniciar la app

**"Rango de fechas excede 90 días"**: Dividir sincronización en múltiples solicitudes
