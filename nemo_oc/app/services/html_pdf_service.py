"""
Generacion on-demand de PDF desde snapshots HTML usando Chromium headless.
"""

from __future__ import annotations

import logging
import re
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


_KNOWN_BROWSER_PATHS = [
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
]


def render_html_to_pdf(
    html: str,
    *,
    source_locator: str = "",
    filename_hint: str = "documento",
) -> bytes:
    browser_paths = find_chromium_executables()
    if not browser_paths:
        raise RuntimeError(
            "No se encontro Microsoft Edge o Google Chrome para generar el PDF automaticamente."
        )

    prepared_html = prepare_html_document(html, source_locator=source_locator, auto_print=False)
    safe_name = _safe_filename(filename_hint or "documento")

    with tempfile.TemporaryDirectory(prefix="nemonkey_pdf_") as tmpdir:
        temp_dir = Path(tmpdir)
        input_html = temp_dir / f"{safe_name}.html"
        output_pdf = temp_dir / f"{safe_name}.pdf"
        profile_dir = temp_dir / "profile"
        profile_dir.mkdir(exist_ok=True)

        input_html.write_text(prepared_html, encoding="utf-8")
        attempts: list[str] = []

        for browser_path in browser_paths:
            for command in _build_pdf_commands(
                browser_path=browser_path,
                profile_dir=profile_dir,
                output_pdf=output_pdf,
                input_html=input_html,
            ):
                completed = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=90,
                )
                resolved_pdf = _resolve_generated_pdf(
                    expected_pdf=output_pdf,
                    temp_dir=temp_dir,
                    completed=completed,
                )
                summary = _format_attempt_summary(command, completed, resolved_pdf)
                attempts.append(summary)

                if completed.returncode == 0 and resolved_pdf is not None:
                    logger.info(
                        "PDF generado para %s con %s: %s bytes",
                        safe_name,
                        browser_path.name,
                        resolved_pdf.stat().st_size,
                    )
                    return resolved_pdf.read_bytes()

        logger.warning(
            "No se pudo generar PDF para %s. Intentos: %s",
            safe_name,
            " | ".join(attempts[-4:]),
        )
        last_attempt = attempts[-1] if attempts else "sin detalle adicional"
        raise RuntimeError(
            "El navegador termino sin producir el archivo PDF esperado. "
            f"{last_attempt[:280]}"
        )


def prepare_html_document(
    html: str,
    *,
    source_locator: str = "",
    auto_print: bool = False,
) -> str:
    prepared = _ensure_utf8_meta(html)
    prepared = _ensure_base_href(prepared, _origin_base(source_locator))
    prepared = _inject_print_styles(prepared)

    if auto_print:
        prepared = _inject_auto_print(prepared)
    return prepared


def find_chromium_executable() -> Path | None:
    candidates = find_chromium_executables()
    return candidates[0] if candidates else None


def find_chromium_executables() -> list[Path]:
    encontrados: list[Path] = []
    seen: set[str] = set()

    def add(candidate: Path | None) -> None:
        if not candidate or not candidate.exists():
            return
        normalized = str(candidate.resolve()).lower()
        if normalized in seen:
            return
        seen.add(normalized)
        encontrados.append(candidate.resolve())

    for candidate in _KNOWN_BROWSER_PATHS:
        add(candidate)

    search_roots = [
        Path(r"C:\Program Files (x86)\Microsoft"),
        Path(r"C:\Program Files\Google"),
        Path(r"C:\Program Files (x86)\Google"),
    ]
    patterns = ("**/msedge.exe", "**/chrome.exe")
    for root in search_roots:
        if not root.exists():
            continue
        for pattern in patterns:
            try:
                match = next(root.glob(pattern), None)
            except Exception:
                match = None
            add(match)
    return encontrados


def _build_pdf_commands(
    *,
    browser_path: Path,
    profile_dir: Path,
    output_pdf: Path,
    input_html: Path,
) -> list[list[str]]:
    return [
        [
            str(browser_path),
            "--headless",
            "--disable-gpu",
            "--run-all-compositor-stages-before-draw",
            "--allow-file-access-from-files",
            "--disable-web-security",
            "--no-first-run",
            "--no-default-browser-check",
            f"--user-data-dir={profile_dir}",
            "--print-to-pdf-no-header",
            f"--print-to-pdf={output_pdf}",
            "--virtual-time-budget=8000",
            input_html.resolve().as_uri(),
        ],
        [
            str(browser_path),
            "--headless=new",
            "--disable-gpu",
            "--allow-file-access-from-files",
            "--disable-web-security",
            "--no-first-run",
            "--no-default-browser-check",
            f"--user-data-dir={profile_dir}",
            "--print-to-pdf-no-header",
            f"--print-to-pdf={output_pdf}",
            "--virtual-time-budget=12000",
            input_html.resolve().as_uri(),
        ],
    ]


