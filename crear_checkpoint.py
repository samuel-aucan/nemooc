"""
crear_checkpoint.py - Crea un respaldo versionado del proyecto NemoOC.

Uso:
    python crear_checkpoint.py v1.2.1 "fix-precio-sap" --title "Fix precio SAP"
    python crear_checkpoint.py v1.3.0 nueva-feature --dry-run

Que hace:
    1. Crea la carpeta RESPALDOS/YYYY-MM-DD_vX.Y.Z_descripcion/
    2. Copia codigo y archivos de configuracion relevantes
    3. Genera artefactos Git del estado actual
    4. Copia app.db, salvo que se use --skip-db
    5. Genera manifest.json y CHECKPOINT_vX.Y.Z.md
    6. Actualiza VERSION.json y RESPALDOS/INDICE_RESPALDOS.md
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESPALDOS_DIR = ROOT / "RESPALDOS"
VERSION_FILE = ROOT / "VERSION.json"
DB_PATH = ROOT / "nemo_oc" / "data" / "app.db"

EXCLUDED_DIR_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".venv",
    "%TEMP%",
    "__pycache__",
    "RESPALDOS",
    "build",
    "dist",
    "node_modules",
    "venv",
}
EXCLUDED_FILE_EXTENSIONS = {
    ".egg-info",
    ".log",
    ".pyc",
    ".pyo",
    ".sqlite-journal",
}
EXCLUDED_FILE_PREFIXES = ("PAQUETI",)

SOURCE_DIRECTORIES = [
    "nemo_oc/app",
    "nemo_oc/app_qt",
    "nemo_oc/config",
    "nemo_oc/assets",
    "nemo_oc/catalogs",
    "nemo_oc_web/backend",
    "nemo_oc_web/frontend/src",
    "nemo_oc_web/frontend/public",
]

SOURCE_FILES = [
    "CHANGELOG.md",
    "README.md",
    "VERSION.json",
    "nemo_oc/README.md",
    "nemo_oc/requirements.txt",
    "nemo_oc/requirements-build.txt",
    "nemo_oc_web/INSTALAR.md",
    "nemo_oc_web/requirements.txt",
    "nemo_oc_web/run.py",
    "nemo_oc_web/launcher.py",
    "nemo_oc_web/frontend/index.html",
    "nemo_oc_web/frontend/package.json",
    "nemo_oc_web/frontend/package-lock.json",
    "nemo_oc_web/frontend/postcss.config.js",
    "nemo_oc_web/frontend/tailwind.config.js",
    "nemo_oc_web/frontend/tsconfig.json",
    "nemo_oc_web/frontend/vite.config.ts",
    "crear_checkpoint.py",
]

SEMVER_RE = re.compile(r"^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")

DEFAULT_INDEX_TEMPLATE = """# Indice de Respaldos

Referencia rapida de checkpoints locales de NemoOC.

## Convencion
- Carpeta: `YYYY-MM-DD_vX.Y.Z_descripcion-corta`
- Fuente humana: `CHANGELOG.md`
- Fuente automatica actual: `VERSION.json`

## Versiones
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crea un checkpoint versionado dentro de RESPALDOS/."
    )
    parser.add_argument("version", help="Version semantica, por ejemplo v1.2.0")
    parser.add_argument(
        "description",
        nargs="+",
        help="Descripcion corta para la carpeta del checkpoint",
    )
    parser.add_argument(
        "--title",
        help="Titulo humano para VERSION.json e INDICE_RESPALDOS.md",
    )
    parser.add_argument(
        "--skip-db",
        action="store_true",
        help="No copia nemo_oc/data/app.db",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Muestra lo que haria sin escribir archivos",
    )
    return parser.parse_args()


def normalize_version(raw_version: str) -> str:
    match = SEMVER_RE.fullmatch(raw_version.strip())
    if not match:
        raise ValueError("La version debe usar el formato vX.Y.Z")
    return f"v{match.group(1)}.{match.group(2)}.{match.group(3)}"


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "checkpoint"


