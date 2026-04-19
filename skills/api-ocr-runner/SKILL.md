---
name: api-ocr-runner
description: Guide OCR text extraction via cloud APIs (Claude, GPT, Gemini) as an alternative to HPC-based VLM inference. Covers cost estimation, provider selection, rate limit handling, resume logic, and when API makes sense versus local or HPC inference. Use when (1) extracting text from PDFs without GPU access, (2) estimating API costs for a document corpus, (3) choosing between Claude, GPT, and Gemini for OCR, (4) prototyping OCR prompts before deploying to HPC, (5) processing a small corpus (<1000 pages) quickly, (6) building a resume-capable API OCR pipeline, or (7) comparing API OCR quality against local VLM output.
argument-hint: "[describe your corpus size, languages, and budget]"
---

# OCR via Cloud APIs

## Instructions

### 1. When to Use API vs. HPC vs. Local

- **API is the right choice when:** (a) corpus is small (<1000 pages, ~$10-20), (b) you have no GPU access, (c) you're prototyping prompts before an HPC run, or (d) you need results in hours, not days of HPC queue time.
- **HPC is the right choice when:** (a) corpus exceeds 1000 pages, (b) you have free compute allocation, (c) you need reproducibility with pinned model weights, or (d) the total API cost exceeds $50-100.
- **Local GPU is the right choice when:** (a) you have a 24GB+ GPU available, (b) you want to iterate rapidly on prompts without API costs, or (c) privacy requirements prohibit sending data to cloud providers.
- **API + HPC is a valid hybrid.** Use API for the test tranche (10-20 pages, fast feedback on prompt quality), then deploy to HPC for bulk. This is often the fastest path to a working pipeline.

### 2. Cost Estimation

- **Formula:** `pages × avg_tokens_per_page × price_per_token = total_cost`
- **Typical page token counts:**
  - Scanned textbook page (dense text): 1000-2000 output tokens
  - Comic/webtoon page: 50-200 output tokens (sparse text)
  - Image input tokens: ~1000-4000 depending on resolution and provider
- **Rough per-page costs (as of 2026):**
  - Claude Sonnet 4.6: ~$0.01-0.02/page
  - GPT-4.1: ~$0.01-0.02/page
  - Gemini 2.5 Flash: ~$0.002-0.005/page (cheapest for bulk)
- **Quick estimate:** Multiply page count by $0.015 for Claude/GPT, $0.004 for Gemini Flash.
- **Always run 10 pages first** to get an actual per-page cost measurement. Token counts vary significantly by document type.

### 3. Provider Selection

- **Claude Sonnet 4.6:** Strong multilingual OCR, excellent at following structured output instructions (type tags, markdown). Good for Korean, Polish, and mixed-script documents. Consistent output format.
- **GPT-4.1:** Comparable quality, slightly different output style. OpenAI-compatible API means the same client code works with vLLM (useful for HPC migration). Better rate limits for bulk processing.
- **Gemini 2.5 Flash:** Significantly cheaper, adequate quality for clean printed text. May struggle with degraded historical documents or complex panel layouts. Good for prototyping and cost-sensitive bulk runs.
- **Use the same prompt across providers** to enable fair comparison. The prompt module pattern (`prompts.py` with a dict of prompts) keeps this clean.

### 4. Implementation Pattern

```python
# The client pattern is identical for all providers:
# 1. Extract image from PDF (PyMuPDF native extraction)
# 2. Base64-encode the image
# 3. Send to chat API with OCR prompt
# 4. Parse response text
# 5. Save per-page result to JSON
```

- **Use the OpenAI Python client for everything.** Claude has its own SDK (`anthropic`), but GPT and vLLM both use the `openai` package. When migrating from API to vLLM on HPC, the client code barely changes — just swap the `base_url` from `https://api.openai.com/v1` to `http://127.0.0.1:8000/v1`.
- **Implement retry with exponential backoff.** All providers rate-limit. Retry on 429/overloaded errors with `wait = 2^attempt × 3` seconds, up to 5 attempts. Log rate-limit events but don't treat them as failures.
- **Build resume capability from the start.** Check for existing `results_raw.json` before processing each PDF. Within a PDF, check which pages already have results. Resume means re-running after a crash or rate-limit exhaustion costs nothing for completed work.
- **Save results incrementally.** Write `results_raw.json` after each PDF completes (or periodically within a PDF for very large documents). Never wait until all PDFs are done to write output — a crash loses everything.

### 5. Rate Limiting and Throughput

- **Claude:** ~50 requests/minute on standard tier. At ~10s per page, expect 6 pages/minute sustained.
- **GPT:** Higher rate limits but varies by account tier and model. GPT-4.1 typically allows 60-100 requests/minute.
- **Gemini Flash:** Generous free tier (1500 requests/day), fast inference (~2-5s per page).
- **Parallelism:** API calls can be parallelized (unlike single-GPU sequential processing). Use `asyncio` or thread pools for 3-5x throughput. But respect rate limits — more parallel requests hit the ceiling faster.
- **Time estimate:** 1000 pages at 6 pages/minute = ~3 hours for Claude/GPT. Gemini Flash may be 2-3x faster.

### 6. Output Format Compatibility

- **Use the same output JSON format as the HPC pipeline.** This ensures that diagnostics, rule fixes, assembly, and verification scripts work identically on API-generated and vLLM-generated output. The `results_raw.json` schema should be: `{pdf, model, language, processed, total_pages_in_pdf, pages_processed, pages: [{page, text, text_raw, has_text, image}]}`.
- **Save extracted images alongside results.** Even though the API doesn't need saved images, store them for spot-checking and archival. Extract native images from PDFs the same way the HPC pipeline does.
- **Record the model name and provider.** Include the exact model identifier (e.g., `claude-sonnet-4-6`, `gpt-4.1`) in the output JSON so the provenance is clear.

### 7. Prompt Testing Workflow

- **Use API for rapid prompt iteration.** The feedback loop is: edit prompt → run 5 pages → inspect output → adjust. This takes minutes with an API, versus 15+ minutes of startup per iteration on HPC.
- **Test on a diverse sample.** Include: a text-heavy page, a text-sparse page, a blank/illustration page, a page with mixed scripts, and a page with tables or unusual layout. Five pages covering these types is a practical minimum.
- **Compare output across providers.** Run the same 5 pages through Claude, GPT, and (if cost-sensitive) Gemini. Differences in output reveal prompt weaknesses — a good prompt produces consistent results across models.
- **Once the prompt is stable, switch to HPC for bulk.** The API test phase typically costs $1-5 and saves hours of HPC time that would be wasted on prompt debugging.

## Quality Checks

- [ ] **Cost estimated before starting:** Per-page cost measured on a 10-page sample, total cost calculated
- [ ] **Provider chosen deliberately:** Selection based on quality needs, budget, and rate limits — not default
- [ ] **Retry logic implemented:** Exponential backoff on rate-limit errors, max 5 attempts per page
- [ ] **Resume capability built in:** Existing output detected and skipped on re-run
- [ ] **Results saved incrementally:** Output written per-PDF, not accumulated in memory until completion
- [ ] **Output format matches HPC pipeline:** Same `results_raw.json` schema for downstream compatibility
- [ ] **Images saved for spot-checking:** Native PDF images extracted and stored alongside OCR results
- [ ] **Model provenance recorded:** Exact model identifier stored in output JSON
- [ ] **Prompt tested on diverse sample:** At least 5 pages covering text-heavy, sparse, blank, mixed-script, and layout variations
- [ ] **Rate limits respected:** No burst patterns that trigger provider throttling
