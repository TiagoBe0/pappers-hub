#!/usr/bin/env python3
"""Match PDF files in pappers_pdf/ to TXT summaries in pappers_resumenes/.

Writes pappers_pdf/map.json  →  { "resumen_foo.txt": "foo.pdf", ... }

Usage:
    python scripts/match_pdfs.py [--dry-run]

Options:
    --dry-run   Print matches without writing map.json
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "pappers_pdf"
TXT_DIR = ROOT / "pappers_resumenes"
MAP_FILE = PDF_DIR / "map.json"

MATCH_THRESHOLD = 0.45  # minimum SequenceMatcher ratio to accept a fuzzy match


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "resumen"


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def find_best_match(pdf_slug: str, txt_slugs: list[tuple[str, Path]]) -> Path | None:
    """Return the TXT path whose slug best matches pdf_slug, or None."""
    best_path: Path | None = None
    best_score = 0.0

    for txt_slug, txt_path in txt_slugs:
        # Exact match
        if pdf_slug == txt_slug:
            return txt_path

        # Substring containment
        if pdf_slug in txt_slug or txt_slug in pdf_slug:
            score = max(len(pdf_slug), len(txt_slug)) / max(len(pdf_slug), len(txt_slug), 1)
            # prefer longer overlap
            score = 0.90 - 0.01 * abs(len(pdf_slug) - len(txt_slug))
            if score > best_score:
                best_score = score
                best_path = txt_path

        # Fuzzy fallback
        score = similarity(pdf_slug, txt_slug)
        if score > best_score and score >= MATCH_THRESHOLD:
            best_score = score
            best_path = txt_path

    return best_path


def load_existing_map() -> dict[str, str]:
    if MAP_FILE.exists():
        try:
            return json.loads(MAP_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def main(dry_run: bool = False) -> None:
    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    txts = [
        p for p in sorted(TXT_DIR.iterdir())
        if p.is_file() and p.suffix.lower() == ".txt" and p.stat().st_size > 0
    ]

    if not pdfs:
        print("No se encontraron PDFs en pappers_pdf/.")
        print("Coloca los archivos PDF allí y vuelve a ejecutar este script.")
        if not dry_run:
            existing = load_existing_map()
            MAP_FILE.write_text(
                json.dumps(existing, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(f"map.json conservado con {len(existing)} entrada(s) existente(s).")
        return

    txt_slugs = [(slugify(p.stem), p) for p in txts]

    existing_map = load_existing_map()
    # existing_map: txt_name → pdf_name  (preserve manual overrides)
    locked: set[str] = set(existing_map.values())  # PDFs already mapped manually

    new_map: dict[str, str] = dict(existing_map)
    matched: list[tuple[Path, Path]] = []
    unmatched: list[Path] = []

    for pdf in pdfs:
        if pdf.name in locked:
            continue  # already manually assigned
        pdf_slug = slugify(pdf.stem)
        best = find_best_match(pdf_slug, txt_slugs)
        if best is None:
            unmatched.append(pdf)
        else:
            new_map[best.name] = pdf.name
            matched.append((pdf, best))

    print(f"PDFs encontrados  : {len(pdfs)}")
    print(f"Resúmenes TXT     : {len(txts)}")
    print()

    if matched:
        print("Matches encontrados:")
        for pdf, txt in matched:
            print(f"  {pdf.name}  →  {txt.name}")
    else:
        print("Sin matches nuevos.")

    if unmatched:
        print()
        print("PDFs sin match (añade manualmente a map.json):")
        for pdf in unmatched:
            print(f"  {pdf.name}")

    if not dry_run:
        MAP_FILE.write_text(
            json.dumps(new_map, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print()
        print(f"map.json actualizado con {len(new_map)} entrada(s) → {MAP_FILE.relative_to(ROOT)}")
    else:
        print()
        print("(modo --dry-run: map.json no fue modificado)")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)
