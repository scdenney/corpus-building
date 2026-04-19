#!/bin/bash
# ============================================================================
# alice_deploy.sh — sync pipeline code + data to ALICE HPC and produce an
#                   ALICE-path manifest.
#
# What this does:
#   1. rsync your pipeline code to <remote-base>/pipeline
#   2. rsync your source PDFs to <remote-base>/data
#   3. Rewrite the local manifest.csv → manifest_alice.csv, translating
#      local pdf_path values to their equivalent /zfsstore paths.
#
# What this does NOT do:
#   - Submit a SLURM job. Use `ssh <host> "cd <remote-base>/pipeline && sbatch run_ocr.slurm"`.
#   - Create the venv or download model weights. Do those on the login node
#     once (see the `alice-vllm-deploy` skill).
#
# Usage:
#   alice_deploy.sh \\
#       --host alice3 \\
#       --code-src ./pipeline \\
#       --data-src ./pdfs \\
#       --manifest ./pipeline/manifest.csv \\
#       --remote-base /zfsstore/user/<netid>/<project>
#
# Reference: the `alice-vllm-deploy` skill covers SSH discipline,
# ControlMaster multiplexing, and offline-mode env vars.
# ============================================================================

set -euo pipefail

HOST=""
CODE_SRC=""
DATA_SRC=""
MANIFEST=""
REMOTE_BASE=""
DRY_RUN=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --host)        HOST="$2"; shift 2 ;;
        --code-src)    CODE_SRC="$2"; shift 2 ;;
        --data-src)    DATA_SRC="$2"; shift 2 ;;
        --manifest)    MANIFEST="$2"; shift 2 ;;
        --remote-base) REMOTE_BASE="$2"; shift 2 ;;
        --dry-run)     DRY_RUN="--dry-run"; shift ;;
        -h|--help)
            sed -n '3,24p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 2
            ;;
    esac
done

for var in HOST CODE_SRC DATA_SRC MANIFEST REMOTE_BASE; do
    if [ -z "${!var}" ]; then
        echo "Missing required --${var,,} (set via ${var})" >&2
        exit 2
    fi
done

if [ ! -d "${CODE_SRC}" ]; then
    echo "Code source not a directory: ${CODE_SRC}" >&2
    exit 2
fi
if [ ! -d "${DATA_SRC}" ]; then
    echo "Data source not a directory: ${DATA_SRC}" >&2
    exit 2
fi
if [ ! -f "${MANIFEST}" ]; then
    echo "Manifest not found: ${MANIFEST}" >&2
    exit 2
fi

REMOTE_CODE="${REMOTE_BASE}/pipeline"
REMOTE_DATA="${REMOTE_BASE}/data"

echo "=============================================="
echo "alice_deploy.sh"
echo "=============================================="
echo "Host:        ${HOST}"
echo "Code:        ${CODE_SRC}  →  ${HOST}:${REMOTE_CODE}"
echo "Data:        ${DATA_SRC}  →  ${HOST}:${REMOTE_DATA}"
echo "Manifest:    ${MANIFEST}"
echo "Remote base: ${REMOTE_BASE}"
if [ -n "${DRY_RUN}" ]; then
    echo "Mode:        DRY RUN"
fi
echo "=============================================="

# ---- Ensure remote directories exist -------------------------------------
if [ -z "${DRY_RUN}" ]; then
    ssh "${HOST}" "mkdir -p '${REMOTE_CODE}' '${REMOTE_DATA}'"
fi

# ---- Sync code -----------------------------------------------------------
echo ""
echo "--- Syncing code ---"
rsync -avz ${DRY_RUN} \
    --exclude='__pycache__' \
    --exclude='.venv*' \
    --exclude='.pytest_cache' \
    --exclude='.mypy_cache' \
    --exclude='logs/' \
    --exclude='ocr_output/' \
    --exclude='.DS_Store' \
    "${CODE_SRC}/" "${HOST}:${REMOTE_CODE}/"

# ---- Sync data (PDFs only) ------------------------------------------------
echo ""
echo "--- Syncing data (PDFs) ---"
rsync -avz ${DRY_RUN} \
    --include='*/' \
    --include='*.pdf' \
    --exclude='*' \
    --exclude='.DS_Store' \
    "${DATA_SRC}/" "${HOST}:${REMOTE_DATA}/"

# ---- Rewrite manifest for ALICE paths ------------------------------------
echo ""
echo "--- Rewriting manifest → manifest_alice.csv ---"

# Resolve the local DATA_SRC to an absolute path so we can do a prefix swap.
DATA_SRC_ABS="$(cd "${DATA_SRC}" && pwd)"
MANIFEST_ALICE="$(dirname "${MANIFEST}")/manifest_alice.csv"

python3 - "${MANIFEST}" "${MANIFEST_ALICE}" "${DATA_SRC_ABS}" "${REMOTE_DATA}" <<'PY'
import csv
import sys

src_path, dst_path, local_prefix, remote_prefix = sys.argv[1:5]
local_prefix = local_prefix.rstrip("/")
remote_prefix = remote_prefix.rstrip("/")
rewritten = 0

with open(src_path, encoding="utf-8", newline="") as fin, \
     open(dst_path, "w", encoding="utf-8", newline="") as fout:
    # Preserve leading '#'-comment lines verbatim
    lines = []
    while True:
        pos = fin.tell()
        line = fin.readline()
        if line.startswith("#"):
            fout.write(line)
            continue
        fin.seek(pos)
        break

    reader = csv.DictReader(fin)
    fieldnames = reader.fieldnames
    if fieldnames is None:
        print("ERROR: manifest has no header", file=sys.stderr)
        sys.exit(1)
    if "pdf_path" not in fieldnames:
        print("ERROR: manifest is missing 'pdf_path' column", file=sys.stderr)
        sys.exit(1)

    writer = csv.DictWriter(fout, fieldnames=fieldnames)
    writer.writeheader()
    for row in reader:
        pdf_path = row["pdf_path"]
        if pdf_path.startswith(local_prefix):
            row["pdf_path"] = remote_prefix + pdf_path[len(local_prefix):]
            rewritten += 1
        writer.writerow(row)

print(f"  Rewrote {rewritten} pdf_path values")
print(f"  Output: {dst_path}")
PY

echo ""
echo "=============================================="
echo "Deploy complete."
echo "Next: ssh ${HOST} \"cd ${REMOTE_CODE} && sbatch run_ocr.slurm\""
echo "=============================================="
