---
title: "Small corpus via ALICE HPC"
---

# Scenario: Small corpus via ALICE HPC

**Who this is for:** a student who has an ALICE account and wants free compute. Same corpus size as the API scenario — this is about the path, not the scale.

---

## The situation

A grad student studying democratization discourse in late-1970s South Korea has 75 historical newspaper issues (~800 pages, 1960s–1980s). Text mixes Hangul, occasional Hanja, and uneven archival print. Analysis target: Python topic modelling and keyword work grouped by year. ALICE account active, no API budget allocated.

## Wizard answers

| Question | Answer |
|----------|--------|
| How many pages? | 501–1,000 |
| What compute? | ALICE account, ready to use |
| Languages/scripts? | Multiple scripts in one corpus |
| Document type? | Newspapers or multi-column layouts |
| What software? | Python |
| Resource constraints? | No budget; time flexible |

**Route:** ALICE path. `alice-vllm-deploy` covers SLURM, cold-start timing, SSH discipline.

---

## Starter kit

```
Recommended path: ALICE
Corpus scale:    ~800 pages across 75 documents
Est. cost:       free (HPC compute)
Est. time:       ~13 min cold start + ~90 min OCR + ~10 min post-processing
```

**Read first**
1. `corpus-from-pdfs` — end-to-end framing
2. `corpus-metadata-design` — schema for Python output
3. `alice-vllm-deploy` — SLURM, cold-start timing, SSH discipline

**Paste into Claude Code / Codex**
> I have 75 historical Korean newspaper scans (roughly 800 pages). The text mixes Hangul with some Hanja and the print quality is uneven. I have an ALICE account and want to run vLLM on `gpu_lucdh`. My analysis target is Python topic modelling grouped by year. Walk me through the `corpus-from-pdfs` pipeline. Start by helping me fill in the SLURM template and the Korean prompt. Then help me deploy and monitor the job.

**Or launch a fresh session directly**

```bash
claude "I have 75 historical Korean newspaper scans (roughly 800 pages). The text mixes Hangul with some Hanja and the print quality is uneven. I have an ALICE account and want to run vLLM on gpu_lucdh. My analysis target is Python topic modelling grouped by year. Walk me through the corpus-from-pdfs pipeline."
```

**Files to copy**
- `templates/prompts.py.template` → `prompts.py` (Pattern B, Korean newspaper pages with type tags)
- `templates/run_ocr.slurm.template` → `run_ocr.slurm` (project name, `gpu_lucdh`, model, account flag uncommented)

**Commands (pre-filled)**
```bash
python3 scripts/inventory_builder.py --pdf-dir ./newspapers --output manifest.csv
bash scripts/alice_deploy.sh \
    --host alice3 \
    --code-src ./pipeline --data-src ./newspapers \
    --manifest ./manifest.csv \
    --remote-base /zfsstore/user/<netid>/korean-news
ssh alice3 "cd /zfsstore/user/<netid>/korean-news/pipeline && sbatch run_ocr.slurm"
# …wait for the SLURM job to finish (monitor via squeue + log tail)…
python3 scripts/corpus_assembler.py --parse-tags --ocr-dir ocr_output --manifest manifest.csv --output corpus/
```

---

## Walkthrough

> **Note:** the commands below cannot be executed without an ALICE account and PDFs. The outputs shown are what a student would actually see.

### Step 1 — Inventory (local)

Same as the API scenario. Runs on the student's laptop.

```bash
python3 scripts/inventory_builder.py --pdf-dir ./newspapers --output manifest.csv
```

```
Found 75 PDFs under /Users/you/newspapers
Manifest: manifest.csv
  Total PDFs:     75
  Total pages:    798
```

### Step 2 — Fill `prompts.py`

Inside Claude Code, the student opens `prompts.py` (copied from the template) and fills Pattern B for Korean newspaper pages:

```python
PROMPTS = {
    "korean_news": (
        "Extract all text from this newspaper page image. "
        "The text is mostly Korean (Hangul) with some Hanja. "
        "Use the provided type tags for headline, body, caption, table, and note blocks. "
        "Preserve the original wording and reading order as closely as possible. "
        "If the page has no text at all, output only: [NO_TEXT]. "
        "Do not translate or interpret the text."
    ),
}
LANGUAGE_PROMPT_MAP = {"korean_news": "korean_news"}
```

