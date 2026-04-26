---
title: "Small corpus on a local GPU"
---

# Scenario: Small corpus on a local GPU

**Who this is for:** a student or staff member with a home machine and a consumer NVIDIA GPU. 8–12 GB VRAM is plenty for small-to-medium student projects with an 8B vision-language model. No cloud costs, no HPC queue.

---

## The situation

A grad student studying parliamentary speeches has 75 English-language committee reports (~750 pages) from a government portal. Hardware: RTX 3060 with 12 GB VRAM. Analysis target: `spaCy` for named-entity extraction, then `pandas` for downstream counts.

## Wizard answers

| Question | Answer |
|----------|--------|
| How many pages? | 501–1,000 |
| What compute? | Local GPU with less than 16 GB |
| Languages/scripts? | Latin only |
| Document type? | Reports |
| What software? | Python |
| Resource constraints? | No budget; fast iteration wanted |

**Route:** Local GPU path. `hf-transformers-ocr` covers BnB NF4 loading, inference patterns, cache hygiene.

---

## Starter kit

```
Recommended path: Local GPU
Corpus scale:    roughly 750 pages
Est. cost:       free (your electricity)
Est. time:       ~2 min model load + ~100 min sequential OCR + ~10 min assembly
```

**Read first**
1. `corpus-from-pdfs` — end-to-end framing
2. `corpus-metadata-design` — schema for pandas / spaCy
3. `hf-transformers-ocr` — BnB NF4 loading, inference, cache hygiene

**Paste into Claude Code / Codex**
> I have 75 English committee reports (roughly 750 pages) and a local RTX 3060 with 12 GB VRAM. I want to use Qwen3-VL-8B-Instruct with BitsAndBytes NF4 quantization. Analysis target is spaCy in Python. Walk me through the `corpus-from-pdfs` pipeline. Help me set up the model loading script, run OCR, and assemble the corpus. Keep CUDA memory tidy — clear cache every 5–10 pages.

**Or launch a fresh session directly**

```bash
claude "I have 75 English committee reports (roughly 750 pages) and a local RTX 3060 with 12 GB VRAM. I want to use Qwen3-VL-8B-Instruct with BitsAndBytes NF4 quantization. Analysis target is spaCy in Python. Walk me through the corpus-from-pdfs pipeline."
```

**Files to copy**
- `templates/prompts.py.template` → `prompts.py` (Pattern A, English, no character enumeration needed)

**Commands (pre-filled)**
```bash
python3 scripts/inventory_builder.py --source-dir ./reports --output manifest.csv
# OCR step — HF Transformers client built with Claude Code:
#   loads Qwen3-VL-8B with BnB NF4, processes each page,
#   writes ocr_output/<pdf_id>/results_raw.json
python3 scripts/corpus_assembler.py --ocr-dir ocr_output --manifest manifest.csv --output corpus/
```

---

## Walkthrough

> **Note:** runs on any machine with a 8 GB+ CUDA GPU. At ~8 s/page for an 8B model on a 12 GB consumer card, budget roughly 100 minutes for 750 pages.

### Step 1: Inventory (local)

```bash
python3 scripts/inventory_builder.py --source-dir ./reports --output manifest.csv
```

```
Found 75 PDFs under /home/you/reports
Manifest: manifest.csv
  Total PDFs:     75
  Total pages:    748
```

### Step 2: Fill `prompts.py`

Pattern A, English. No character enumeration needed — English has no tricky diacritics.

```python
PROMPTS = {
    "english": (
        "Extract all text from this document image. "
        "Transcribe every character exactly as it appears. "
        "Output in markdown format preserving headings, paragraphs, "
        "footnotes, and tables. "
        "If the page has no text at all, output only: [NO_TEXT]. "
        "Do not translate or interpret the text."
    ),
}
LANGUAGE_PROMPT_MAP = {"english": "english"}
```

### Step 3: Build the HF Transformers client (inside Claude Code)

