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
PDF_DIR = ROOT / "pappers_pdf"
PDF_MAP_FILE = PDF_DIR / "map.json"
FIGURES_DIR = OUTPUT_DIR / "figures"
MANIFEST = OUTPUT_DIR / "index.json"

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}


TITLE_PATTERNS = (
    re.compile(r"^\s*T[ií]tulo:\s*(.+)$", re.IGNORECASE),
    re.compile(r"^\s*📄\s*Paper:\s*(.+)$", re.IGNORECASE),
    re.compile(r"^\s*Paper:\s*(.+)$", re.IGNORECASE),
    re.compile(r"^\s*#\s+(.+)$"),
)

QUOTED_TITLE_PATTERNS = (
    re.compile(
        r"(?:paper|art[ií]culo|libro/art[ií]culo|trabajo)(?:\s+(?:de\s+revisi[oó]n|titulado|sobre))?\s+[*_]*[\"“](.+?)[\"”][*_]*(?:\s*\(([^)]+)\))?",
        re.IGNORECASE,
    ),
    re.compile(r"^[*_]*[\"“](.+?)[\"”][*_]*$"),
)

DESCRIPTIVE_TITLE_PATTERNS = (
    re.compile(
        r"trabajo\s+sobre\s+(?:el\s+dataset\s+)?(.+?)(?::|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"algoritmo\s+novedoso\s+llamado\s+([A-Z0-9-]+)\s+\(([^)]+)\)",
        re.IGNORECASE,
    ),
    re.compile(
        r"c[oó]mo\s+se\s+forma\s+(?:el\s+)?(.+?)\s+y\s+c[oó]mo",
        re.IGNORECASE,
    ),
)

GENERIC_HEADINGS = {
    "aportes principales del paper",
    "cómo lo hacen (métodos y setup)",
    "cómo podrías usarlo (si estás simulando cu-ni)",
    "conceptos clave para recordar",
    "conclusión",
    "conclusión del paper",
    "explicación detallada por secciones",
    "figuras y captiones importantes",
    "idea central del trabajo",
    "limitaciones",
    "limitaciones (implícitas del setup)",
    "limitaciones y desafíos",
    "objetivo principal",
    "puntos clave del trabajo",
    "qué aportan (interpretación)",
    "qué estudia",
    "recursos destacados",
    "resultados principales",
    "resumen del paper",
    "resumen detallado",
    "resumen general",
}


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "resumen"


def clean_title(value: str) -> str:
    value = re.sub(r"^\s*#+\s*", "", value)
    value = value.strip().strip("*").strip()
    value = re.sub(r"^[^\wÁÉÍÓÚÜÑáéíóúüñ¿¡]+", "", value).strip()
    value = re.sub(r"^[\"“”']+|[\"“”']+$", "", value)
    value = value.rstrip(":;.").strip()
    return value


def sentence_case(value: str) -> str:
    value = clean_title(value)
    return value[:1].upper() + value[1:] if value else value


def clean_author(value: str) -> str:
    value = re.sub(r"\*|_", "", value).strip()
    value = re.split(r",\s*(?:Journal|Nature|Phys|IEEE|Science|202[0-9]|19[0-9]{2})", value, maxsplit=1)[0]
    return value.strip()


def is_generic_heading(value: str) -> bool:
    normalized = clean_title(value.lower()).lower().replace("–", "-").replace("—", "-")
    normalized = normalized.strip("¡!¿?").strip()
    return normalized in GENERIC_HEADINGS


