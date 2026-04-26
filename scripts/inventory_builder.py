#!/usr/bin/env python3
"""
inventory_builder.py — walk a directory of source files and build a manifest CSV.

This is the Stage 0 of a corpus-building pipeline. Given a root directory
containing PDFs or other source files (flat or nested), it produces a
manifest.csv with:

    pdf_id, source_format, filename, source_path, pdf_path,
    total_pages, content_start, content_end, [language], [parent_folder]

Design choices:

- Filenames are NFC-normalized before use (macOS HFS+/APFS decomposes Korean,
  Japanese, and accented characters to NFD; regex matching against those
  filenames silently fails without normalization).
- Page counts come from PyMuPDF for PDFs when available; otherwise left blank.
- Non-PDF sources are included with source_format/source_path so the
  source-file-extraction skill can route them to the right extractor.
- Content range detection (content_start / content_end) is optional and
  opt-in via --detect-content. Two built-in detectors: Naver webtoon UI on
  page 0 (selectable text with known Korean nav strings), and "tail
  selectable text" (comment / footer pages at the end of saved-from-web
  PDFs). Both are Korean-webtoon-specific; extend for your corpus.
- Series / chapter parsing is NOT in the generic tool. That's corpus-specific
  glue — see the customization block near the bottom of this file, or adapt
  /Thesis/pipeline/inventory.py for a worked multi-series example.

Usage:
    inventory_builder.py --source-dir ./sources --output manifest.csv
    inventory_builder.py --pdf-dir ./pdfs --output manifest.csv
    inventory_builder.py --pdf-dir ./pdfs --output manifest.csv \\
        --language-from-folder --detect-content
"""

from __future__ import annotations

import argparse
import csv
import sys
import unicodedata
from pathlib import Path

try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False


SUPPORTED_EXTENSIONS = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".doc": "doc",
    ".txt": "text",
    ".md": "text",
    ".rtf": "rtf",
    ".csv": "csv",
    ".html": "html",
    ".htm": "html",
    ".epub": "epub",
    ".xml": "xml",
    ".tei": "tei",
    ".json": "json",
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
    ".tif": "image",
    ".tiff": "image",
}


# ---------------------------------------------------------------------------
# Content-range detection (Korean webtoon-specific by default; extend below)
# ---------------------------------------------------------------------------

NAVER_UI_STRINGS = {
    "홈", "웹툰", "웹소설", "시리즈", "컷츠", "베스트도전", "도전만화",
    "마이페이지", "요일전체", "로그인", "관심", "이전화", "다음화", "목록",
}


def detect_content_range(pdf_path: Path, tail_window: int = 5) -> tuple[int, int, int]:
    """Return (content_start, content_end, total_pages) — both endpoints inclusive.

    content_start: first content page (0-indexed). Skips page 0 if it contains
        Naver UI strings as selectable text.
    content_end: last content page (0-indexed, INCLUSIVE). Skips tail pages
        containing substantial selectable text (comments, metadata).
    """
    if not HAS_FITZ:
        return (0, -1, -1)

    doc = fitz.open(str(pdf_path))
    total = len(doc)

    content_start = 0
    if total > 1:
        page0_text = doc[0].get_text().strip()
        if page0_text and (set(page0_text.split()) & NAVER_UI_STRINGS):
            content_start = 1

    content_end = total - 1
    for i in range(total - 1, max(content_start, total - tail_window) - 1, -1):
        page_text = doc[i].get_text().strip()
        if page_text and len(page_text) > 50:
            content_end = i - 1
        else:
            break

    doc.close()
    return (content_start, content_end, total)


def total_pages(pdf_path: Path) -> int | None:
    if not HAS_FITZ:
        return None
    try:
        doc = fitz.open(str(pdf_path))
        n = len(doc)
        doc.close()
        return n
    except Exception as e:
        print(f"  WARN: could not open {pdf_path}: {e}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def make_pdf_id(source_path: Path, root: Path) -> str:
    """Generate a stable legacy pdf_id/doc id from the path relative to root."""
    rel = source_path.relative_to(root)
    stem = unicodedata.normalize("NFC", rel.stem)
    parts = [unicodedata.normalize("NFC", p) for p in rel.parts[:-1]]
    parts.append(stem)
    safe = "_".join(parts)
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in safe).strip("_").lower()


def classify_source(source_path: Path) -> str:
    return SUPPORTED_EXTENSIONS.get(source_path.suffix.lower(), "unknown")