def humanize_slug(slug: str) -> str:
    return slug.replace("-", " ")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def run_command(args: list[str]) -> str:
    try:
        result = subprocess.run(
            args,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as exc:
        return f"(error ejecutando {' '.join(args)}: {exc})\n"

    parts: list[str] = []
    if result.stdout:
        parts.append(result.stdout.rstrip())
    if result.stderr:
        parts.append(result.stderr.rstrip())
    output = "\n".join(part for part in parts if part).strip()
    return f"{output}\n" if output else ""


def git_text(*args: str) -> str:
    return run_command(["git", *args])


def git_value(*args: str) -> str:
    return git_text(*args).strip()


def copy_directory(relative_dir: str, snapshot_root: Path) -> int:
    origin = ROOT / relative_dir
    if not origin.exists():
        return 0

    copied_files = 0
    destination_root = snapshot_root / relative_dir

    for source in origin.rglob("*"):
        relative_path = source.relative_to(origin)
        if any(part in EXCLUDED_DIR_NAMES for part in relative_path.parts):
            continue
        if source.is_dir():
            continue
        if source.suffix.lower() in EXCLUDED_FILE_EXTENSIONS:
            continue
        if source.name.startswith(EXCLUDED_FILE_PREFIXES):
            continue

        destination = destination_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied_files += 1

    return copied_files


def copy_file(relative_file: str, snapshot_root: Path) -> bool:
    origin = ROOT / relative_file
    if not origin.exists():
        return False
    destination = snapshot_root / relative_file
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(origin, destination)
    return True


def copy_database(backup_root: Path) -> tuple[bool, float | None]:
    if not DB_PATH.exists():
        return False, None

    destination = backup_root / "data" / "app.db"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DB_PATH, destination)
    size_mb = DB_PATH.stat().st_size / 1024 / 1024
    return True, round(size_mb, 2)


def build_checkpoint_markdown(metadata: dict) -> str:
    source_directories = "\n".join(
        f"- `{item}`" for item in metadata["source_directories"]
    )
    source_files = "\n".join(f"- `{item}`" for item in metadata["source_files"])

    database_section = (
        "- `data/app.db` - copia local de la base SQLite.\n"
        if metadata["database"]["included"]
        else "- Base de datos no incluida (`--skip-db` o archivo ausente).\n"
    )

    return f"""# Checkpoint {metadata["version"]}

**Fecha:** {metadata["date"]} {metadata["time"]}
**Titulo:** {metadata["title"]}
**Slug:** `{metadata["description_slug"]}`

## Que incluye este respaldo

### Directorios de codigo (`source_snapshot/`)
{source_directories}

### Archivos de apoyo y configuracion (`source_snapshot/`)
{source_files}

### Base de datos
{database_section}

### Git (`git/`)
- `git_status.txt` - estado del arbol de trabajo
- `tracked_changes.patch` - diff completo desde HEAD
- `git_log.txt` - ultimos 20 commits
- `untracked_files.txt` - archivos sin trackear
- `head.txt` - commit actual
- `branch.txt` - rama actual

### Metadata
- `manifest.json` - metadata estructurada del checkpoint

## Como restaurar desde este punto
1. Copia `source_snapshot/` sobre el directorio del proyecto.
2. Si incluiste base de datos, copia `data/app.db` a `nemo_oc/data/app.db`.
3. Si necesitas reproducir el estado tracked exacto, aplica:
   ```
   git apply git/tracked_changes.patch
   ```

## Nota
Este checkpoint es un respaldo de trabajo, no un release Git limpio.
"""


def build_index_entry(metadata: dict) -> str:
    backup_name = metadata["backup_name"]
    checkpoint_name = Path(metadata["checkpoint_file"]).name
    return f"""## [{metadata["version"]}] {metadata["date"]} {metadata["time"]} - {metadata["title"]}
- Carpeta: [{backup_name}]({backup_name}/)
- Checkpoint: [{checkpoint_name}]({backup_name}/{checkpoint_name})
- Manifest: [manifest.json]({backup_name}/manifest.json)
- Resumen: {metadata["title"]}.
"""


