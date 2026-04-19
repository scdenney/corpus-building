---
name: source-file-extraction
description: Extract plain text from documents in formats other than scanned PDFs — DOCX, HTML, TXT, ePub, XML/TEI, database exports (LexisNexis/Factiva/ProQuest), image files, and born-digital PDFs. Covers the best Python tool per format, common gotchas, one-line extraction sketches, and criteria for when to fall back to the VLM-OCR path. Use when (1) your corpus includes non-PDF source files, (2) born-digital PDFs give garbage output from extraction, (3) you need to process LexisNexis/Factiva/ProQuest RTF or CSV exports, (4) you're working with TEI-XML or ePub files, (5) scraped web text needs structured cleanup, (6) deciding whether a file should go through text-extraction or VLM-OCR, or (7) building a format-agnostic ingestion stage for a mixed-format corpus.
argument-hint: "[describe your source format(s) and what you need to extract]"
---

# Text Extraction from Non-Scanned Formats

## Instructions

### 1. Extraction Principle

- **Extract to plain text at the earliest stage, then hand off.** Students arrive with a dozen different source formats — DOCX, HTML, ePub, XML, RTF exports from databases, image files, born-digital PDFs. The downstream corpus pipeline (preprocessing, cleanup, metadata schema, assembly via `corpus_assembler.py`) only needs one thing from each: clean UTF-8 text plus whatever structural metadata the researcher wants to preserve. Make the extractor format-specific; make everything downstream format-agnostic.
- **Produce the same `results_raw.json` schema the OCR path produces.** After extraction, each document should write to `ocr_output/<doc_id>/results_raw.json` with the same `{pdf, language, pages: [{page, text, has_text}]}` shape the VLM-OCR client uses. That keeps the diagnostics, rule-fixes, and assembly stages working without branching.
- **Decide text-extraction vs. VLM-OCR per file, not per format.** "Text-bearing" and "contains recoverable text" aren't the same. A DOCX can wrap an image-only scan; an ePub can be fixed-layout with no text at all; a born-digital PDF can have a garbage ToUnicode map that extracts as gibberish. When a quick diagnostic shows extraction failed, reroute that file to the VLM path.

### 2. DOCX (Microsoft Word)

- **Primary tool:** `python-docx` for structured paragraph and table access.
- **Fallback:** `pandoc` (subprocess) when you also need footnotes, comments, or Markdown conversion.
- **Gotchas:** `python-docx` sees only paragraphs and tables — text inside text boxes, SmartArt, or headers/footers needs explicit traversal. Legacy `.doc` binary files aren't supported; convert with `libreoffice --headless --convert-to docx` first.
- **Sketch:** `text = "\n".join(p.text for p in docx.Document(path).paragraphs)`
- **Route to VLM OCR when:** the DOCX wraps an image-only scan (common with "Save as Word" from a scanner) or text was pasted in as a picture.

### 3. HTML / Scraped Web Pages

- **Primary tool:** `trafilatura` for main-content extraction (strips nav, footer, ads).
- **Fallback:** `BeautifulSoup` with `lxml` when you need precise DOM control.
- **Gotchas:** encoding is rarely declared correctly — use `charset-normalizer` to detect, then `ftfy.fix_text()` to repair mojibake. JavaScript-rendered pages need a headless browser (Playwright) before parsing.
- **Sketch:** `text = trafilatura.extract(trafilatura.fetch_url(url), favor_precision=True)`
- **Route to VLM OCR when:** the page is a screenshotted article or PDF-in-an-iframe with no underlying HTML text.

### 4. Plain Text (TXT, MD)

- **Primary tool:** stdlib `open()`, with `charset-normalizer` for unknown encodings and `ftfy.fix_text()` for repair.
- **Gotchas:** Windows CP1252 vs. UTF-8 confusion (smart quotes rendered as `â€œ`), mixed line endings, BOM markers, NFC vs. NFD normalisation (macOS-sourced filenames and Korean / Vietnamese text especially).
- **Sketch:** `text = ftfy.fix_text(pathlib.Path(p).read_text(encoding=charset_normalizer.from_path(p).best().encoding))`
- **Route to VLM OCR when:** the "txt" is actually a dump of OCR garbage from an upstream tool — re-OCR the original rather than attempt repair.

### 5. ePub

