#!/usr/bin/env python3
"""Generate styled HTML paper summaries from text files."""

from __future__ import annotations

import html
import json
import re
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "pappers_resumenes"
OUTPUT_DIR = ROOT / "pappers_html"
MANIFEST = OUTPUT_DIR / "index.json"


TITLE_PATTERNS = (
    re.compile(r"^\s*T[ií]tulo:\s*(.+)$", re.IGNORECASE),
    re.compile(r"^\s*📄\s*Paper:\s*(.+)$", re.IGNORECASE),
    re.compile(r"^\s*Paper:\s*(.+)$", re.IGNORECASE),
    re.compile(r"^\s*#\s+(.+)$"),
)


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "resumen"


def clean_title(value: str) -> str:
    value = value.strip().strip("*").strip()
    value = re.sub(r"^[\"“”']+|[\"“”']+$", "", value)
    return value


def title_from_text(path: Path, text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        for pattern in TITLE_PATTERNS:
            match = pattern.match(stripped)
            if match:
                return clean_title(match.group(1))

    generic_starts = (
        "aquí tienes",
        "claro",
        "este es",
        "esumen ejecutivo",
        "leí tu archivo",
        "perfecto",
        "resumen ejecutivo",
        "resumen general",
        "vamos",
        "voy a",
    )
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        lower = stripped.lower().lstrip("¡¿").strip()
        if lower.startswith(generic_starts):
            continue
        if len(stripped) > 8 and not stripped.startswith(("---", "*", "-", "[")):
            return clean_title(stripped)
    return path.stem.replace("-", " ").replace("_", " ").title()


def inline_markup(value: str) -> str:
    escaped = html.escape(value)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*(.+?)\*", r"<em>\1</em>", escaped)
    escaped = re.sub(r"`(.+?)`", r"<code>\1</code>", escaped)
    return escaped


def flush_list(items: list[str], output: list[str]) -> None:
    if not items:
        return
    output.append("<ul>")
    output.extend(f"<li>{inline_markup(item)}</li>" for item in items)
    output.append("</ul>")
    items.clear()


def text_to_html(text: str) -> str:
    blocks: list[str] = []
    list_items: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()

        if not stripped:
            flush_list(list_items, blocks)
            continue

        if stripped == "---":
            flush_list(list_items, blocks)
            blocks.append("<hr>")
            continue

        heading = re.match(r"^(#{1,4})\s+(.+)$", stripped)
        if heading:
            flush_list(list_items, blocks)
            level = min(len(heading.group(1)) + 1, 4)
            blocks.append(f"<h{level}>{inline_markup(heading.group(2))}</h{level}>")
            continue

        bullet = re.match(r"^(?:[-*•]|[0-9]+[.)])\s+(.+)$", stripped)
        indented_label = re.match(r"^([A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9][^:]{1,70}):\s+(.+)$", stripped)
        if bullet:
            list_items.append(bullet.group(1))
            continue
        if raw_line.startswith(("    ", "\t")) and indented_label:
            list_items.append(stripped)
            continue

        flush_list(list_items, blocks)

        label = re.match(r"^([^:]{2,80}):\s+(.+)$", stripped)
        if label:
            blocks.append(
                "<p><strong>"
                + inline_markup(label.group(1))
                + ":</strong> "
                + inline_markup(label.group(2))
                + "</p>"
            )
            continue

        blocks.append(f"<p>{inline_markup(stripped)}</p>")

    flush_list(list_items, blocks)
    return "\n".join(blocks)


def render_page(title: str, source_name: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="es">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)}</title>
    <style>
      :root {{
        --bg: #10151b;
        --paper: #f7f2e8;
        --ink: #17130f;
        --muted: #6b5b4b;
        --accent: #1e6b83;
        --accent-2: #8a2d2d;
        --rule: #d8c9ad;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        min-height: 100vh;
        color: var(--ink);
        background:
          linear-gradient(rgba(16, 21, 27, 0.72), rgba(16, 21, 27, 0.84)),
          repeating-linear-gradient(90deg, #17202a 0 1px, transparent 1px 46px),
          #10151b;
        font-family: Georgia, "Times New Roman", serif;
        line-height: 1.72;
      }}
      main {{
        width: min(980px, calc(100% - 32px));
        margin: 32px auto;
        padding: clamp(28px, 5vw, 58px);
        background: var(--paper);
        border: 1px solid var(--rule);
        box-shadow: 0 28px 70px rgba(0, 0, 0, 0.36);
      }}
      nav a {{
        color: var(--accent);
        font: 700 0.82rem Arial, sans-serif;
        letter-spacing: 0.08em;
        text-decoration: none;
        text-transform: uppercase;
      }}
      header {{
        margin: 26px 0 34px;
        padding-bottom: 24px;
        border-bottom: 3px double var(--rule);
      }}
      h1 {{
        margin: 0 0 12px;
        color: var(--ink);
        font-size: clamp(2rem, 5vw, 3.25rem);
        line-height: 1.08;
      }}
      .source {{
        margin: 0;
        color: var(--muted);
        font: 0.9rem Arial, sans-serif;
      }}
      h2, h3, h4 {{
        color: var(--accent);
        line-height: 1.22;
        margin: 2rem 0 0.8rem;
      }}
      h2 {{ font-size: 1.65rem; border-bottom: 2px solid var(--rule); padding-bottom: 0.35rem; }}
      h3 {{ color: var(--accent-2); font-size: 1.28rem; }}
      h4 {{ font-size: 1.05rem; font-family: Arial, sans-serif; text-transform: uppercase; letter-spacing: 0.06em; }}
      p {{ margin: 0 0 1rem; }}
      ul {{ margin: 0 0 1.2rem 1.2rem; padding: 0; }}
      li {{ margin: 0.42rem 0; }}
      code {{
        padding: 0.1rem 0.28rem;
        border-radius: 3px;
        background: #eadfc9;
        font-size: 0.9em;
      }}
      hr {{
        border: 0;
        border-top: 1px solid var(--rule);
        margin: 2rem 0;
      }}
      strong {{ color: #2b2119; }}
      @media (max-width: 640px) {{
        main {{ width: min(100% - 18px, 980px); margin: 9px auto; }}
      }}
    </style>
  </head>
  <body>
    <main>
      <nav><a href="../index.html">Volver al mapa</a></nav>
      <header>
        <h1>{html.escape(title)}</h1>
        <p class="source">Generado desde {html.escape(source_name)}</p>
      </header>
      <article>
        {body}
      </article>
    </main>
  </body>
</html>
"""


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)

    generated: list[str] = []
    skipped: list[str] = []

    for source in sorted(SOURCE_DIR.iterdir()):
        if not source.is_file():
            continue

        text = source.read_text(encoding="utf-8").strip()
        if not text:
            skipped.append(source.name)
            continue

        title = title_from_text(source, text)
        output_name = f"{slugify(source.stem)}.html"
        body = text_to_html(text)
        (OUTPUT_DIR / output_name).write_text(
            render_page(title, source.name, body),
            encoding="utf-8",
        )
        generated.append(output_name)

    existing = []
    if MANIFEST.exists():
        existing = json.loads(MANIFEST.read_text(encoding="utf-8"))

    files = sorted(
        {
            *[entry for entry in existing if isinstance(entry, str) and entry.endswith(".html")],
            *generated,
        }
    )
    MANIFEST.write_text(
        json.dumps(files, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Generated {len(generated)} HTML files.")
    if skipped:
        print("Skipped empty files: " + ", ".join(skipped))
    print(f"Updated {MANIFEST.relative_to(ROOT)} with {len(files)} entries.")


if __name__ == "__main__":
    main()
