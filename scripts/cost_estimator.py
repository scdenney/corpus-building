#!/usr/bin/env python3
"""
cost_estimator.py — ballpark cost for API-based OCR.

Uses the per-page pricing summarized in the `api-ocr-runner` skill.
These are ballparks, not guarantees. Always measure actual cost on a
10-page sample before committing to a full run.

Usage:
    cost_estimator.py --pages 450
    cost_estimator.py --pages 1200 --provider gemini
    cost_estimator.py --pages 800 --doctype comic --provider claude
    cost_estimator.py --pages 2000 --compare

Pricing is stated per page (image input + text output, typical densities).
Revisit PRICING when provider pricing changes.
"""

from __future__ import annotations

import argparse
import sys

# ---------------------------------------------------------------------------
# Per-page ballpark costs (USD). Reference: api-ocr-runner skill, Section 2.
# Update when provider pricing shifts materially.
# ---------------------------------------------------------------------------

PRICING = {
    "claude":  {"low": 0.010, "high": 0.020, "model": "claude-sonnet-4-6"},
    "gpt":     {"low": 0.010, "high": 0.020, "model": "gpt-4.1"},
    "gemini":  {"low": 0.002, "high": 0.005, "model": "gemini-2.5-flash"},
}

# ---------------------------------------------------------------------------
# Output-token ballparks by document type. Informational only — the per-page
# rate above already bakes in typical densities. Shown so users can judge
# whether their corpus fits the "typical" profile.
# ---------------------------------------------------------------------------

TOKEN_PROFILES = {
    "book":   {"output_tokens": (1000, 2000), "note": "dense scanned textbook / article page"},
    "comic":  {"output_tokens":   (50,  200), "note": "comic / webtoon page (sparse text)"},
    "sparse": {"output_tokens":  (100,  500), "note": "forms, covers, mixed-sparsity pages"},
}

IMAGE_INPUT_TOKENS_TYPICAL = "1,000–4,000 (varies by provider and resolution)"


def estimate(pages: int, provider: str) -> dict:
    if provider not in PRICING:
        raise ValueError(f"Unknown provider '{provider}'. Known: {list(PRICING)}")
    p = PRICING[provider]
    return {
        "provider": provider,
        "model": p["model"],
        "pages": pages,
        "low_usd": pages * p["low"],
        "high_usd": pages * p["high"],
    }


def format_row(est: dict) -> str:
    return (
        f"  {est['provider']:8s} ({est['model']:20s}): "
        f"${est['low_usd']:8.2f} – ${est['high_usd']:8.2f}"
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Ballpark API OCR cost estimator.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--pages", type=int, required=True, help="Total pages to OCR.")
    ap.add_argument(
        "--provider",
        choices=list(PRICING),
        default="claude",
        help="API provider (default: claude).",
    )
    ap.add_argument(
        "--doctype",
        choices=list(TOKEN_PROFILES),
        default="book",
        help="Document-type profile for informational token ballpark (default: book).",
    )
    ap.add_argument(
        "--compare",
        action="store_true",
        help="Show the estimate across all providers side by side.",
    )
    args = ap.parse_args(argv)

    if args.pages <= 0:
        print("--pages must be positive", file=sys.stderr)
        return 2

    profile = TOKEN_PROFILES[args.doctype]
    tok_low, tok_high = profile["output_tokens"]

    print(f"Pages:      {args.pages:,}")
    print(f"Doctype:    {args.doctype} ({profile['note']})")
    print(f"Per-page output tokens (ballpark): {tok_low}–{tok_high}")
    print(f"Image input tokens (per provider):  {IMAGE_INPUT_TOKENS_TYPICAL}")
    print()

    if args.compare:
        print("Estimated total cost (USD):")
        for provider in PRICING:
            print(format_row(estimate(args.pages, provider)))
    else:
        est = estimate(args.pages, args.provider)
        print("Estimated total cost (USD):")
        print(format_row(est))

    print()
    print(
        "NOTE: Ballpark only. Run a 10-page sample to measure actual "
        "per-page cost before a full run. See the `api-ocr-runner` skill."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