- **Primary tool:** `EbookLib` to walk spine items; `BeautifulSoup` to strip the XHTML.
- **Gotchas:** EPUB3 fixed-layout files are often image-only (children's books, manga). DRM'd files fail silently — check for the `encryption.xml` manifest first.
- **Sketch:** `text = "\n".join(BeautifulSoup(item.get_content(), "lxml").get_text() for item in ebooklib.epub.read_epub(p).get_items_of_type(ebooklib.ITEM_DOCUMENT))`
- **Route to VLM OCR when:** fixed-layout ePub with embedded page images, or DRM strips out the text.

### 6. XML / TEI

- **Primary tool:** `lxml.etree` for validated parsing.
- **Fallback:** `BeautifulSoup(xml, "lxml-xml")` for forgiving traversal of malformed files.
- **Gotchas:** TEI namespaces must be declared in XPath queries (`{http://www.tei-c.org/ns/1.0}`). The choice between `<orig>`/`<reg>` or `<sic>`/`<corr>` is an editorial decision you must make explicit in the methodology chapter. Entity references may not resolve offline.
- **Sketch:** `text = " ".join(lxml.etree.parse(p).xpath("//tei:text//text()", namespaces={"tei": "http://www.tei-c.org/ns/1.0"}))`
- **Route to VLM OCR when:** never — if XML fails, the source is broken, not the format.

### 7. Database Exports (LexisNexis / Factiva / ProQuest)

- **Primary tool:** `news_extract` (`nexis_rtf_extract`, `factiva_rtf_extract`) for RTF article bundles; `pandas.read_csv` for ProQuest CSV.
- **Fallback:** `striprtf` for generic RTF stripping when the vendor-specific parser chokes.
- **Gotchas:** each vendor's export schema drifts over time — field delimiters, date formats, and duplicate-article markers change without notice. LexisNexis exports silently truncate at 500 articles per file; always check the tail of the export matches your search result count.
- **Sketch:** `articles = news_extract.nexis_rtf_extract(path_to_rtf)`
- **Route to VLM OCR when:** the vendor gives you a PDF bundle instead of RTF or CSV (increasingly common with ProQuest historical newspapers).

### 8. Image Files (JPG, PNG, TIFF)

- **Primary tool:** the VLM-OCR path. Route single images through the same pipeline as PDF pages; prompt and post-processing are identical.
- **Fallback:** `pytesseract` for clean, high-contrast typography with a well-supported language pack.
- **Gotchas:** multi-page TIFFs need `PIL.Image.seek()` per frame; orientation EXIF tags are often wrong (use `exif_transpose` before inference); CMYK images must be converted to RGB.
- **Sketch:** `text = pytesseract.image_to_string(Image.open(p).convert("RGB"))` (fallback) — otherwise hand the image to your existing VLM prompt.
- **Route to VLM OCR when:** always, unless text is printed, monolingual, and high-resolution (Tesseract's sweet spot).

### 9. Born-Digital PDFs (with Text Layer)

- **Primary tool:** `pymupdf4llm` for clean Markdown with preserved headings.
- **Fallback:** `pdfplumber` when you need table coordinates or column-aware layout.
- **Gotchas:** "text layer present" is not "text layer correct" — some PDFs have garbage ToUnicode maps that yield ligature glyphs or shuffled reading order; two-column academic PDFs often concatenate columns. Always spot-check the first extraction against the rendered page.
- **Sketch:** `text = pymupdf4llm.to_markdown(path)`
- **Route to VLM OCR when:** extraction produces gibberish (broken CMap), reading order is scrambled, or the file turns out to be a scan mis-tagged with an empty text layer. Quick diagnostic: if `len(extracted_text) / num_pages < 100`, re-route through the VLM pipeline.

### 10. Mixed-Format Corpora

- **Build the manifest first.** Use `inventory_builder.py` to walk the source directory and classify each file by extension. Add a `source_format` column to the manifest so every downstream stage knows what route the file took.
- **Run one extractor per format, not one Swiss-Army-knife extractor.** Each format has enough gotchas that format-specific tools pay off. Orchestrate them from a single Python script that reads the manifest and dispatches by `source_format`.
- **Normalise to a common output schema.** Regardless of extractor, write per-document `results_raw.json` to `ocr_output/<doc_id>/` so `corpus_assembler.py` can join everything against the manifest metadata at the end.
- **Log format-level statistics.** Report in the methodology chapter how many files came from each source format and what percentage of each needed re-routing to the VLM path. This matters for reproducibility and for understanding where extraction errors concentrate.

## Quality Checks

- [ ] **Format classified per file:** Every file in the manifest has an explicit `source_format` column; nothing assumed
- [ ] **Extractor matched to format:** Each format uses its format-specific tool; no generic "extract everything" fallback as the default path
- [ ] **Extraction diagnostic run:** For each format, a quick check (character count / page or visual spot-check) confirms the extractor produced usable text before bulk processing
- [ ] **VLM-OCR fallback wired up:** Files where text-extraction fails the diagnostic are rerouted to the VLM pipeline automatically or flagged for manual review
- [ ] **Output schema uniform:** All extractors write to the same per-document `results_raw.json` shape so `corpus_assembler.py` works identically across formats
- [ ] **Unicode normalisation applied:** Text is NFC-normalised after extraction; NFD-decomposed filenames (macOS) and mixed-encoding content (CP1252/UTF-8) are handled explicitly
- [ ] **Format distribution reported:** Methodology chapter reports how many files came from each source format and how many needed rerouting
