---
title: "Small corpus via ALICE HPC"
---

# Scenario: Small corpus via ALICE HPC

**Who this is for:** a student who has an ALICE account and wants free compute. Same corpus size as the API scenario — this is about the path, not the scale.

---

## The situation

A grad student studying press coverage during the Polish People's Republic has 75 historical newspaper issues (~800 pages, 1960s–1980s). Text contains Polish diacritics (ą, ć, ę, ł, ń, ó, ś, ź, ż) and occasional pre-reform spelling. Analysis target: `stm` in R for topic modelling by year. ALICE account active, no API budget allocated.

## Wizard answers

| Question | Answer |
|----------|--------|
| How many pages? | 501–1,000 |
| What compute? | ALICE account, ready to use |
| Languages/scripts? | Historical scripts / older orthographies |
| Document type? | Newspapers or multi-column layouts |
| What software? | R |
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
2. `corpus-metadata-design` — schema for R `stm`
3. `alice-vllm-deploy` — SLURM, cold-start timing, SSH discipline

**Paste into Claude Code / Codex**
> I have 75 Polish historical newspaper scans (roughly 800 pages). The text uses Polish diacritics (ą, ć, ę, ł, ń, ó, ś, ź, ż) and occasional pre-reform spelling. I have an ALICE account and want to run vLLM on `gpu_lucdh`. My analysis target is `stm` in R. Walk me through the `corpus-from-pdfs` pipeline. Start by helping me fill in the SLURM template and the Polish prompt. Then help me deploy and monitor the job.

**Or launch a fresh session directly**

```bash
claude "I have 75 Polish historical newspaper scans (roughly 800 pages). The text uses Polish diacritics and occasional pre-reform spelling. I have an ALICE account and want to run vLLM on gpu_lucdh. My analysis target is stm in R. Walk me through the corpus-from-pdfs pipeline."
```

**Files to copy**
- `templates/prompts.py.template` → `prompts.py` (Pattern A, Polish diacritics enumerated)
- `templates/run_ocr.slurm.template` → `run_ocr.slurm` (project name, `gpu_lucdh`, model, account flag uncommented)

**Commands (pre-filled)**
```bash
python3 scripts/inventory_builder.py --pdf-dir ./newspapers --output manifest.csv
bash scripts/alice_deploy.sh \
    --host alice3 \
    --code-src ./pipeline --data-src ./newspapers \
    --manifest ./manifest.csv \
    --remote-base /zfsstore/user/<netid>/polish-news
ssh alice3 "cd /zfsstore/user/<netid>/polish-news/pipeline && sbatch run_ocr.slurm"
# …wait for the SLURM job to finish (monitor via squeue + log tail)…
python3 scripts/corpus_assembler.py --ocr-dir ocr_output --manifest manifest.csv --output corpus/
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

Inside Claude Code, the student opens `prompts.py` (copied from the template) and fills Pattern A for Polish:

```python
PROMPTS = {
    "polish": (
        "Extract all text from this document image. "
        "The text is in Polish and contains Polish diacritical characters "
        "(ą, ć, ę, ł, ń, ó, ś, ź, ż). "
        "Transcribe every character exactly as it appears. "
        "Output in markdown format preserving headings, paragraphs, "
        "footnotes, and tables. "
        "If the page has no text at all, output only: [NO_TEXT]. "
        "Do not translate or interpret the text."
    ),
}
LANGUAGE_PROMPT_MAP = {"polish": "polish"}
```

Claude Code reviews this against the `corpus-from-pdfs` guidance on character enumeration and confirms it's ready. No `VALID_TAGS` needed — Pattern A doesn't use type tags.

### Step 3 — Fill `run_ocr.slurm`

From the template, with the student's values substituted:

- `{{PROJECT_NAME}}` → `polish-news`
- `{{PARTITION}}` → `gpu_lucdh`
- `{{WALL_TIME}}` → `04:00:00`
- `{{GPU_SPEC}}` → `gpu:1`
- `#SBATCH --account=gpu_lucdh` line uncommented
- `{{PIPELINE_DIR}}` → `/zfsstore/user/<netid>/polish-news/pipeline`
- `{{MODEL_ID}}` → `Qwen/Qwen3.5-35B-A3B-GPTQ-Int4`
- `{{QUANT_BACKEND}}` → `gptq_marlin`
- Client / diagnostics / assembler script placeholders → filenames from the pipeline

### Step 4 — Deploy

```bash
bash scripts/alice_deploy.sh \
    --host alice3 \
    --code-src ./pipeline --data-src ./newspapers \
    --manifest ./manifest.csv \
    --remote-base /zfsstore/user/<netid>/polish-news
```

Output sketch:

```
==============================================
alice_deploy.sh
==============================================
Host:        alice3
Code:        ./pipeline  →  alice3:/zfsstore/user/<netid>/polish-news/pipeline
Data:        ./newspapers  →  alice3:/zfsstore/user/<netid>/polish-news/data
==============================================

--- Syncing code ---
(rsync output, ~30 files)

--- Syncing data (PDFs) ---
(rsync output, 75 PDFs, ~400 MB)

--- Rewriting manifest → manifest_alice.csv ---
  Rewrote 75 pdf_path values
  Output: ./pipeline/manifest_alice.csv
```

The student checks `manifest_alice.csv` — every `pdf_path` now starts with `/zfsstore/user/<netid>/polish-news/data/`.

### Step 5 — Submit the job

```bash
ssh alice3 "cd /zfsstore/user/<netid>/polish-news/pipeline && sbatch run_ocr.slurm"
# Submitted batch job 2847193
```

Then — following the `alice-vllm-deploy` skill's SSH discipline — they consolidate checks into single commands, polling at 2-3 minute intervals:

```bash
ssh alice3 "squeue -j 2847193 -o '%.8T %.10M'; tail -20 logs/ocr_2847193.out"
```

Early on, the log shows Python imports (no visible GPU activity is normal):

```
==============================================
polish-news OCR via vLLM
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
rsync -avz alice3:/zfsstore/user/<netid>/polish-news/ocr_output/ ./ocr_output/
python3 scripts/corpus_assembler.py \
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

### Step 7 — Analyze in R

```r
library(tidytext)
library(stm)

corpus <- read.csv("corpus/corpus.csv", encoding = "UTF-8")
# ...proceed to stm preprocessing and model fitting
```

---

## What would change at a different scale?

- **Larger corpus (>5k pages):** same path, longer wall time. Switch to `gpu-a100-80g` partition if the `gpu_lucdh` queue is backed up.
- **Mixed scripts in the corpus:** split the manifest by language, run separate SLURM jobs with the appropriate prompt per language.
- **No ALICE account:** wizard routes to API (see [`small_api`](small_api.html)) or local GPU (see [`small_local_gpu`](small_local_gpu.html)). Under $15 for the same corpus on Claude.
