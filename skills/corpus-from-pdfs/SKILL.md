---
name: corpus-from-pdfs
description: Guide the full process of building a structured text corpus from PDF documents. Covers inventory building, OCR approach selection (VLM on HPC, cloud API, direct transformers), metadata schema design, output formatting for analysis tools, and quality verification. Use when (1) planning how to extract text from a collection of PDFs, (2) choosing between HPC/GPU, API, or local OCR approaches, (3) deciding what metadata to track for a text corpus, (4) structuring corpus output for Orange Data Mining, R tidytext, or Python pandas, (5) designing a pipeline for multilingual or mixed-format PDFs, (6) advising a student on their first corpus-building project, or (7) converting a folder of scanned documents into a research-ready dataset.
argument-hint: "[describe your PDFs, languages, analysis goals, and compute access]"
---

# Building a Text Corpus from PDFs

## Instructions

### 1. Assess Your Source Material

- **Determine the PDF type before choosing tools.** Scanned book pages (single embedded image per page) need VLM-based OCR. Born-digital PDFs with selectable text can use direct text extraction (PyMuPDF `get_text()`). Comics and webtoons have text embedded in artwork requiring VLM with specialized prompts. Mixed collections may need different strategies per document type.
- **Inventory the collection first.** Before any OCR, scan the directory structure, count files, measure total pages, check file sizes, and parse filenames for metadata (language, chapter, date, edition). A manifest CSV is the single source of truth for the pipeline. Build it programmatically, not by hand.
- **Check for filesystem encoding issues.** macOS HFS+/APFS uses NFD Unicode normalization for filenames, which decomposes Korean, Japanese, and accented characters. If filenames contain non-ASCII characters, normalize to NFC before regex matching. This is a common silent failure mode.
- **Detect content page ranges automatically.** Many PDFs include non-content pages: title pages, navigation UI (web-saved PDFs), comment sections, blank pages. Use selectable-text detection (PyMuPDF) to identify and skip these. For web-saved Webtoons, page 0 typically contains Naver/Webtoon navigation text.

### 2. Choose Your OCR Approach

Four approaches are available, each with different tradeoffs:

**A. vLLM on HPC (recommended for bulk)**
- Best for: Large corpora (>500 pages), multilingual, research-grade accuracy
- Requires: SLURM cluster access, GPU (A100 80GB or A40 48GB), pre-cached model weights
- Cost: Free (HPC compute time)
- Speed: ~6s/page on A100 after model startup; cold start takes ~13 minutes
- Model: Qwen3.5-35B-A3B-GPTQ-Int4 via `gptq_marlin` quantization (910 OCRBench)
- Pattern: Start vLLM server in background → send pages via OpenAI-compatible API → shut down
- See the `alice-vllm-deploy` skill for deployment details

**B. Direct HuggingFace Transformers (local GPU)**
- Best for: Smaller corpora, development/testing, when vLLM has compatibility issues
- Requires: Local GPU (24GB+ VRAM) or HPC allocation
- Cost: Free
- Speed: ~10-30s/page depending on model and quantization
- Pattern: Load model directly via `AutoModelForImageTextToText`, process pages sequentially
- Quantization: BitsAndBytes NF4 for dense models; GPTQ for MoE models (BnB NF4 is incompatible with MoE on transformers v5)

**C. Cloud API (Claude, GPT)**
- Best for: Small corpora (<1000 pages), quick prototyping, no GPU access
- Requires: API key (Anthropic or OpenAI)
- Cost: ~$0.01-0.02/page ($10-20 per 1000 pages)
- Speed: ~5-15s/page depending on rate limits
- Pattern: Base64-encode page image → send to chat API → parse response
- See the `api-ocr-runner` skill for implementation details

**D. Traditional OCR (Tesseract)**
- Best for: Clean printed text on white backgrounds, as a baseline for comparison
- Requires: Tesseract system package
- Cost: Free
- Speed: ~1-2s/page
- Limitation: Fails on colored backgrounds, stylized text, complex layouts, non-Latin scripts with poor language packs

- **Use the decision tree.** Do you have HPC access? → Yes: vLLM for bulk, API for testing prompts. No: → Is your corpus <1000 pages? → Yes: API. No: → Do you have a local GPU? → Yes: Direct transformers. No: → API (budget accordingly) or request HPC access.
- **Always prototype on a small sample first.** Regardless of approach, run 10-20 pages through the pipeline before committing to bulk processing. Inspect the output manually. Adjust prompts. This prevents wasting GPU-hours or API credits on a broken pipeline.

### 3. Design Your Prompts