Claude Code reviews this against the `corpus-from-pdfs` guidance on tagged newspaper extraction and confirms it's ready. `VALID_TAGS` is enabled because the student wants clean separation between headlines, body text, captions, and notes.

### Step 3 — Fill `run_ocr.slurm`

From the template, with the student's values substituted:

- `{{PROJECT_NAME}}` → `korean-news`
- `{{PARTITION}}` → `gpu_lucdh`
- `{{WALL_TIME}}` → `04:00:00`
- `{{GPU_SPEC}}` → `gpu:1`
- `#SBATCH --account=gpu_lucdh` line uncommented
- `{{PIPELINE_DIR}}` → `/zfsstore/user/<netid>/korean-news/pipeline`
- `{{MODEL_ID}}` → `Qwen/Qwen3.5-35B-A3B-GPTQ-Int4`
- `{{QUANT_BACKEND}}` → `gptq_marlin`
- Client / diagnostics / assembler script placeholders → filenames from the pipeline

### Step 4 — Deploy

```bash
bash scripts/alice_deploy.sh \
    --host alice3 \
    --code-src ./pipeline --data-src ./newspapers \
    --manifest ./manifest.csv \
    --remote-base /zfsstore/user/<netid>/korean-news
```

Output sketch:

```
==============================================
alice_deploy.sh
==============================================
Host:        alice3
Code:        ./pipeline  →  alice3:/zfsstore/user/<netid>/korean-news/pipeline
Data:        ./newspapers  →  alice3:/zfsstore/user/<netid>/korean-news/data
==============================================

--- Syncing code ---
(rsync output, ~30 files)

--- Syncing data (PDFs) ---
(rsync output, 75 PDFs, ~400 MB)

--- Rewriting manifest → manifest_alice.csv ---
  Rewrote 75 pdf_path values
  Output: ./pipeline/manifest_alice.csv
```

The student checks `manifest_alice.csv` — every `pdf_path` now starts with `/zfsstore/user/<netid>/korean-news/data/`.

### Step 5 — Submit the job

```bash
ssh alice3 "cd /zfsstore/user/<netid>/korean-news/pipeline && sbatch run_ocr.slurm"
# Submitted batch job 2847193
```

Then — following the `alice-vllm-deploy` skill's SSH discipline — they consolidate checks into single commands, polling at 2-3 minute intervals:

```bash
ssh alice3 "squeue -j 2847193 -o '%.8T %.10M'; tail -20 logs/ocr_2847193.out"
```

Early on, the log shows Python imports (no visible GPU activity is normal):

```
==============================================
korean-news OCR via vLLM
==============================================
Job ID:    2847193
Node:      node852
Partition: gpu_lucdh
GPU:       NVIDIA A40
Model:     Qwen/Qwen3.5-35B-A3B-GPTQ-Int4
Started:   Sat Apr 19 14:32:08 CEST 2026
==============================================
Starting vLLM server on port 8000...
vLLM PID: 482341
Waiting for vLLM server /health (up to 900s)...
```

After ~13 minutes:

```
vLLM server ready after 784s

--- Stage 1: VLM OCR ---
[processing apsm_1966_01... 14 pages]
[processing apsm_1966_02... 12 pages]
...
```

Total job runtime: ~13 min cold start + ~90 min OCR + ~10 min CPU stages ≈ 1h 53m.

### Step 6 — Pull results and assemble (local)

```bash
rsync -avz alice3:/zfsstore/user/<netid>/korean-news/ocr_output/ ./ocr_output/
python3 scripts/corpus_assembler.py --parse-tags \
    --ocr-dir ocr_output \
    --manifest manifest.csv \
    --output corpus/
```

```
  corpus: 798 pages total, 791 with text
    JSON: corpus/corpus.json
    CSV : corpus/corpus.csv (791 rows)
  Text density:   99.1%
```

### Step 7 — Analyze in Python

```python
import pandas as pd

corpus = pd.read_csv("corpus/corpus.csv")
# ...proceed to Korean tokenisation and topic modelling
```

---

## What would change at a different scale?

- **Larger corpus (>5k pages):** same path, longer wall time. Switch to `gpu-a100-80g` partition if the `gpu_lucdh` queue is backed up.
- **Mixed scripts in the corpus:** split the manifest by layout or decade if one prompt no longer handles the variation cleanly.
- **No ALICE account:** wizard routes to API (see [`small_api`](small_api.html)) or local GPU (see [`small_local_gpu`](small_local_gpu.html)). Under $15 for the same corpus on Claude.