def title_from_text(path: Path, text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    for index, stripped in enumerate(lines):
        for pattern in TITLE_PATTERNS:
            match = pattern.match(stripped)
            if match and not is_generic_heading(match.group(1)):
                return clean_title(match.group(1))

        for pattern in QUOTED_TITLE_PATTERNS:
            match = pattern.search(stripped)
            if not match:
                continue

            title = clean_title(match.group(1))
            author = clean_author(match.group(2) if match.lastindex and match.lastindex >= 2 else "")
            if not author:
                for next_line in lines[index + 1 : index + 4]:
                    author_match = re.match(r"^\(([^)]+)\)", next_line)
                    if author_match:
                        author = clean_author(author_match.group(1))
                        break
            return f"{title} — {author}" if author else title

        for pattern in DESCRIPTIVE_TITLE_PATTERNS:
            match = pattern.search(stripped)
            if not match:
                continue
            if match.lastindex and match.lastindex >= 2:
                title = f"{sentence_case(match.group(1))}: {clean_title(match.group(2))}"
            else:
                title = sentence_case(match.group(1))
            if title and len(title) > 8:
                return title

    generic_starts = (
        "aquí tienes",
        "claro",
        "este es",
        "esumen ejecutivo",
        "leí tu archivo",
        "laro",
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
        lower = re.sub(r"^[^\wáéíóúüñ]+", "", stripped.lower()).lstrip("¡¿").strip()
        if lower.startswith(generic_starts):
            continue
        if is_generic_heading(lower):
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


def load_figures_gallery(slug: str) -> str:
    """Return figures-section HTML if extracted figures exist for this slug, else ''."""
    figures_dir = FIGURES_DIR / slug
    if not figures_dir.is_dir():
        return ""

    images = sorted(f for f in figures_dir.iterdir() if f.suffix.lower() in IMAGE_EXTS)
    if not images:
        return ""

    items: list[str] = []
    for img in images:
        page_match = re.search(r"_p(\d+)\.", img.name)
        caption = f"Página {page_match.group(1)}" if page_match else img.stem
        rel = f"figures/{slug}/{img.name}"
        items.append(
            f'        <figure class="paper-figure">\n'
            f"          <img src=\"{rel}\" alt=\"{html.escape(caption)}\" loading=\"lazy\">\n"
            f"          <figcaption>{html.escape(caption)}</figcaption>\n"
            f"        </figure>"
        )

    return (
        "<!-- FIGURES_START -->\n"
        '<section class="figures-section">\n'
        "  <h2>Figuras del artículo</h2>\n"
        '  <div class="figures-gallery">\n'
        + "\n".join(items) + "\n"
        "  </div>\n"
        "</section>\n"
        "<!-- FIGURES_END -->"
    )


def render_page(title: str, source_name: str, body: str, figures_html: str = "", pdf_name: str = "") -> str:
    pdf_link = (
        f'<a class="pdf-link" href="../pappers_pdf/{html.escape(pdf_name)}" target="_blank" rel="noopener">Ver PDF original ↗</a>'
        if pdf_name else ""
    )
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
      .figures-section {{
        margin: 2.5rem 0 0;
        padding-top: 2rem;
        border-top: 3px double var(--rule);
      }}
      .figures-gallery {{
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
        gap: 1.5rem;
        margin-top: 1.2rem;
      }}
      .paper-figure {{
        margin: 0;
        border: 1px solid var(--rule);
        background: #fdfaf4;
        border-radius: 2px;
        overflow: hidden;
      }}
      .paper-figure img {{
        width: 100%;
        height: auto;
        display: block;
      }}
      .paper-figure figcaption {{
        padding: 0.5rem 0.75rem;
        font-size: 0.82rem;
        color: var(--muted);
        font-family: Arial, sans-serif;
        text-align: center;
        border-top: 1px solid var(--rule);
      }}
      .pdf-link {{
        display: inline-block;
        margin-top: 0.75rem;
        padding: 0.35rem 0.9rem;
        background: var(--accent);
        color: #fff;
        font: 700 0.82rem Arial, sans-serif;
        letter-spacing: 0.06em;
        text-decoration: none;
        text-transform: uppercase;
        border-radius: 2px;
      }}
      .pdf-link:hover {{ background: var(--accent-2); }}
      @media (max-width: 640px) {{
        main {{ width: min(100% - 18px, 980px); margin: 9px auto; }}
        .figures-gallery {{ grid-template-columns: 1fr; }}
      }}
    </style>
  </head>
  <body>
    <main>
      <nav><a href="../index.html">Volver al mapa</a></nav>
      <header>
        <h1>{html.escape(title)}</h1>
        <p class="source">Generado desde {html.escape(source_name)}</p>
        {pdf_link}
      </header>
      <article>
        {body}
        {figures_html}
      </article>
    </main>
  </body>
</html>
"""


def load_pdf_map() -> dict[str, str]:
    """Return mapping of txt_filename → pdf_filename from pappers_pdf/map.json."""
    if PDF_MAP_FILE.exists():
        try:
            return json.loads(PDF_MAP_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)

    pdf_map = load_pdf_map()  # txt_name → pdf_name
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
        slug = slugify(source.stem)
        output_name = f"{slug}.html"
        body = text_to_html(text)
        figures_html = load_figures_gallery(slug)
        pdf_name = pdf_map.get(source.name, "")
        (OUTPUT_DIR / output_name).write_text(
            render_page(title, source.name, body, figures_html, pdf_name),
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
