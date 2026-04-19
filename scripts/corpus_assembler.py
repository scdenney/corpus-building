#!/usr/bin/env python3
"""
corpus_assembler.py — assemble final corpus JSON + CSV from per-PDF OCR output.

Stage 3 of the corpus-building pipeline. Reads per-PDF result files (produced
by the VLM client or the API runner), joins them with manifest metadata, and
writes analysis-ready outputs:

    <output>/corpus_<group>.json   # all pages, full metadata, nested
    <output>/corpus_<group>.csv    # text-bearing pages only, tidy columns

With --group-by language, this produces corpus_korean.{json,csv},
corpus_english.{json,csv}, etc. Without --group-by, a single
corpus.{json,csv} pair.

Input layout expected (per the other pipeline scripts):

    <ocr-dir>/
        <pdf_id>/
            results_raw.json           # from the OCR client
            results_cleaned.json       # optional: from post_ocr_cleanup
            images/...                 # optional: native-extracted images

Each results_*.json has schema:
    { "pages": [ { "page": N, "text": "...", "has_text": bool, ... }, ... ] }

Usage:
    corpus_assembler.py --ocr-dir ocr_output --manifest manifest.csv --output corpus/
    corpus_assembler.py --ocr-dir ocr_output --manifest manifest.csv --output corpus/ \\
        --group-by language --parse-tags

Reference skills: corpus-from-pdfs, corpus-metadata-design.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable

# ---------------------------------------------------------------------------
# Tag parsing (for Pattern B prompts — see templates/prompts.py.template)
# ---------------------------------------------------------------------------

NO_TEXT_SENTINEL = "[NO_TEXT]"
DEFAULT_TAGS = ("DIALOGUE", "NARRATION", "SFX", "TEXT")


def build_tag_regex(tags: Iterable[str]) -> re.Pattern:
    joined = "|".join(re.escape(t) for t in tags)
    return re.compile(rf"^\[({joined})\]\s*(.*)")


def parse_tagged_text(text: str, tags: Iterable[str]) -> dict:
    """Split tagged VLM output into per-tag columns + a combined 'text'.

    Returns keys: one per tag (lowercase), 'text' (combined), 'text_tagged'
    (raw input preserved), plus 'other' for untagged lines.
    """
    tags = tuple(tags)
    buckets: dict[str, list[str]] = {t: [] for t in tags}
    other: list[str] = []
    result_raw = text.strip() if text else ""

    if not text or result_raw == NO_TEXT_SENTINEL:
        out = {t.lower(): "" for t in tags}
        out.update({"other": "", "text": "", "text_tagged": result_raw})
        return out

    tag_re = build_tag_regex(tags)
    current_tag: str | None = None
    current_lines: list[str] = []

    def flush():
        if current_tag and current_lines:
            buckets[current_tag].append(" ".join(current_lines))

    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        m = tag_re.match(stripped)
        if m:
            flush()
            current_tag = m.group(1)
            rest = m.group(2).strip()
            current_lines = [rest] if rest else []
        elif current_tag:
            current_lines.append(stripped)
        elif stripped != NO_TEXT_SENTINEL:
            other.append(stripped)
    flush()

    out = {t.lower(): " ".join(buckets[t]) for t in tags}
    out["other"] = " ".join(other)
    parts = [" ".join(buckets[t]) for t in tags] + [" ".join(other)]
    out["text"] = " ".join(p for p in parts if p).strip()
    out["text_tagged"] = result_raw
    return out


# ---------------------------------------------------------------------------
# Manifest + results loading
# ---------------------------------------------------------------------------

def load_manifest(path: Path) -> dict[str, dict]:
    manifest: dict[str, dict] = {}
    with open(path, encoding="utf-8", newline="") as f:
        rows = [ln for ln in f if not ln.startswith("#")]
    reader = csv.DictReader(rows)
    for row in reader:
        if not row.get("pdf_id"):
            continue
        manifest[row["pdf_id"]] = row
    return manifest


def find_results(ocr_dir: Path, pdf_id: str) -> Path | None:
    d = ocr_dir / pdf_id
    for name in ("results_cleaned.json", "results_raw.json"):
        p = d / name
        if p.exists():
            return p
    return None


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def assemble(
    ocr_dir: Path,
    manifest_path: Path,
    output_dir: Path,
    group_by: str | None,
    parse_tags: bool,
    tags: tuple[str, ...],
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(manifest_path)

    # Collect rows keyed by group value ("" when not grouping)
    groups: dict[str, list[dict]] = {}
    stats = {"pdfs": 0, "pdfs_missing": 0, "pages": 0, "text_pages": 0}

    manifest_skip_cols = {"pdf_path", "content_start", "content_end", "total_pages"}

    for pdf_id, meta in sorted(manifest.items()):
        results_path = find_results(ocr_dir, pdf_id)
        if results_path is None:
            print(f"  WARN: no results for {pdf_id}, skipping", file=sys.stderr)
            stats["pdfs_missing"] += 1
            continue

        with open(results_path, encoding="utf-8") as f:
            data = json.load(f)

        stats["pdfs"] += 1

        base_meta = {k: v for k, v in meta.items() if k not in manifest_skip_cols}

        for page_data in data.get("pages", []):
            raw_text = page_data.get("text", "")
            has_text_flag = page_data.get("has_text", True)

            entry = dict(base_meta)
            entry["page"] = page_data.get("page")

            if parse_tags:
                parsed = parse_tagged_text(raw_text, tags)
                entry.update(parsed)
                if not parsed["text"].strip():
                    has_text_flag = False
            else:
                text_clean = "" if raw_text.strip() == NO_TEXT_SENTINEL else raw_text.strip()
                entry["text"] = text_clean
                entry["text_tagged"] = raw_text.strip()
                if not text_clean:
                    has_text_flag = False

            entry["has_text"] = has_text_flag
            stats["pages"] += 1
            if has_text_flag:
                stats["text_pages"] += 1

            group_val = meta.get(group_by, "") if group_by else ""
            groups.setdefault(group_val, []).append(entry)

    # Write outputs per group
    for group_val, rows in groups.items():
        suffix = f"_{group_val}" if group_val else ""
        rows.sort(key=_sort_key)

        text_rows = [r for r in rows if r.get("has_text")]

        # --- JSON (all pages, all metadata) ---
        json_path = output_dir / f"corpus{suffix}.json"
        payload = {
            "metadata": {
                "created": datetime.now().isoformat(timespec="seconds"),
                "group_by": group_by,
                "group_value": group_val,
                "total_pages": len(rows),
                "text_pages": len(text_rows),
                "no_text_pages": len(rows) - len(text_rows),
                "parse_tags": parse_tags,
                "tags": list(tags) if parse_tags else [],
            },
            "pages": rows,
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        # --- CSV (text-bearing pages only, tidy columns) ---
        csv_path = output_dir / f"corpus{suffix}.csv"
        fieldnames = _csv_fieldnames(text_rows, parse_tags, tags)
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for r in text_rows:
                writer.writerow(r)

        label = group_val or "corpus"
        print(f"  {label}: {len(rows)} pages total, {len(text_rows)} with text")
        print(f"    JSON: {json_path}")
        print(f"    CSV : {csv_path} ({len(text_rows)} rows)")

    print()
    print(f"  PDFs processed: {stats['pdfs']} (missing: {stats['pdfs_missing']})")
    print(f"  Total pages:    {stats['pages']}")
    print(f"  Pages w/ text:  {stats['text_pages']}")
    density = stats["text_pages"] / max(stats["pages"], 1)
    print(f"  Text density:   {density:.1%}")

    return stats


def _sort_key(row: dict):
    # Reasonable default: (series, chapter, page) if present, otherwise (pdf_id, page).
    if "series" in row and "chapter" in row:
        try:
            chapter = int(row["chapter"])
        except (ValueError, TypeError):
            chapter = 0
        return (row.get("series", ""), chapter, int(row.get("page", 0) or 0))
    return (row.get("pdf_id", ""), int(row.get("page", 0) or 0))


def _csv_fieldnames(rows: list[dict], parse_tags: bool, tags: tuple[str, ...]) -> list[str]:
    # Core metadata first, then text columns. Adjust to taste.
    preferred = ["pdf_id", "series", "language", "chapter", "page"]
    fields = [p for p in preferred if rows and p in rows[0]]

    if parse_tags:
        fields.append("text")
        fields.extend(t.lower() for t in tags)
        fields.append("text_tagged")
    else:
        fields.append("text")

    # Include any other manifest columns present on the rows
    known = set(fields)
    extra_skip = {"has_text", "other"}
    for r in rows[:1]:
        for k in r:
            if k not in known and k not in extra_skip:
                fields.append(k)
                known.add(k)
    return fields


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Assemble corpus JSON + CSV from per-PDF OCR results.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--ocr-dir", type=Path, required=True, help="Directory of per-PDF results subdirs.")
    ap.add_argument("--manifest", type=Path, required=True, help="Manifest CSV produced by inventory_builder.py.")
    ap.add_argument("--output", type=Path, required=True, help="Output directory for corpus files.")
    ap.add_argument("--group-by", default=None, help="Manifest column to split outputs by (e.g. 'language'). Omit for a single corpus file.")
    ap.add_argument("--parse-tags", action="store_true", help="Parse [TAG] lines into separate columns (dialogue, narration, sfx, other).")
    ap.add_argument("--tags", default=",".join(DEFAULT_TAGS), help=f"Comma-separated tag names. Default: {','.join(DEFAULT_TAGS)}")
    args = ap.parse_args(argv)

    if not args.ocr_dir.is_dir():
        print(f"--ocr-dir not a directory: {args.ocr_dir}", file=sys.stderr)
        return 2
    if not args.manifest.is_file():
        print(f"--manifest not found: {args.manifest}", file=sys.stderr)
        return 2

    tags = tuple(t.strip() for t in args.tags.split(",") if t.strip())
    print("Assembling corpus...\n")
    assemble(
        ocr_dir=args.ocr_dir,
        manifest_path=args.manifest,
        output_dir=args.output,
        group_by=args.group_by,
        parse_tags=args.parse_tags,
        tags=tags,
    )
    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
