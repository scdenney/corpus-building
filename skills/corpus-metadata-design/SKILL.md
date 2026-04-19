---
name: corpus-metadata-design
description: Guide metadata schema design for text corpora extracted from PDFs. Covers choosing granularity (document, page, paragraph), mandatory and optional fields, CSV vs JSON tradeoffs, compatibility with Orange Data Mining, R tidytext, and Python pandas. Use when (1) deciding what metadata fields to include in a corpus, (2) choosing between per-page and per-document rows, (3) structuring a CSV for Orange Data Mining or R, (4) designing JSON output for programmatic corpus access, (5) creating metadata for a bilingual or parallel corpus, (6) balancing corpus file size against information completeness, or (7) advising a student on corpus structure for their analysis.
argument-hint: "[describe your analysis goals, languages, and target analysis tool]"
---

# Metadata Schema Design for Text Corpora

## Instructions

### 1. Start from the Analysis Question

- **The schema should serve the analysis, not describe the data.** Ask: "What will I filter by? What will I group by? What will I compare?" Each answer becomes a column. A verb-ending study needs a speaker/narrator field; a topic model needs date and document type; a translation study needs aligned source/target identifiers.
- **Interview the researcher before designing.** Students often request "everything" but only need 3-5 fields for their actual analysis. Excess columns add complexity, inflate file size, and confuse the analysis tool. Design the minimum schema that answers their research questions, with room to add fields later.
- **Consider the analysis tool's constraints.** Orange Data Mining loads the entire CSV into memory and renders poorly with wide tables. R tidytext expects one-token-per-row or one-document-per-row. Python pandas is flexible but benefits from typed columns. Design for the primary tool.

### 2. Choose Granularity

- **One row per page is the safest default.** It preserves page references (critical for context lookup in the original PDF), keeps rows at a manageable text length, and works across all analysis tools. This is the recommended starting point for any new corpus.
- **One row per document (chapter, article, book) when:** The analysis aggregates across pages (topic modeling, document classification), individual pages have too little text to analyze meaningfully (comics with 1-2 speech bubbles per page), or the researcher explicitly needs document-level units.
- **One row per sentence or paragraph when:** The analysis requires fine-grained units (sentiment analysis, named entity extraction, syntactic analysis). Requires reliable sentence segmentation, which is language-dependent and error-prone on OCR output. Avoid for Korean without a dedicated tokenizer.
- **Never mix granularities in one CSV.** If both page-level and document-level views are needed, produce two separate files. Mixing causes confusion and breaks analysis tools that assume uniform rows.

### 3. Mandatory Fields

Every text corpus should include:

| Field | Type | Purpose |
|-------|------|---------|
| `id` or `doc_id` | string | Unique identifier for the row (e.g., `empress_kr_001_p005`) |
| `source_file` or `filename` | string | Original PDF filename for traceability |
| `language` | string | ISO code or label (`korean`, `english`, `polish`) |
| `text` | string | The extracted text content |
| `has_text` | boolean | Whether this row contains meaningful text (for filtering) |

For page-level corpora, add:
| `page` | integer | PDF page number (0-indexed) for context lookup |

For document-level corpora, add:
| `word_count` | integer | Enables length-based filtering and normalization |

### 4. Common Optional Fields

Add based on analysis needs:

| Field | When to include | Example |
|-------|----------------|---------|
| `series` / `collection` | Multiple source collections | `empress`, `maru`, `omniscient_reader` |
| `chapter` / `section` | Sequential documents | `1`, `42` |
| `date` / `year` | Temporal analysis | `1970`, `2016` |
| `author` | Attribution analysis | Author name or code |
| `document_type` | Heterogeneous corpora | `textbook`, `newspaper`, `comic` |
| `text_type` | Mixed content types | `dialogue`, `narration`, `caption` |
| `dialogue` | Filtered text columns | Speech bubble text only |
| `narration` | Filtered text columns | Narrator text only |
| `sfx` | Sound effects (comics) | Onomatopoeia text |
| `text_tagged` | Raw VLM output preservation | `[DIALOGUE] 와, 대박.` |
| `subject` | Topic/domain classification | `history`, `social_studies` |
| `level` | Education level | `elementary`, `middle`, `high` |