The student pastes the wizard's prompt. Claude Code reads `hf-transformers-ocr` and helps write a ~100-line `hf_ocr.py` script. Key patterns the agent applies from the skill:

- `AutoProcessor.from_pretrained("Qwen/Qwen3-VL-8B-Instruct", ...)` with `min_pixels` / `max_pixels` set
- `AutoModelForImageTextToText.from_pretrained(...)` with `BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4")`
- `attn_implementation="flash_attention_2"` with fall-back to `"eager"`
- `enable_thinking=False` and `do_sample=False` on generation
- `torch.cuda.empty_cache()` every 5–10 pages (12 GB fills up fast)
- Native image extraction via PyMuPDF's `page.get_images()`; rasterize for VLM at 200 DPI
- Resumable: skip PDFs whose `results_raw.json` already exists

A trimmed version of the inference loop:

```python
def ocr_page(model, processor, image_path, prompt, max_new_tokens=8192):
    messages = [{"role": "user", "content": [
        {"type": "image", "image": str(image_path)},
        {"type": "text", "text": prompt},
    ]}]
    inputs = processor.apply_chat_template(
        messages, tokenize=True, add_generation_prompt=True,
        return_dict=True, return_tensors="pt", enable_thinking=False,
    ).to(model.device)
    with torch.no_grad():
        output_ids = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
    trimmed = [out[len(inp):] for inp, out in zip(inputs.input_ids, output_ids)]
    return processor.batch_decode(trimmed, skip_special_tokens=True)[0].strip()
```

### Step 4: Run

```bash
python3 hf_ocr.py --manifest manifest.csv --output ocr_output/
```

Expected timing on RTX 3060 (12 GB):

```
Loading Qwen/Qwen3-VL-8B-Instruct (NF4)... 1m 48s
Processing aggr_committee_2019_001.pdf (12 pages)...
  page 0: 8s  page 1: 7s  page 2: 9s  ...
[cache cleared]
Processing aggr_committee_2019_002.pdf (9 pages)...
...
```

~8 s/page × 748 pages ≈ **100 min**. Laptop can sleep during this; the run continues. If the student closes their terminal, they lose the run unless they used `tmux` or `nohup` — Claude Code will have suggested one of those.

### Step 5: Assemble

```bash
python3 scripts/corpus_assembler.py \
    --ocr-dir ocr_output \
    --manifest manifest.csv \
    --output corpus/
```

```
  corpus: 748 pages total, 745 with text
    JSON: corpus/corpus.json
    CSV : corpus/corpus.csv (745 rows)
  Text density:   99.6%
```

### Step 6: Analyze

```python
import pandas as pd
import spacy

nlp = spacy.load("en_core_web_trf")
df = pd.read_csv("corpus/corpus.csv")

entities = []
for _, row in df.iterrows():
    for ent in nlp(row["text"]).ents:
        entities.append({"pdf_id": row["pdf_id"], "page": row["page"],
                         "text": ent.text, "label": ent.label_})
ents_df = pd.DataFrame(entities)
```

---

## What would change at a different scale or hardware?

- **Less than 8 GB VRAM:** even the smallest VLMs struggle at useful speed. Use the API path instead (see `small_api.html`).
- **16 GB+ (RTX 4070 Ti Super, 4080):** step up to a 13B model for better accuracy on dense or stylized text. Still fits at 4-bit.
- **24 GB+ (RTX 4090):** the 32B tier opens up — best accuracy for consumer-grade work, especially on multi-column or historical text.
- **MoE model wanted (Qwen3.5-35B-A3B):** BnB NF4 is incompatible with MoE on transformers v5. Use vLLM + GPTQ via ALICE instead — `hf-transformers-ocr` spells this out.
- **Larger corpus (>5k pages):** runtime scales linearly. ~11 hours for 5k pages on a 3060. Consider whether the API is actually simpler at that point.
- **Non-Latin / historical script:** add character enumeration to Pattern A as in the ALICE scenario.