def upsert_index(indice_path: Path, version_tag: str, entry: str) -> None:
    if indice_path.exists():
        content = indice_path.read_text(encoding="utf-8")
    else:
        content = DEFAULT_INDEX_TEMPLATE

    if "## Versiones" not in content:
        content = DEFAULT_INDEX_TEMPLATE.rstrip() + "\n\n"

    entry_pattern = re.compile(
        rf"^## \[{re.escape(version_tag)}\].*?(?=^## \[|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    if entry_pattern.search(content):
        updated = entry_pattern.sub(entry.strip() + "\n\n", content)
    else:
        head, marker, tail = content.partition("## Versiones\n")
        if marker:
            updated = (
                f"{head}{marker}\n{entry.strip()}\n\n{tail.lstrip()}"
            )
        else:
            updated = DEFAULT_INDEX_TEMPLATE.rstrip() + "\n\n" + entry.strip() + "\n"

    write_text(indice_path, updated)


def main() -> int:
    args = parse_args()

    try:
        version_tag = normalize_version(args.version)
    except ValueError as exc:
        print(f"[ERROR] {exc}")
        return 1

    raw_description = " ".join(args.description).strip()
    slug = slugify(raw_description)
    title = args.title.strip() if args.title else humanize_slug(slug)

    now = datetime.now().astimezone()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")
    backup_name = f"{date_str}_{version_tag}_{slug}"
    backup_dir = RESPALDOS_DIR / backup_name
    snapshot_dir = backup_dir / "source_snapshot"
    git_dir = backup_dir / "git"

    print(f"[*] Checkpoint: {version_tag}")
    print(f"[*] Titulo: {title}")
    print(f"[*] Carpeta: {backup_dir}")
    print(f"[*] Dry run: {'si' if args.dry_run else 'no'}")

    if backup_dir.exists() and args.dry_run:
        print("[WARN] La carpeta ya existe. En dry-run no se escribe nada.")

    if backup_dir.exists() and not args.dry_run:
        answer = input(
            f"La carpeta '{backup_name}' ya existe. Sobreescribir? (s/n): "
        ).strip().lower()
        if answer != "s":
            print("[INFO] Operacion cancelada.")
            return 0
        shutil.rmtree(backup_dir)

    missing_paths: list[str] = []
    copied_dir_counts: dict[str, int] = {}
    copied_files_list: list[str] = []
    total_files = 0

    for relative_dir in SOURCE_DIRECTORIES:
        origin = ROOT / relative_dir
        if not origin.exists():
            missing_paths.append(relative_dir)
            continue
        if args.dry_run:
            copied_dir_counts[relative_dir] = 0
            continue
        copied_count = copy_directory(relative_dir, snapshot_dir)
        copied_dir_counts[relative_dir] = copied_count
        total_files += copied_count

    for relative_file in SOURCE_FILES:
        origin = ROOT / relative_file
        if not origin.exists():
            missing_paths.append(relative_file)
            continue
        if args.dry_run:
            copied_files_list.append(relative_file)
            continue
        if copy_file(relative_file, snapshot_dir):
            copied_files_list.append(relative_file)
            total_files += 1

    database_included = False
    database_size_mb = None
    if not args.skip_db and not args.dry_run:
        database_included, database_size_mb = copy_database(backup_dir)
    elif args.skip_db:
        print("[INFO] Base de datos omitida por --skip-db.")

    git_branch = git_value("rev-parse", "--abbrev-ref", "HEAD")
    git_head = git_value("rev-parse", "HEAD")

    metadata = {
        "app": "NemoOC",
        "version": version_tag,
        "title": title,
        "description_slug": slug,
        "date": date_str,
        "time": time_str,
        "timestamp": now.isoformat(timespec="seconds"),
        "backup_name": backup_name,
        "backup_dir": (Path("RESPALDOS") / backup_name).as_posix(),
        "snapshot_dir": (Path("RESPALDOS") / backup_name / "source_snapshot").as_posix(),
        "checkpoint_file": (
            Path("RESPALDOS") / backup_name / f"CHECKPOINT_{version_tag}.md"
        ).as_posix(),
        "manifest_file": (
            Path("RESPALDOS") / backup_name / "manifest.json"
        ).as_posix(),
        "source_directories": SOURCE_DIRECTORIES,
        "source_files": copied_files_list,
        "missing_paths": missing_paths,
        "copied_files": {
            "total": total_files,
            "directories": copied_dir_counts,
            "standalone_files": copied_files_list,
        },
        "database": {
            "included": database_included,
            "size_mb": database_size_mb,
            "source_path": DB_PATH.relative_to(ROOT).as_posix(),
        },
        "git": {
            "branch": git_branch,
            "head": git_head,
            "status_file": (
                Path("RESPALDOS") / backup_name / "git" / "git_status.txt"
            ).as_posix(),
            "patch_file": (
                Path("RESPALDOS") / backup_name / "git" / "tracked_changes.patch"
            ).as_posix(),
            "log_file": (
                Path("RESPALDOS") / backup_name / "git" / "git_log.txt"
            ).as_posix(),
            "untracked_file": (
                Path("RESPALDOS") / backup_name / "git" / "untracked_files.txt"
            ).as_posix(),
        },
    }

    print("[*] Directorios fuente considerados:")
    for relative_dir in SOURCE_DIRECTORIES:
        print(f"   - {relative_dir}")

    if copied_files_list:
        print("[*] Archivos extra considerados:")
        for relative_file in copied_files_list:
            print(f"   - {relative_file}")

    if missing_paths:
        print("[WARN] Rutas no encontradas:")
        for missing in missing_paths:
            print(f"   - {missing}")

    if args.dry_run:
        print("[OK] Dry-run completado. No se escribieron archivos.")
        return 0

    backup_dir.mkdir(parents=True, exist_ok=True)
    git_dir.mkdir(parents=True, exist_ok=True)

    write_text(git_dir / "git_status.txt", git_text("status"))
    write_text(git_dir / "tracked_changes.patch", git_text("diff", "HEAD"))
    write_text(git_dir / "git_log.txt", git_text("log", "--oneline", "-20"))
    write_text(
        git_dir / "untracked_files.txt",
        git_text("ls-files", "--others", "--exclude-standard"),
    )
    write_text(git_dir / "branch.txt", git_branch)
    write_text(git_dir / "head.txt", git_head)

    write_json(backup_dir / "manifest.json", metadata)
    write_text(
        backup_dir / f"CHECKPOINT_{version_tag}.md",
        build_checkpoint_markdown(metadata),
    )

    version_payload = {
        "app": metadata["app"],
        "current_version": metadata["version"],
        "title": metadata["title"],
        "description_slug": metadata["description_slug"],
        "date": metadata["date"],
        "time": metadata["time"],
        "timestamp": metadata["timestamp"],
        "checkpoint_dir": metadata["backup_dir"],
        "checkpoint_file": metadata["checkpoint_file"],
        "manifest_file": metadata["manifest_file"],
        "database_included": metadata["database"]["included"],
        "git": {
            "branch": metadata["git"]["branch"],
            "head": metadata["git"]["head"],
        },
    }
    write_json(VERSION_FILE, version_payload)

    upsert_index(
        RESPALDOS_DIR / "INDICE_RESPALDOS.md",
        version_tag,
        build_index_entry(metadata),
    )

    print(f"[OK] Checkpoint {version_tag} creado.")
    print(f"     Archivos copiados: {total_files}")
    if database_included and database_size_mb is not None:
        print(f"     app.db: {database_size_mb:.2f} MB")
    print(f"     Backup: {backup_dir}")
    print(f"     Version actual: {VERSION_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
