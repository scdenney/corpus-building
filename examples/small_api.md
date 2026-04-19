---
title: "Small corpus via cloud API"
---

# Scenario: Small corpus via cloud API

**Who this is for:** a student with a modest PDF collection, a laptop, and no HPC access. The API path is the lowest-setup option. This scenario shows what the wizard produces for it and what the student does end-to-end.

---

## The situation

A grad student working on immigration discourse has pulled 75 journal articles from JSTOR — all English, mixed publishers, one-column scanned PDFs averaging 10 pages each. Total: ~750 pages. Analysis target: `pandas` + `spaCy` in Python. No GPU, no ALICE, modest research funds.

## Wizard answers

| Question | Answer |
|----------|--------|
| How many pages? | 501–1,000 |
| What compute? | None — laptop only |
| Languages/scripts? | Latin only |
| Document type? | Scanned books or articles |
| What software? | Python |
| Resource constraints? | Small budget, flexible timeline |

**Route:** API path. `api-ocr-runner` covers cost estimation, retry, and resume logic.

---

## Starter kit (what the wizard renders)

```
Recommended path: API
Corpus scale:    ~750 pages across 75 articles
Est. cost:       $7.50 – $15.00 on Claude Sonnet (or ~$3 on Gemini Flash)
Est. time:       2–3 hours sustained API calls + ~10 min of local stages
```

**Read first**
1. `corpus-from-pdfs` — end-to-end framing
2. `corpus-metadata-design` — schema for pandas output
3. `api-ocr-runner` — cost, rate limits, resume

**Paste into Claude Code / Codex**
> I have 75 English journal articles (roughly 750 pages). I want to extract the text via a cloud API (Claude Sonnet) and analyze it in Python with pandas. I'm on a laptop — no GPU, no HPC. Walk me through the `corpus-from-pdfs` pipeline and help me set up the OCR client and assembly stages. Start by asking about my analysis question so we can design the metadata schema before building.

**Or launch a fresh session directly**

```bash
claude "I have 75 English journal articles (roughly 750 pages). I want to extract the text via a cloud API (Claude Sonnet) and analyze it in Python with pandas. I'm on a laptop — no GPU, no HPC. Walk me through the corpus-from-pdfs pipeline."
```

**Files to copy**
- `templates/prompts.py.template` → `prompts.py` (Pattern A, English, no character enumeration needed)

**Commands (pre-filled)**
```bash
python3 scripts/inventory_builder.py --pdf-dir ./articles --output manifest.csv
python3 scripts/cost_estimator.py --pages 750 --compare
# OCR step — client script built with Claude Code, sends base64 page images
#   to the Claude API, writes results_raw.json per article
python3 scripts/corpus_assembler.py --ocr-dir ocr_output --manifest manifest.csv --output corpus/
```

---

## Walkthrough

### Step 1 — Inventory

```bash
python3 scripts/inventory_builder.py --pdf-dir ./articles --output manifest.csv
```

Expected output:

```
Found 75 PDFs under /Users/you/articles
Manifest: manifest.csv
  Total PDFs:     75
  Total pages:    748
  Content pages:  748
```

`manifest.csv` (first 3 rows):

```csv
pdf_id,filename,pdf_path,parent_folder,total_pages,content_start,content_end
apsr_2017_001,apsr_2017_001.pdf,/Users/you/articles/apsr_2017_001.pdf,articles,12,0,11
ajps_2018_044,ajps_2018_044.pdf,/Users/you/articles/ajps_2018_044.pdf,articles,9,0,8
jop_2019_108,jop_2019_108.pdf,/Users/you/articles/jop_2019_108.pdf,articles,11,0,10
```

### Step 2 — Cost check

```bash
python3 scripts/cost_estimator.py --pages 748 --compare
```

```
Pages:      748
Doctype:    book (dense scanned textbook / article page)
Per-page output tokens (ballpark): 1000–2000

Estimated total cost (USD):
  claude   (claude-sonnet-4-6   ): $    7.48 – $   14.96
  gpt      (gpt-4.1             ): $    7.48 – $   14.96
  gemini   (gemini-2.5-flash    ): $    1.50 – $    3.74
```

Under $15 on Claude, under $4 on Gemini. The student picks Claude for output quality on dense academic prose.

### Step 3 — OCR (inside Claude Code)

The student pastes the wizard's prompt into Claude Code. The agent:

1. Asks a clarifying question about the analysis: "What are you filtering or grouping by? Journal? Year? Topic?" The student says "journal and year."
2. Fills `prompts.py` with an English article prompt (Pattern A, no character enumeration).
3. Writes a ~50-line client script (`api_ocr.py`) that reads the manifest, rasterizes each page via PyMuPDF, sends to the Claude API, writes `ocr_output/<pdf_id>/results_raw.json`. Includes exponential backoff and a resume check.
4. Runs it in a terminal tab. The student monitors.

A single page's result looks like:

```json
{
  "pdf": "/Users/you/articles/apsr_2017_001.pdf",
  "model": "claude-sonnet-4-6",
  "language": "english",
  "pages": [
    {
      "page": 0,
      "text": "Immigration Attitudes and the Rise of Populist Parties\n\nAbstract\n\nRecent scholarship on immigration attitudes has emphasized...",
      "has_text": true
    },
    { "page": 1, "text": "...", "has_text": true }
  ]
}
```

After ~2.5 hours, all 75 articles are done. If anything crashed, re-running the client resumes from where it left off.

### Step 4 — Assemble

```bash
python3 scripts/corpus_assembler.py \
    --ocr-dir ocr_output \
    --manifest manifest.csv \
    --output corpus/
```

```
Assembling corpus...

  corpus: 748 pages total, 744 with text
    JSON: corpus/corpus.json
    CSV : corpus/corpus.csv (744 rows)

  PDFs processed: 75 (missing: 0)
  Total pages:    748
  Pages w/ text:  744
  Text density:   99.5%
```

`corpus/corpus.csv` (first 3 rows):

```csv
pdf_id,page,text,filename,parent_folder
apsr_2017_001,0,"Immigration Attitudes and the Rise of Populist Parties Abstract Recent scholarship on immigration attitudes has emphasized...",apsr_2017_001.pdf,articles
apsr_2017_001,1,"dimensional models of preference formation (Hainmueller and Hopkins 2014; Dancygier and Laitin 2014)...",apsr_2017_001.pdf,articles
apsr_2017_001,2,"...",apsr_2017_001.pdf,articles
```

### Step 5 — Analyze

```python
import pandas as pd
df = pd.read_csv("corpus/corpus.csv")
print(df.groupby("pdf_id")["text"].apply(len).describe())
```

The student now has 744 text-bearing pages joined to their source metadata, ready for `spaCy` tokenization and whatever comes next.

---

## What would change at a different scale?

- **Fewer than 50 pages?** Skip the resume logic, send the whole batch in one script, ignore cost entirely (<$1).
- **More than 5,000 pages?** Wizard would route to ALICE if the student has an account; API stays viable if they don't, but budget approaches $100.
- **Non-Latin script?** Pattern A prompt gains a character-set enumeration block. See [`small_alice`](small_alice.html) for the Polish case.
- **Comics or newspapers?** Switch to Pattern B (type tags) and pass `--parse-tags` to `corpus_assembler.py`. Different scenario.

## Try this yourself

The canned version of this walkthrough (with a handful of public-domain sample PDFs and pre-generated `results_raw.json` fragments) is what a first-run student would use to build intuition before spending real tokens. That sample dataset is TK — add 3 public-domain JSTOR-early-access or arXiv PDFs here and the wizard's "cold entry" link becomes a real click-through demo.
