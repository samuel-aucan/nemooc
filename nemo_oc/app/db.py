"""
Gestion de base de datos SQLite para NemoOC.
Inicializa el schema, aplica migraciones y provee conexiones con WAL mode.
"""

import logging
import sqlite3
from pathlib import Path

from app.config import get_data_dir

logger = logging.getLogger(__name__)

DB_PATH = get_data_dir() / "app.db"


def get_connection() -> sqlite3.Connection:
    """Retorna una conexion SQLite con row_factory y foreign keys activos."""
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.execute("PRAGMA journal_mode = WAL")
    except Exception:
        conn.execute("PRAGMA journal_mode = DELETE")
    return conn


def backup_db() -> Path:
    """Crea un backup con timestamp en data/backups/."""
    import shutil
    from datetime import datetime

    backup_dir = DB_PATH.parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = backup_dir / f"app_{ts}.db"
    if DB_PATH.exists():
        shutil.copy2(str(DB_PATH), str(dest))
        logger.info(f"Backup creado: {dest}")
    return dest


def initialize_db() -> None:
    """Crea todas las tablas y vistas si no existen. Aplica migraciones."""
    conn = get_connection()
    try:
        _create_tables(conn)
        _apply_migrations(conn)
        conn.commit()
        logger.info(f"Base de datos inicializada en {DB_PATH}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error inicializando base de datos: {e}")
        raise
    finally:
        conn.close()


