# NemoOC — Gestión de Órdenes de Compra Mercado Público

Herramienta interna portable para Nemo Chile S.A.
Consulta, homologa y prepara para SAP las Órdenes de Compra de Convenio Marco desde Mercado Público.

---

## Características

- Descarga automática de OCs CM (Convenio Marco) desde la API de Mercado Público
- Homologación automática de productos usando archivo HOMOLOGACION.xlsx
- Cálculo de Cantidad SAP y Precio SAP con Factor de Empaque
- Cliente SAP sugerido generado automáticamente desde RUT del comprador (`CN` + RUT)
- Copia tabla tabulada lista para pegar en SAP Business One (ItemCode | Desc | Cant SAP | Precio SAP)
- Bandeja de OCs con filtros por estado, fecha y búsqueda
- Marcado de OCs como ingresadas con fecha automática
- Notas internas por OC
- Exportación a Excel
- Auto-sync configurable al iniciar
- Base de datos SQLite local (sin servidor)
- 100% portable: corre desde pendrive o carpeta local

---

## Requisitos

- Windows 11 (x64)
- Python 3.11 o superior (solo para desarrollo / build)
- Ticket de API de Mercado Público (gratuito, solicitado en [www.mercadopublico.cl](https://www.mercadopublico.cl))

---

## Estructura del proyecto

```
nemo_oc/
├── app/
│   ├── main.py                    # Punto de entrada
│   ├── config.py                  # Configuración portable
│   ├── db.py                      # Inicialización SQLite
│   ├── models/                    # Dataclasses (OC, Línea, Homologación)
│   ├── repositories/              # Acceso a base de datos
│   ├── services/                  # Lógica de negocio y API
│   └── ui/                        # Interfaz CustomTkinter
├── data/                          # Base de datos SQLite (auto-creada)
├── config/                        # settings.json (ticket, preferencias)
├── logs/                          # app.log rotativo
├── assets/                        # Íconos y recursos
├── requirements.txt
├── build_portable.bat
└── README.md
```

---

## Cómo ejecutar en modo desarrollo

```bash
# 1. Clonar / descomprimir el proyecto
# 2. Crear entorno virtual (recomendado)
python -m venv .venv
.venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar
python app/main.py
```

---

## Cómo generar la versión portable (.exe)

```bash
# Desde la carpeta raíz del proyecto:
build_portable.bat
```

El ejecutable queda en `dist\NemoOC_portable\NemoOC.exe`.

**Contenido de la carpeta portable:**
```
NemoOC_portable/
├── NemoOC.exe     ← Ejecutar esto
├── data/          ← BD SQLite (auto-creada en primer uso)
├── config/        ← settings.json con ticket y preferencias
└── logs/          ← Logs rotativos
```

---

## Primera vez: configurar la aplicación

1. Ejecutar `NemoOC.exe`
2. Ir a **Configuración**
3. Ingresar el **Ticket de API** de Mercado Público
4. Importar **HOMOLOGACION.xlsx** (catálogo de Convenio Marco)
5. Importar **Maestra de Materiales** (opcional, para descripciones SAP oficiales)
6. Hacer clic en **Guardar configuración**
7. Ir a **Importar** y descargar las OCs del período deseado

---

## Reglas de negocio importantes

### Cliente SAP sugerido
Se construye automáticamente desde el RUT de la unidad compradora:

```
RutUnidad: "61.606.402-9"
→ quitar puntos: "61606402-9"
→ quitar guión + dígito: "61606402"
→ añadir CN: "CN61606402"
```

### Extracción de código MP
El código de producto se extrae del campo `EspecificacionComprador`:

```
"(2230498) ENVOLTURA NEMO POLIPROPILENO..."
→ codigo_mp: "2230498"
```

### Factor de Empaque
La columna **F. EMP** de HOMOLOGACION.xlsx indica unidades por paquete.

```
Ejemplo:
  F.EMP = 100  (el producto viene en cajas de 100 unidades)
  OC Cantidad = 4 cajas
  OC PrecioNeto = 99.479 por caja

  → Cantidad SAP = 4 × 100 = 400 unidades
  → Precio SAP = 99.479 / 100 = 994,79 por unidad
```

**El portapapeles SAP usará siempre los valores calculados (Cantidad SAP y Precio SAP).**

### Filtro OCs CM
Solo se descargan y muestran OCs de tipo Convenio Marco (`Tipo = "CM"`).
Las demás OCs (licitaciones, trato directo, etc.) se ignoran completamente.

---

## Columnas de HOMOLOGACION.xlsx esperadas

| Columna | Campo | Uso |
|---------|-------|-----|
| A — ID | `codigo_mp` | Llave de homologación (mismo número entre paréntesis en EspecificacionComprador) |
| B — TIPO | tipo | Categoría del producto |
| C — MARCA | marca | Marca del producto |
| D — COD NEMO | cod_nemo | Código interno Nemo |
| E — COD SAP | `itemcode_sap` | Código SAP que va al portapapeles |
| F — MODELO | `descripcion_sap` | Descripción SAP |
| G — PRECIO ID | precio_id | Referencia (no se usa en cálculos) |
| H — F. EMP | `factor_empaque` | **Factor de empaque crítico** |
| I — PRECIO UNI | precio_uni | Referencia (no se usa en cálculos) |
| J — Activo | activo | Se homologa independientemente del valor |

---

## Formato portapapeles SAP

El botón **"Copiar tabla para SAP"** genera texto listo para pegar en SAP Business One:

```
ALG00002	TÓRULA CHICA 0.5 GR BOLSA 100 UNIDADES	400	3.88
BOB25100	BOBINA ESTERILIZACIÓN 25CM X 100M	800	2.35
```

Columnas: `ItemCode` | `Descripción SAP` | `Cantidad SAP` | `Precio SAP`
Separador: TAB
Salto de línea: CRLF (Windows)
Sin encabezados

---

## Dependencias utilizadas

| Librería | Versión | Justificación |
|----------|---------|---------------|
| customtkinter | ≥5.2.2 | UI moderna y premium con soporte dark/light |
| requests | ≥2.31.0 | Consumo API Mercado Público |
| openpyxl | ≥3.1.2 | Lectura HOMOLOGACION.xlsx y exportación |
| tkcalendar | ≥1.6.1 | Selector de fechas visual (evita errores de formato) |
| pyinstaller | ≥6.3.0 | Empaquetado portable Windows |

Todas las dependencias son gratuitas y de código abierto.

---

## Mejoras sugeridas para v2

- Notificación Windows toast al detectar OCs nuevas
- Dashboard con gráficas (montos por mes, OCs por organismo)
- Historial de cambios de estado por OC
- Sincronización automática programada (Windows Task Scheduler)
- Búsqueda y filtro por múltiples organismos simultáneamente
- Soporte de múltiples proveedores (actualmente fijo para Nemo Chile S.A.)

---

## Soporte técnico

Para consultas o problemas, contactar al equipo de TI interno de Nemo Chile S.A.

---

*NemoOC v1.0 — Uso interno Nemo Chile S.A. — No distribuir externamente.*