- **Prompts are the most important technical decision.** The same model with different prompts produces dramatically different output. Invest time here.
- **Be explicit about the document type.** "This is a page from a Korean webtoon" or "This is a scanned Polish history textbook from the 1970s" gives the VLM critical context for interpreting the image.
- **Enumerate expected character sets.** For Polish, list every diacritic (ą, ć, ę, ł, ń, ó, ś, ź, ż). For Korean, mention both hangul and hanja. For mixed-script documents, specify which scripts to expect.
- **Request structured output.** Tags like `[DIALOGUE]`, `[NARRATION]`, `[SFX]` for comics; markdown with headings and tables for textbooks. Structure during extraction is far cheaper than post-hoc classification.
- **Include negative instructions.** "Do not translate," "do not describe the image," "do not add content not present." VLMs will summarize, translate, or describe unless told not to.
- **Handle empty pages explicitly.** Instruct the model: "If no text on page, output only: [NO_TEXT]." Without this, models hallucinate content for blank pages.
- **Store prompts in a separate module.** A `prompts.py` file with a dict mapping language/document-type keys to prompt strings keeps prompts version-controlled and auditable.

### 4. Structure Your Metadata

- **Start from the analysis question, not the data.** Ask: "What will I filter, group, or compare?" The answer determines your metadata fields. A verb-ending study needs speaker/narrator classification; a topic model needs date and document type; a translation study needs aligned source/target pairs.
- **Mandatory fields for any corpus:** document/PDF ID, language, source filename, page number, text content, has_text flag
- **Common optional fields:** series/collection name, chapter/section number, date/year, author, document type, text type (dialogue/narration/caption), word count
- **One row per page is the safest default.** It preserves page references for context lookup, keeps rows manageable, and works with any analysis tool. Per-document aggregation loses page-level detail; per-sentence requires reliable sentence segmentation.
- **Produce both JSON and CSV.** JSON preserves structure (nested fields, arrays, metadata blocks) for programmatic access. CSV is the universal interchange format for analysis tools. The CSV should contain only text-bearing rows to keep file size small.
- See the `corpus-metadata-design` skill for detailed schema guidance.

### 5. Build the Pipeline

- **Follow the multi-stage pattern.** Stage 0: Inventory → Stage 1: OCR → Stage 2: Diagnostics + Cleanup → Stage 3: Assembly → Stage 4: Verification. Each stage reads the previous stage's output and produces structured JSON. This separation allows re-running individual stages without re-processing everything.
- **Make the pipeline resumable.** Check for existing output before processing each document. A simple file-existence check (`results_raw.json` present → skip) enables restarting after failures without re-processing completed work.
- **Use the tranche/gate pattern for bulk runs.** Process a test batch (3-5 documents per language), manually evaluate quality, then proceed to bulk. This is the single most important resource management decision — it prevents wasting hours of GPU time on a broken prompt or misconfigured pipeline.
- **Apply rule-based cleanup unconditionally.** Unicode normalization (NFKC), control character removal, whitespace normalization, and repetition collapse are safe, deterministic, and fast. Run these on every corpus.
- **LLM-based cleanup is optional and language-dependent.** Pilot-test per language before committing. Some languages see CER improvement; others see degradation. See the `post-ocr-cleanup` skill for methodology.

### 6. Verify and Deliver

- **Check completeness.** Every PDF in the manifest should have corresponding OCR output. Report any gaps.
- **Check cross-language alignment.** If the corpus has parallel translations (e.g., Korean + English chapters), verify that chapter counts match and shared identifiers align.
- **Report text density.** What percentage of pages have text? For comics, 50-70% is normal. For textbooks, 90%+ is expected. Anomalous density suggests pipeline issues.
- **Spot-check randomly.** Display 10-20 random page images alongside extracted text for human review. This catches systematic errors that aggregate statistics miss.
- **Test in the target analysis tool.** Load the CSV in Orange Data Mining (or R, or Python) and verify that word clouds, text analysis widgets, and filtering work as expected. A corpus that can't be loaded is not a corpus.

## Quality Checks

- [ ] **PDF type assessed:** Document format identified (scanned, born-digital, comic, mixed) before choosing OCR approach
- [ ] **Manifest built programmatically:** Complete inventory with metadata parsed from filenames and directory structure
- [ ] **OCR approach justified:** Choice of vLLM/API/transformers/Tesseract based on corpus size, languages, and compute access
- [ ] **Prompts prototyped on sample:** 10-20 pages processed and manually inspected before bulk run
- [ ] **Character sets enumerated in prompts:** Language-specific diacritics and scripts explicitly listed
- [ ] **Metadata schema derived from analysis goals:** Fields chosen based on planned filters, groupings, and comparisons
- [ ] **Pipeline is resumable:** Existing output detected and skipped on re-run
- [ ] **Test tranche gated:** Quality evaluated on small batch before bulk processing
- [ ] **Rule-based cleanup applied:** NFKC normalization, control chars, whitespace standardized across corpus
- [ ] **Completeness verified:** Every manifest entry has corresponding output; no gaps
- [ ] **Spot-check conducted:** Random pages visually compared against extracted text
- [ ] **Target tool tested:** CSV loaded successfully in the intended analysis tool