def _resolve_generated_pdf(
    *,
    expected_pdf: Path,
    temp_dir: Path,
    completed: subprocess.CompletedProcess[str],
) -> Path | None:
    for _ in range(12):
        if expected_pdf.exists() and expected_pdf.stat().st_size > 0:
            return expected_pdf
        time.sleep(0.25)

    stderr = completed.stderr or ""
    match = re.search(r"bytes written to file\s+(.+\.pdf)", stderr, flags=re.IGNORECASE)
    if match:
        candidate = Path(match.group(1).strip().strip('"'))
        if candidate.exists() and candidate.stat().st_size > 0:
            return candidate

    generated = sorted(
        [p for p in temp_dir.rglob("*.pdf") if p.exists() and p.stat().st_size > 0],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return generated[0] if generated else None


def _format_attempt_summary(
    command: list[str],
    completed: subprocess.CompletedProcess[str],
    resolved_pdf: Path | None,
) -> str:
    mode = next((arg for arg in command if arg.startswith("--headless")), "--headless?")
    output = (completed.stderr or completed.stdout or "").strip().replace("\r", " ").replace("\n", " ")
    truncated = output[:180]
    return (
        f"{Path(command[0]).name} {mode} rc={completed.returncode} "
        f"pdf={'ok' if resolved_pdf else 'missing'} {truncated}".strip()
    )


def _origin_base(source_locator: str) -> str:
    parsed = urlparse((source_locator or "").strip())
    if not parsed.scheme or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}/"


def _ensure_utf8_meta(html: str) -> str:
    if re.search(r"<meta[^>]+charset=", html, re.IGNORECASE):
        return re.sub(
            r"(<meta[^>]+charset=)(['\"]?)[^'\"> ]+(['\"]?)([^>]*>)",
            r"\1\2utf-8\3\4",
            html,
            count=1,
            flags=re.IGNORECASE,
        )
    if re.search(r"<head[^>]*>", html, re.IGNORECASE):
        return re.sub(
            r"(<head[^>]*>)",
            r"\1<meta charset=\"utf-8\"/>",
            html,
            count=1,
            flags=re.IGNORECASE,
        )
    return "<head><meta charset=\"utf-8\"/></head>" + html


def _ensure_base_href(html: str, base_href: str) -> str:
    if not base_href:
        return html
    base_tag = f'<base href="{base_href}"/>'
    if re.search(r"<base[^>]+href=", html, re.IGNORECASE):
        return re.sub(
            r"<base[^>]+href=[^>]*>",
            base_tag,
            html,
            count=1,
            flags=re.IGNORECASE,
        )
    if re.search(r"<head[^>]*>", html, re.IGNORECASE):
        return re.sub(
            r"(<head[^>]*>)",
            r"\1" + base_tag,
            html,
            count=1,
            flags=re.IGNORECASE,
        )
    return base_tag + html


def _inject_print_styles(html: str) -> str:
    style = """
<style>
@page {
  size: A4;
  margin: 12mm;
}
@media print {
  button,
  input[type="button"],
  input[type="submit"],
  [id*="buttons"],
  [class*="button"],
  [class*="Button"] {
    display: none !important;
  }
  body {
    margin: 0 !important;
    background: #fff !important;
  }
}
</style>
""".strip()
    if "</head>" in html.lower():
        return re.sub(r"</head>", style + "</head>", html, count=1, flags=re.IGNORECASE)
    return style + html


def _inject_auto_print(html: str) -> str:
    script = (
        "<script>"
        "window.addEventListener('load', function () {"
        "setTimeout(function () { window.print(); }, 350);"
        "});"
        "</script>"
    )
    if "</body>" in html.lower():
        return re.sub(r"</body>", script + "</body>", html, count=1, flags=re.IGNORECASE)
    return html + script


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return cleaned.strip("._-") or "documento"