def _create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY
        );

        CREATE TABLE IF NOT EXISTS app_config (
            config_key   TEXT PRIMARY KEY,
            config_value TEXT,
            updated_at   TEXT
        );

        CREATE TABLE IF NOT EXISTS oc_cabecera (
            codigo_oc                 TEXT PRIMARY KEY,
            nombre_oc                 TEXT,
            codigo_estado_mp          INTEGER,
            estado_mp                 TEXT,
            codigo_tipo               TEXT,
            tipo_oc                   TEXT,
            fecha_creacion            TEXT,
            fecha_envio               TEXT,
            fecha_aceptacion          TEXT,
            fecha_cancelacion         TEXT,
            fecha_ultima_modificacion TEXT,
            total_neto                REAL,
            impuestos                 REAL,
            total                     REAL,
            porcentaje_iva            REAL,
            descuentos                REAL,
            cargos                    REAL,
            moneda                    TEXT,
            codigo_organismo          TEXT,
            nombre_organismo          TEXT,
            rut_unidad                TEXT,
            codigo_unidad             TEXT,
            nombre_unidad             TEXT,
            direccion_unidad          TEXT,
            comuna_unidad             TEXT,
            region_unidad             TEXT,
            codigo_licitacion         TEXT,
            direccion_despacho        TEXT,
            direccion_facturacion     TEXT,
            codigo_proveedor          TEXT,
            nombre_proveedor          TEXT,
            rut_proveedor             TEXT,
            cliente_sap_sugerido      TEXT,
            cantidad_lineas           INTEGER,
            estado_interno            TEXT DEFAULT 'Nueva',
            fecha_ingreso             TEXT,
            notas                     TEXT,
            created_at                TEXT,
            updated_at                TEXT
        );

        CREATE TABLE IF NOT EXISTS oc_detalle (
            id                        INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_oc                 TEXT NOT NULL,
            correlativo               INTEGER NOT NULL,
            codigo_categoria          INTEGER,
            categoria                 TEXT,
            codigo_producto_api       TEXT,
            codigo_mp                 TEXT,
            producto                  TEXT,
            especificacion_comprador  TEXT,
            especificacion_proveedor  TEXT,
            cantidad                  REAL,
            unidad                    TEXT,
            moneda                    TEXT,
            precio_neto               REAL,
            total_cargos              REAL,
            total_descuentos          REAL,
            total_impuestos           REAL,
            total                     REAL,
            factor_empaque            REAL DEFAULT 1,
            cantidad_sap              REAL,
            precio_sap                REAL,
            itemcode_sap              TEXT,
            descripcion_sap           TEXT,
            estado_homologacion       TEXT DEFAULT 'pendiente',
            created_at                TEXT,
            updated_at                TEXT,
            UNIQUE(codigo_oc, correlativo),
            FOREIGN KEY (codigo_oc) REFERENCES oc_cabecera(codigo_oc)
        );

        CREATE TABLE IF NOT EXISTS homologacion_productos (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_mp       TEXT NOT NULL,
            itemcode_sap    TEXT NOT NULL,
            descripcion_sap TEXT,
            factor_empaque  REAL DEFAULT 1,
            activo          INTEGER DEFAULT 1,
            origen_archivo  TEXT,
            created_at      TEXT,
            updated_at      TEXT,
            UNIQUE(codigo_mp)
        );

        CREATE TABLE IF NOT EXISTS sap_articulos (
            itemcode_sap    TEXT PRIMARY KEY,
            descripcion_sap TEXT,
            activo          INTEGER DEFAULT 1,
            origen_archivo  TEXT,
            created_at      TEXT,
            updated_at      TEXT
        );

        CREATE TABLE IF NOT EXISTS homologacion_redsalud (
            codigo_cliente  TEXT PRIMARY KEY,
            descripcion     TEXT,
            itemcode_sap    TEXT,
            precio_ref      REAL DEFAULT 0,
            origen_archivo  TEXT,
            created_at      TEXT,
            updated_at      TEXT
        );

        CREATE TABLE IF NOT EXISTS cartera_clientes (
            cod_cliente     TEXT PRIMARY KEY,
            rut             TEXT,
            razon           TEXT,
            comuna          TEXT,
            region_cod      TEXT,
            vendedor        TEXT,
            industria       TEXT,
            sector          TEXT,
            cartera         TEXT,
            region_nombre   TEXT,
            origen_archivo  TEXT,
            created_at      TEXT,
            updated_at      TEXT
        );

        CREATE VIEW IF NOT EXISTS vw_oc_detalle_sap AS
        SELECT
            d.codigo_oc,
            d.correlativo,
            d.codigo_mp,
            d.itemcode_sap,
            COALESCE(s.descripcion_sap, d.descripcion_sap) AS descripcion_sap,
            d.cantidad AS cantidad_oc,
            d.cantidad_sap,
            d.precio_neto,
            d.precio_sap,
            d.factor_empaque,
            d.estado_homologacion
        FROM oc_detalle d
        LEFT JOIN sap_articulos s ON d.itemcode_sap = s.itemcode_sap;
    """)


def _apply_migrations(conn: sqlite3.Connection) -> None:
    """Aplica migraciones incrementales controladas por schema_version."""
    row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
    current = row[0] if row[0] is not None else 0

    migrations = {
        2: """
            CREATE TABLE IF NOT EXISTS maestra_materiales (
                itemcode_sap      TEXT PRIMARY KEY,
                descripcion       TEXT,
                codigo_historico  TEXT,
                grupo             TEXT,
                categoria         TEXT,
                cant_display      REAL DEFAULT 0,
                cant_caja_master  REAL DEFAULT 0,
                origen_archivo    TEXT,
                created_at        TEXT,
                updated_at        TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_maestra_cod_hist
                ON maestra_materiales(codigo_historico);

            CREATE TABLE IF NOT EXISTS licitaciones_ref (
                id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                rut_comprador         TEXT,
                descripcion_comprador TEXT NOT NULL,
                descripcion_norm      TEXT NOT NULL,
                producto_code_old     TEXT,
                itemcode_sap          TEXT,
                descripcion_nemo      TEXT,
                frecuencia            INTEGER DEFAULT 1,
                origen_archivo        TEXT,
                created_at            TEXT,
                updated_at            TEXT,
                UNIQUE(descripcion_norm, rut_comprador, producto_code_old)
            );
            CREATE INDEX IF NOT EXISTS idx_lic_ref_norm
                ON licitaciones_ref(descripcion_norm);
            CREATE INDEX IF NOT EXISTS idx_lic_ref_rut
                ON licitaciones_ref(rut_comprador);
        """,
        3: """
            DROP TABLE IF EXISTS licitaciones_ref;
            CREATE TABLE licitaciones_ref (
                id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                rut_comprador         TEXT,
                descripcion_comprador TEXT NOT NULL,
                descripcion_norm      TEXT NOT NULL,
                producto_code_old     TEXT,
                itemcode_sap          TEXT,
                descripcion_nemo      TEXT,
                frecuencia            INTEGER DEFAULT 1,
                origen_archivo        TEXT,
                created_at            TEXT,
                updated_at            TEXT,
                UNIQUE(descripcion_norm, rut_comprador, producto_code_old)
            );
            CREATE INDEX IF NOT EXISTS idx_lic_ref_norm
                ON licitaciones_ref(descripcion_norm);
            CREATE INDEX IF NOT EXISTS idx_lic_ref_rut
                ON licitaciones_ref(rut_comprador);
        """,
        4: """
            CREATE TABLE IF NOT EXISTS holdings (
                id          TEXT PRIMARY KEY,
                nombre      TEXT NOT NULL,
                prefijo     TEXT NOT NULL,
                parser_type TEXT NOT NULL,
                homo_file   TEXT,
                activo      INTEGER DEFAULT 1,
                created_at  TEXT,
                updated_at  TEXT
            );

            CREATE TABLE IF NOT EXISTS holding_ruts (
                rut_norm        TEXT PRIMARY KEY,
                holding_id      TEXT NOT NULL,
                rut_display     TEXT,
                nombre_sucursal TEXT,
                FOREIGN KEY (holding_id) REFERENCES holdings(id)
            );

            CREATE TABLE IF NOT EXISTS homologacion_privados (
                codigo_cliente TEXT NOT NULL,
                holding_id     TEXT NOT NULL,
                descripcion    TEXT,
                itemcode_sap   TEXT,
                precio_ref     REAL DEFAULT 0,
                origen_archivo TEXT,
                created_at     TEXT,
                updated_at     TEXT,
                PRIMARY KEY (codigo_cliente, holding_id)
            );
        """,
        5: """
            CREATE TABLE IF NOT EXISTS holding_match_rules (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                holding_id TEXT NOT NULL,
                rule_type  TEXT NOT NULL,
                rule_value TEXT NOT NULL,
                prioridad  INTEGER DEFAULT 100,
                activo     INTEGER DEFAULT 1,
                notas      TEXT,
                created_at TEXT,
                updated_at TEXT,
                UNIQUE(holding_id, rule_type, rule_value),
                FOREIGN KEY (holding_id) REFERENCES holdings(id)
            );
            CREATE INDEX IF NOT EXISTS idx_holding_match_rules_lookup
                ON holding_match_rules(rule_type, rule_value, activo, prioridad);

            CREATE TABLE IF NOT EXISTS holding_catalog_files (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                holding_id        TEXT NOT NULL,
                catalog_kind      TEXT NOT NULL,
                filename          TEXT,
                original_filename TEXT,
                file_path         TEXT,
                checksum          TEXT,
                activo            INTEGER DEFAULT 1,
                created_at        TEXT,
                updated_at        TEXT,
                FOREIGN KEY (holding_id) REFERENCES holdings(id)
            );
            CREATE INDEX IF NOT EXISTS idx_holding_catalog_files_holding
                ON holding_catalog_files(holding_id, catalog_kind, activo);

            CREATE TABLE IF NOT EXISTS oc_privado_auditoria (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo_oc          TEXT NOT NULL,
                holding_id         TEXT,
                rut_emisor_norm    TEXT,
                emisor_detectado   TEXT,
                remitente_email    TEXT,
                asunto_email       TEXT,
                metodo_deteccion   TEXT,
                confianza          REAL DEFAULT 0,
                parser_usado       TEXT,
                precio_validacion  TEXT,
                detalle_validacion TEXT,
                requiere_revision  INTEGER DEFAULT 0,
                created_at         TEXT,
                updated_at         TEXT,
                FOREIGN KEY (codigo_oc) REFERENCES oc_cabecera(codigo_oc),
                FOREIGN KEY (holding_id) REFERENCES holdings(id)
            );
            CREATE INDEX IF NOT EXISTS idx_oc_privado_auditoria_codigo
                ON oc_privado_auditoria(codigo_oc);
        """,
        6: """
            CREATE TABLE IF NOT EXISTS holding_match_rules (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                holding_id TEXT NOT NULL,
                rule_type  TEXT NOT NULL,
                rule_value TEXT NOT NULL,
                prioridad  INTEGER DEFAULT 100,
                activo     INTEGER DEFAULT 1,
                notas      TEXT,
                created_at TEXT,
                updated_at TEXT,
                UNIQUE(holding_id, rule_type, rule_value),
                FOREIGN KEY (holding_id) REFERENCES holdings(id)
            );
            CREATE INDEX IF NOT EXISTS idx_holding_match_rules_lookup
                ON holding_match_rules(rule_type, rule_value, activo, prioridad);

            CREATE TABLE IF NOT EXISTS holding_catalog_files (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                holding_id        TEXT NOT NULL,
                catalog_kind      TEXT NOT NULL,
                filename          TEXT,
                original_filename TEXT,
                file_path         TEXT,
                checksum          TEXT,
                activo            INTEGER DEFAULT 1,
                created_at        TEXT,
                updated_at        TEXT,
                FOREIGN KEY (holding_id) REFERENCES holdings(id)
            );
            CREATE INDEX IF NOT EXISTS idx_holding_catalog_files_holding
                ON holding_catalog_files(holding_id, catalog_kind, activo);

            CREATE TABLE IF NOT EXISTS oc_privado_auditoria (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo_oc          TEXT NOT NULL,
                holding_id         TEXT,
                rut_emisor_norm    TEXT,
                emisor_detectado   TEXT,
                remitente_email    TEXT,
                asunto_email       TEXT,
                metodo_deteccion   TEXT,
                confianza          REAL DEFAULT 0,
                parser_usado       TEXT,
                precio_validacion  TEXT,
                detalle_validacion TEXT,
                requiere_revision  INTEGER DEFAULT 0,
                created_at         TEXT,
                updated_at         TEXT,
                FOREIGN KEY (codigo_oc) REFERENCES oc_cabecera(codigo_oc),
                FOREIGN KEY (holding_id) REFERENCES holdings(id)
            );
            CREATE INDEX IF NOT EXISTS idx_oc_privado_auditoria_codigo
                ON oc_privado_auditoria(codigo_oc);
        """,
        7: """
            CREATE TABLE IF NOT EXISTS usuarios (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                username       TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash  TEXT NOT NULL,
                nombre_completo TEXT,
                rol            TEXT NOT NULL DEFAULT 'admin',
                activo         INTEGER NOT NULL DEFAULT 1,
                last_login_at  TEXT,
                created_at     TEXT,
                updated_at     TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_usuarios_username
                ON usuarios(username);
        """,
        8: """
            ALTER TABLE usuarios ADD COLUMN must_reset_password INTEGER NOT NULL DEFAULT 0;
            ALTER TABLE usuarios ADD COLUMN reset_token_hash TEXT;
            ALTER TABLE usuarios ADD COLUMN reset_token_expires_at TEXT;
        """,
        9: """
            SELECT 1;
        """,
        10: """
            CREATE INDEX IF NOT EXISTS idx_oc_detalle_codigo_oc
                ON oc_detalle(codigo_oc);
            CREATE INDEX IF NOT EXISTS idx_oc_detalle_estado_homo
                ON oc_detalle(estado_homologacion);
            CREATE INDEX IF NOT EXISTS idx_oc_detalle_itemcode
                ON oc_detalle(itemcode_sap);
        """,
    }

    for version in sorted(v for v in migrations if v > current):
        logger.info(f"Aplicando migracion v{version}")
        conn.executescript(migrations[version])
        conn.execute("INSERT OR REPLACE INTO schema_version VALUES (?)", (version,))

    if current == 0:
        conn.execute("INSERT OR REPLACE INTO schema_version VALUES (1)")

    if current < 6:
        _seed_holdings(conn)
        _seed_holding_match_rules(conn)

    _ensure_column(conn, "oc_cabecera", "codigo_licitacion", "TEXT")
    _ensure_column(conn, "oc_cabecera", "direccion_despacho", "TEXT")
    _ensure_column(conn, "oc_cabecera", "direccion_facturacion", "TEXT")


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    existing = {
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column in existing:
        return
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _seed_holdings(conn: sqlite3.Connection) -> None:
    """Inserta holdings iniciales y migra datos existentes de homologacion_redsalud."""
    from datetime import datetime

    now = datetime.now().isoformat()

    holdings = [
        ("redsalud", "Red Salud", "RS", "redsalud", "HOMO RED SALUD.xlsx"),
        ("indisa", "Clinica Indisa", "IN", "indisa", "HOMO INDISA.xlsx"),
        ("banmedica", "Banmedica", "BM", "banmedica", "HOMO BANMEDICA.xlsx"),
        ("achs", "Asociacion Chilena de Seguridad", "AC", "achs", "HOMO ACHS.xlsx"),
    ]
    for h in holdings:
        conn.execute("""
            INSERT OR IGNORE INTO holdings (id, nombre, prefijo, parser_type, homo_file, activo, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?)
        """, (*h, now, now))

    ruts = [
        ("780405201", "redsalud", "78040520-1", "CLINICA AVANSALUD S.A."),
        ("780535601", "redsalud", "78053560-1", "SERVICIOS MEDICOS TABANCURA S.P.A."),
        ("968859307", "redsalud", "96885930-7", "CLINICA BICENTENARIO S.A."),
        ("965988505", "redsalud", "96598850-5", "CLINICA IQUIQUE S.A."),
        ("995337908", "redsalud", "99533790-8", "CLINICA REGIONAL DEL ELQUI SPA"),
        ("995687208", "redsalud", "99568720-8", "CLINICA VALPARAISO SPA"),
        ("789182906", "redsalud", "78918290-6", "CLINICA DE SALUD INTEGRAL S.A."),
        ("967745804", "redsalud", "96774580-4", "INMOBILIARIA INVERSALUD SPA"),
        ("969424002", "redsalud", "96942400-2", "MEGASALUD S.A."),
        ("920510000", "indisa", "92051000-0", "CLINICA INDISA"),
        ("907530000", "banmedica", "90753000-0", "CLINICA SANTA MARIA SPA"),
        ("703601006", "achs", "70360100-6", "ASOCIACION CHILENA DE SEGURIDAD"),
    ]
    for r in ruts:
        conn.execute("""
            INSERT OR IGNORE INTO holding_ruts (rut_norm, holding_id, rut_display, nombre_sucursal)
            VALUES (?, ?, ?, ?)
        """, r)

    try:
        rows = conn.execute(
            "SELECT codigo_cliente, descripcion, itemcode_sap, precio_ref, origen_archivo, created_at, updated_at "
            "FROM homologacion_redsalud"
        ).fetchall()
        for row in rows:
            conn.execute("""
                INSERT OR IGNORE INTO homologacion_privados
                    (codigo_cliente, holding_id, descripcion, itemcode_sap, precio_ref, origen_archivo, created_at, updated_at)
                VALUES (?, 'redsalud', ?, ?, ?, ?, ?, ?)
            """, (row[0], row[1], row[2], row[3], row[4], row[5], row[6]))
        logger.info(f"Migrados {len(rows)} registros de homologacion_redsalud a homologacion_privados")
    except Exception as e:
        logger.warning(f"No se pudo migrar homologacion_redsalud: {e}")


def _seed_holding_match_rules(conn: sqlite3.Connection) -> None:
    """Inserta reglas basicas para deteccion de holdings privados."""
    from datetime import datetime

    now = datetime.now().isoformat()
    rules = [
        ("redsalud", "pdf_rut", "780405201", 10, "Rut emisor RedSalud"),
        ("redsalud", "pdf_rut", "780535601", 10, "Rut emisor RedSalud"),
        ("redsalud", "pdf_rut", "968859307", 10, "Rut emisor RedSalud"),
        ("redsalud", "pdf_rut", "965988505", 10, "Rut emisor RedSalud"),
        ("redsalud", "pdf_rut", "995337908", 10, "Rut emisor RedSalud"),
        ("redsalud", "pdf_rut", "995687208", 10, "Rut emisor RedSalud"),
        ("redsalud", "pdf_rut", "789182906", 10, "Rut emisor RedSalud"),
        ("redsalud", "pdf_rut", "967745804", 10, "Rut emisor RedSalud"),
        ("redsalud", "pdf_rut", "969424002", 10, "Rut emisor RedSalud"),
        ("redsalud", "pdf_text", "N CONTRATO MARCO", 40, "Formato SAP RedSalud"),
        ("indisa", "pdf_rut", "920510000", 10, "Rut emisor INDISA"),
        ("indisa", "pdf_text", "INSTITUTO DE DIAGNOSTICO S.A.", 20, "Texto empresa INDISA"),
        ("indisa", "pdf_text", "CLINICA INDISA", 20, "Sucursal INDISA"),
        ("banmedica", "pdf_rut", "907530000", 10, "Rut Clinica Santa Maria"),
        ("banmedica", "pdf_text", "CLINICA SANTA MARIA", 20, "Texto empresa Banmedica"),
        ("achs", "pdf_rut", "703601006", 10, "Rut ACHS"),
        ("achs", "pdf_text", "ASOCIACION CHILENA DE SEGURIDAD", 20, "Texto empresa ACHS"),
        ("achs", "email_from", "adquisiciones@achs.cl", 20, "Remitente habitual ACHS"),
    ]

    for holding_id, rule_type, rule_value, prioridad, notas in rules:
        conn.execute("""
            INSERT OR IGNORE INTO holding_match_rules
                (holding_id, rule_type, rule_value, prioridad, activo, notas, created_at, updated_at)
            VALUES (?, ?, ?, ?, 1, ?, ?, ?)
        """, (holding_id, rule_type, rule_value, prioridad, notas, now, now))
