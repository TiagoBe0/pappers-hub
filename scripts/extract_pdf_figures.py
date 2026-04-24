#!/usr/bin/env python3
"""Extract figures from a PDF article and embed them in the HTML summary.

Usage:
    python scripts/extract_pdf_figures.py <archivo.pdf> [resumen.html]

If the HTML path is omitted the script tries to find a matching file in
pappers_html/ by comparing slugified stems. Figures are saved under
pappers_html/figures/<html-slug>/ so that generate_paper_html.py can
include them automatically when it re-renders the page.
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

MIN_SIZE = 100  # pixels — skip decorative icons / rule images
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "resumen"


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def extract_figures(pdf_path: Path, output_dir: Path) -> list[dict]:
    """Return list of dicts with keys: path, page, width, height."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("Error: PyMuPDF no está instalado.")
        print("  Instálalo con:  pip install PyMuPDF")
        sys.exit(1)

    doc = fitz.open(str(pdf_path))
    output_dir.mkdir(parents=True, exist_ok=True)

    seen: set[int] = set()
    figures: list[dict] = []
    count = 0

    for page_num, page in enumerate(doc, start=1):
        for img_info in page.get_images(full=True):
            xref = img_info[0]
            if xref in seen:
                continue
            seen.add(xref)

            img = doc.extract_image(xref)
            w, h = img["width"], img["height"]
            if w < MIN_SIZE or h < MIN_SIZE:
                continue

            count += 1
            ext = img["ext"]
            filename = f"figura_{count:03d}_p{page_num}.{ext}"
            dest = output_dir / filename
            dest.write_bytes(img["image"])
            figures.append({"path": dest, "page": page_num, "width": w, "height": h})

    doc.close()
    return figures


# ---------------------------------------------------------------------------
# HTML gallery
# ---------------------------------------------------------------------------

def build_gallery_html(figures: list[dict], slug: str) -> str:
    """Return the figures section HTML block (bounded by FIGURES_START/END markers)."""
    items: list[str] = []
    for fig in figures:
        rel = f"figures/{slug}/{fig['path'].name}"
        page = fig["page"]
        caption = f"Página {page} — {fig['width']}×{fig['height']} px"
        items.append(
            f'        <figure class="paper-figure">\n'
            f'          <img src="{rel}" alt="Figura página {page}" loading="lazy">\n'
            f'          <figcaption>{caption}</figcaption>\n'
            f'        </figure>'
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


def inject_into_html(html_path: Path, gallery_html: str) -> None:
    """Insert (or replace) the figures gallery inside <article> of the HTML file."""
    content = html_path.read_text(encoding="utf-8")

    # Remove any previously injected block
    content = re.sub(
        r"\n?<!-- FIGURES_START -->.*?<!-- FIGURES_END -->",
        "",
        content,
        flags=re.DOTALL,
    )

    # Place before </article>; fall back to before </body>
    marker = "</article>" if "</article>" in content else "</body>"
    content = content.replace(marker, gallery_html + "\n      " + marker, 1)

    html_path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# HTML discovery
# ---------------------------------------------------------------------------

def find_html_for_pdf(pdf_path: Path, html_dir: Path) -> Path | None:
    slug = slugify(pdf_path.stem)

    # Exact slug match
    candidate = html_dir / f"{slug}.html"
    if candidate.exists():
        return candidate

    # Original stem (no transform)
    candidate = html_dir / f"{pdf_path.stem}.html"
    if candidate.exists():
        return candidate

    # Substring match
    for f in sorted(html_dir.glob("*.html")):
        if slug in slugify(f.stem) or slugify(f.stem) in slug:
            return f

    return None


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"Error: no se encontró '{pdf_path}'")
        sys.exit(1)

    base_dir = Path(__file__).resolve().parents[1]
    html_dir = base_dir / "pappers_html"

    if len(sys.argv) >= 3:
        html_path = Path(sys.argv[2])
    else:
        html_path = find_html_for_pdf(pdf_path, html_dir)

    if html_path is None:
        print(f"No se encontró un HTML para '{pdf_path.name}'.")
        print("Especifica el resumen como segundo argumento, por ejemplo:")
        print(f"  python scripts/extract_pdf_figures.py {pdf_path} pappers_html/mi-resumen.html")
        sys.exit(1)

    if not html_path.exists():
        print(f"Error: el archivo HTML '{html_path}' no existe.")
        sys.exit(1)

    # Figures directory is keyed by the HTML stem so generate_paper_html.py
    # can find them automatically when it re-renders the page.
    slug = slugify(html_path.stem)
    figures_dir = html_dir / "figures" / slug

    print(f"PDF   : {pdf_path.name}")
    print(f"HTML  : {html_path.name}")
    print(f"Figuras → figures/{slug}/")
    print()

    figures = extract_figures(pdf_path, figures_dir)

    if not figures:
        print("No se encontraron figuras (o todas son menores de 100×100 px).")
        sys.exit(0)

    for fig in figures:
        print(f"  [p{fig['page']:>3}] {fig['path'].name}  ({fig['width']}×{fig['height']})")

    print()
    gallery = build_gallery_html(figures, slug)
    inject_into_html(html_path, gallery)
    print(f"Galería de {len(figures)} figura(s) vinculada en '{html_path.name}'.")
    print("Listo. Abre el HTML en tu navegador para verificar.")


if __name__ == "__main__":
    main()