def iter_sources(source_dir: Path, pdf_only: bool) -> list[Path]:
    if pdf_only:
        return sorted(source_dir.rglob("*.pdf"))
    return sorted(
        p for p in source_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def build_rows(
    source_dir: Path,
    language_from_folder: bool,
    detect_content: bool,
    pdf_only: bool,
) -> list[dict]:
    rows = []
    sources = iter_sources(source_dir, pdf_only)
    label = "PDFs" if pdf_only else "supported source files"
    print(f"Found {len(sources)} {label} under {source_dir}")

    for source_path in sources:
        filename = unicodedata.normalize("NFC", source_path.name)
        source_fmt = classify_source(source_path)
        is_pdf = source_fmt == "pdf"
        row = {
            "pdf_id": make_pdf_id(source_path, source_dir),
            "source_format": source_fmt,
            "filename": filename,
            "source_path": str(source_path.resolve()),
            "pdf_path": str(source_path.resolve()) if is_pdf else "",
            "total_pages": "",
            "content_start": "",
            "content_end": "",
        }

        if language_from_folder:
            row["language"] = unicodedata.normalize("NFC", source_path.parent.name).lower()

        row["parent_folder"] = unicodedata.normalize("NFC", source_path.parent.name)

        if detect_content and is_pdf:
            cs, ce, tot = detect_content_range(source_path)
            if tot >= 0:
                row["total_pages"] = tot
                row["content_start"] = cs
                row["content_end"] = ce
        elif is_pdf:
            n = total_pages(source_path)
            if n is not None:
                row["total_pages"] = n
                row["content_start"] = 0
                row["content_end"] = n - 1

        rows.append(row)

    return rows


def write_manifest(rows: list[dict], output: Path, include_language: bool) -> None:
    fieldnames = [
        "pdf_id", "source_format", "filename", "source_path", "pdf_path",
        "parent_folder",
        "total_pages", "content_start", "content_end",
    ]
    if include_language:
        fieldnames.insert(2, "language")

    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8", newline="") as f:
        f.write("# Generated by inventory_builder.py — edit at your own risk.\n")
        f.write("# See templates/manifest.csv.example for column documentation.\n")
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def print_summary(rows: list[dict]) -> None:
    print()
    print(f"  Total sources:  {len(rows)}")
    formats = {}
    for row in rows:
        fmt = row.get("source_format", "unknown")
        formats[fmt] = formats.get(fmt, 0) + 1
    if formats:
        print("  Formats:        " + ", ".join(f"{k}={v}" for k, v in sorted(formats.items())))
    total = sum(int(r["total_pages"]) for r in rows if r["total_pages"] != "")
    if total:
        print(f"  Total pages:    {total}")
        content = 0
        for r in rows:
            if r["content_start"] != "" and r["content_end"] != "":
                content += int(r["content_end"]) - int(r["content_start"]) + 1
        print(f"  Content pages:  {content}")
    langs = sorted({r.get("language", "") for r in rows if r.get("language")})
    if langs:
        print(f"  Languages:      {', '.join(langs)}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Walk a source directory and build a manifest CSV.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--source-dir", type=Path, help="Root directory of supported source files to scan recursively.")
    ap.add_argument("--pdf-dir", type=Path, help="Backward-compatible PDF-only root directory to scan recursively.")
    ap.add_argument("--output", type=Path, required=True, help="Output manifest CSV path.")
    ap.add_argument(
        "--language-from-folder",
        action="store_true",
        help="Use the source file's parent folder name (lowercased) as the language column.",
    )
    ap.add_argument(
        "--detect-content",
        action="store_true",
        help="Run Naver-UI and tail-text detection to set content_start/content_end (Korean-webtoon-specific defaults; adapt for other corpora).",
    )
    args = ap.parse_args(argv)

    if args.source_dir and args.pdf_dir:
        print("Use either --source-dir or --pdf-dir, not both.", file=sys.stderr)
        return 2
    source_dir = args.source_dir or args.pdf_dir
    pdf_only = args.source_dir is None
    if source_dir is None:
        print("Either --source-dir or --pdf-dir is required.", file=sys.stderr)
        return 2
    if not source_dir.is_dir():
        flag = "--pdf-dir" if pdf_only else "--source-dir"
        print(f"{flag} not a directory: {source_dir}", file=sys.stderr)
        return 2
    if not HAS_FITZ:
        print("WARN: PyMuPDF not installed; PDF total_pages will be blank. `pip install PyMuPDF`.", file=sys.stderr)

    rows = build_rows(
        source_dir=source_dir.resolve(),
        language_from_folder=args.language_from_folder,
        detect_content=args.detect_content,
        pdf_only=pdf_only,
    )
    write_manifest(rows, args.output, include_language=args.language_from_folder)
    print(f"\nManifest: {args.output}")
    print_summary(rows)

    # -----------------------------------------------------------------------
    # Customization points (edit below for corpus-specific extraction):
    #
    # - Series / collection identification: parse source_path parts against a
    #   dict of regex patterns (see /Thesis/pipeline/inventory.py for a
    #   sample case with three series).
    # - Chapter / episode numbers: add a CHAPTER_PATTERNS dict keyed by
    #   (series, language) and run against the NFC-normalized filename.
    # - Additional metadata (year, author, edition): parse from filename,
    #   parent folders, or a sibling metadata file and add to row.
    # -----------------------------------------------------------------------
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
