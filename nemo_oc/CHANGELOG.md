# CHANGELOG — NemoOC

Registro de cambios por versión/sesión de desarrollo.

---

## [2026-03-20] — Sesión inicial + correcciones

### Funcionalidades base
- Consumo de API Mercado Público (endpoint público, filtro CM)
- Homologación de productos desde HOMOLOGACION.xlsx → SAP
- Factor de Empaque: cantidad_sap = cantidad × F.EMP, precio_sap = precio / F.EMP
- Cliente SAP auto-generado desde RUT comprador (CN + dígitos)
- Persistencia en SQLite (WAL mode)
- UI dark con CustomTkinter: lista OCs, detalle, configuración, importar

### Correcciones aplicadas en esta sesión
- **Columnas ocultas**: fix `displaycolumns` — columnas desactivadas ahora desaparecen completamente (antes solo se achicaban a ancho 0)
- **Filtro de fecha**: cambiado a opt-in con checkbox; por defecto muestra todas las OCs sin filtrar
- **Fecha en tabla**: cambiado de `fecha_creacion` a `fecha_envio` (coincide con lo que muestra el portal de Mercado Público)
- **Copiar para SAP**: ahora copia solo las columnas visibles en pantalla, respetando orden del usuario
- **Separador decimal SAP**: precios y cantidades decimales usan coma (`,`) en lugar de punto (`.`) para compatibilidad con SAP B1 en locale Chile
- **Columnas independientes**: separación entre "Ver en tabla" (👁) y "Copiar a SAP" (📋) — configurables por separado en el picker de columnas
- **Catálogos automáticos**: HOMOLOGACION.xlsx y MAESTRA DE MATERIALES van en `catalogs/`; al iniciar en PC nuevo se importan solos
- **INSTALAR.bat**: instalador automático (descarga Python si no hay, instala dependencias, crea acceso directo con ícono mono)

### Archivos creados/modificados
- `app/config.py` — añadido `get_catalogs_dir()`, `get_default_homo_path()`, `get_default_maestra_path()`
- `app/main.py` — auto-importa catálogos si BD vacía al inicio
- `app/ui/frames/oc_detail_frame.py` — columnas con flag `copy_default`, picker con columna 📋, fix unpack
- `app/ui/frames/oc_list_frame.py` — checkbox fecha, muestra `fecha_envio`, fix filtro
- `app/repositories/oc_repository.py` — filtro y orden por `fecha_envio`
- `app/ui/frames/config_frame.py` — UI catálogos con estado ✓/✗ y botón Actualizar
- `catalogs/HOMOLOGACION.xlsx` — copiado desde carpeta padre
- `catalogs/MAESTRA DE MATERIALES (PBI).xlsx` — copiado desde carpeta padre
- `.gitignore` — creado
- `CHANGELOG.md` — creado