### 5. The "Both-And" Column Strategy

- **Provide a combined `text` column AND split columns.** The `text` column (all content joined, tags stripped) serves full-text search, word clouds, and topic models. Split columns (`dialogue`, `narration`, `sfx`) serve targeted linguistic analysis. The `text_tagged` column preserves the raw VLM output for re-processing.
- **This is not redundancy — it's usability.** Students working in Orange Data Mining need a single text column for the word cloud widget. Researchers doing verb-ending analysis need only the dialogue column. Preserving the tagged output enables future re-parsing without re-running OCR.

### 6. CSV Design for Orange Data Mining

- **Include only text-bearing rows.** Orange loads the full CSV into memory. Pages with no text (blank panels in comics, illustration-only pages) inflate the file without adding analytical value. Record them in the JSON output but exclude from CSV.
- **Keep columns minimal.** Orange displays all columns in the data table widget. 5-8 columns is manageable; 15+ becomes unwieldy. Put secondary metadata in the JSON, not the CSV.
- **Use simple types.** Strings and integers only. No nested objects, no arrays, no multi-line text within cells. If a cell must contain multi-line text, join lines with spaces.
- **UTF-8 encoding always.** Orange supports UTF-8. Never use Latin-1 or EUC-KR, even for Korean-only corpora.
- **Test by loading.** Before delivering the corpus, open the CSV in Orange and verify: data table renders, word cloud widget works, text filtering by metadata column works.

### 7. JSON Design for Programmatic Access

- **Include everything the CSV leaves out.** The JSON gets no-text pages, full tag structure, per-page diagnostics, pipeline metadata (model, timestamps, settings), and nested objects that CSV can't represent.
- **Structure as metadata block + pages array.** Top-level `metadata` object with corpus-level stats, plus a `pages` array of per-row objects. This pattern works cleanly with `jq`, Python `json.load()`, and R `jsonlite::fromJSON()`.
- **Produce one JSON per language.** For bilingual corpora, separate files (`corpus_korean.json`, `corpus_english.json`) are simpler than a single file with language filtering. Join on shared `series` + `chapter` keys when cross-language analysis is needed.

### 8. Bilingual and Parallel Corpus Design

- **Align at the chapter level, not the page level.** Korean and English versions of the same webtoon chapter have different page counts (different panel layouts, text density). Chapter is the natural alignment unit.
- **Use consistent identifiers across languages.** Both `corpus_korean.csv` and `corpus_english.csv` should use the same `series` and `chapter` columns, enabling joins: `merge(kr, en, on=['series', 'chapter'], suffixes=('_kr', '_en'))`.
- **Separate files, not interleaved rows.** Two CSVs are better than one CSV with a language column for most analysis tools. The combined view is easily constructed via merge/join when needed.

## Quality Checks

- [ ] **Schema derived from research question:** Every field justified by a planned filter, grouping, or comparison
- [ ] **Granularity is uniform:** All rows represent the same unit (page, document, or sentence) — no mixing
- [ ] **Mandatory fields present:** id, source_file, language, text, has_text included in every corpus
- [ ] **Combined + split columns provided:** Both full `text` and filtered type columns available where applicable
- [ ] **CSV excludes empty rows:** Only text-bearing rows included in the CSV output
- [ ] **CSV is loadable:** Tested in the target analysis tool (Orange, R, Python) before delivery
- [ ] **JSON captures everything:** No-text pages, metadata, diagnostics, and pipeline settings preserved in JSON
- [ ] **Cross-language alignment documented:** Shared identifier columns and join strategy specified for bilingual corpora
- [ ] **File encoding is UTF-8:** Verified, especially for Korean, Polish, and other non-ASCII corpora
