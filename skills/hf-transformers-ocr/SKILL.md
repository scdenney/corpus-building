---
name: hf-transformers-ocr
description: Guide direct HuggingFace Transformers model loading for VLM-based OCR on GPU. Covers model selection, quantization strategies (BitsAndBytes NF4, GPTQ), memory management, and when direct loading is appropriate versus vLLM serving. Use when (1) running VLM OCR on a local GPU or single HPC allocation, (2) choosing between BitsAndBytes and GPTQ quantization, (3) loading a vision-language model for the first time with transformers, (4) debugging GPU memory issues during model loading, (5) processing a small-to-medium corpus without vLLM infrastructure, (6) needing maximum flexibility over generation parameters, or (7) comparing inference approaches for a methods paper.
argument-hint: "[describe your model, GPU, and corpus size]"
---

# Direct HuggingFace Transformers OCR

## Instructions

### 1. When to Use Direct Loading vs. vLLM

- **Use direct transformers loading when:** (a) vLLM has compatibility issues with your model architecture, (b) you need fine-grained control over generation (custom stopping criteria, logit manipulation), (c) your corpus is small enough that startup overhead doesn't matter, (d) you're developing and testing locally before deploying, or (e) you're running a model comparison study where each model loads differently.
- **Use vLLM when:** (a) your model is supported by vLLM's architecture list, (b) you're processing >500 pages (amortizes startup cost), (c) you want the OpenAI-compatible API for client simplicity, or (d) you're using GPTQ-quantized MoE models (vLLM's `gptq_marlin` backend handles these; direct BnB loading does not).
- **The pseudohistory project used direct transformers loading** with Qwen3-VL-32B-Instruct and BitsAndBytes NF4 quantization. This worked because Qwen3-VL-32B is a dense model (not MoE). The later upgrade to Qwen3.5-35B-A3B (MoE) required switching to vLLM because BnB NF4 is incompatible with MoE on transformers v5.

### 2. Model Loading Pattern

```python
from transformers import AutoModelForImageTextToText, AutoProcessor, BitsAndBytesConfig

# Processor handles image tokenization
processor = AutoProcessor.from_pretrained(
    model_name,
    min_pixels=256 * 28 * 28,
    max_pixels=1280 * 28 * 28,
)

# Model with quantization
model = AutoModelForImageTextToText.from_pretrained(
    model_name,
    torch_dtype=torch.bfloat16,
    attn_implementation="flash_attention_2",  # or "eager" as fallback
    device_map="auto",
    quantization_config=BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_quant_type="nf4",
    ),
)
model = model.eval()
```

- **Use `AutoModelForImageTextToText`** to auto-detect the correct model class. Do not hardcode `Qwen3VLForConditionalGeneration` — it breaks when switching models.
- **Always try flash attention first, fall back to eager.** `flash_attention_2` is faster but requires compatible hardware and the `flash-attn` package. Wrap in try/except and fall back to `"eager"` on failure.
- **`device_map="auto"`** lets transformers handle multi-GPU placement and CPU offloading automatically. Do not manually assign devices unless you have a specific reason.

### 3. Quantization Strategy

- **Match model size to VRAM.** Consumer GPUs are the common case — not everyone has an A100. At 4-bit quantization: an 8B VLM (Qwen3-VL-8B-Instruct, MiniCPM-V 2.6) fits on 8–12 GB cards with headroom for KV cache. A 13B-class model needs 16 GB+ (RTX 4070 Ti Super, 4080). A 32B dense model needs 24 GB+ (RTX 4090, A6000). Only reach for 32B if accuracy actually demands it.
- **BitsAndBytes NF4 (4-bit):** Best for dense models (Qwen3-VL-8B, Qwen3-VL-32B, InternVL2.5, MiniCPM-V). Reduces VRAM by ~4x. Accuracy loss is ~2-5% on OCR tasks. Requires `bitsandbytes` package.
- **GPTQ (4-bit, pre-quantized):** Best for MoE models where BnB fails. Requires GPTQ-specific model weights from HuggingFace (e.g., `Qwen/Qwen3.5-35B-A3B-GPTQ-Int4`). Works with vLLM's `gptq_marlin` backend but may have compilation issues with direct transformers loading.
- **No quantization (full precision):** Requires 2-4x more VRAM (32B model needs ~64GB). Use only when accuracy is critical and you have the hardware (2x A100, or A100 80GB for 32B models).
- **Critical: BnB NF4 + MoE = broken.** BitsAndBytes 4-bit quantization is incompatible with Mixture-of-Experts models on transformers v5 (bitsandbytes issue #1849). This includes Qwen3.5-35B-A3B and similar MoE architectures. Use GPTQ via vLLM instead.

### 4. Inference Pattern

```python
def ocr_page(model, processor, image_path, prompt, max_new_tokens=8192):
    messages = [{
        "role": "user",
        "content": [
            {"type": "image", "image": str(image_path)},
            {"type": "text", "text": prompt},
        ],
    }]
    
    inputs = processor.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_dict=True,
        return_tensors="pt",
        enable_thinking=False,  # Disable chain-of-thought for OCR
    )
    inputs = inputs.to(model.device)
    
    with torch.no_grad():
        output_ids = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
    
    # Trim input tokens
    generated_ids = [out[len(inp):] for inp, out in zip(inputs.input_ids, output_ids)]
    return processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()
```

- **Disable thinking mode.** `enable_thinking=False` prevents Qwen3+ models from generating `<think>` blocks, which add latency and fabricate rather than transcribe.
- **Use greedy decoding.** `do_sample=False` ensures deterministic, reproducible output. Sampling introduces variance that hurts OCR consistency.
- **Set `max_new_tokens` appropriately.** 8192 for dense text pages (textbooks), 4096 for sparse pages (comics). Too low truncates output; too high wastes compute on the padding.
- **Clear CUDA cache periodically.** Call `torch.cuda.empty_cache()` every 5-10 pages to prevent memory fragmentation. This adds negligible overhead but prevents OOM errors on long runs.

### 5. Image Handling

- **Extract native images from scanned PDFs.** Use PyMuPDF's `page.get_images()` to extract embedded images at their original resolution (typically 300 DPI for scans). This preserves quality without re-encoding.
- **Rasterize for VLM input.** The VLM needs a file path or PIL Image. Rasterize at 200 DPI for the model input — this is sufficient for OCR and keeps input token counts manageable. Do not use the 300 DPI archival image for VLM input.
- **Save a temporary file for the VLM.** Most VLM processors expect a file path. Save the rasterized image to a temp file, process it, then delete. Do not accumulate temp files.

### 6. LLM-Based Post-OCR Cleanup (Optional Stage)

The pseudohistory project added a text-only LLM cleanup stage after VLM OCR:

- **Use a small model (7-8B parameters).** Text correction doesn't need vision. Qwen3-8B at 4-bit uses ~4GB VRAM and processes pages in 2-3 seconds.
- **Write tight correction prompts.** "Fix clear OCR mistakes only: wrong characters, broken words, garbled punctuation. Do not translate, modernize, or add anything."
- **Track changes with edit distance.** Compute Levenshtein distance per page. Flag pages where >10% of characters changed — high change ratios may indicate hallucination rather than correction.
- **Pilot-test per language before committing.** LLM cleanup helps some languages and hurts others. The GEI project deferred this stage pending evaluation. See the `post-ocr-cleanup` skill for detailed methodology.

### 7. SLURM Integration

- **Structure as a single SLURM job per PDF.** Load model once, process all pages, save results. This amortizes the 2-5 minute model loading time across many pages.
- **For batch processing, chain jobs.** Use `sbatch --dependency=afterany:$PREV_JOB_ID` to process PDFs sequentially. Each job loads the model fresh (no model persistence across jobs).
- **Memory requirements:** 4-bit quantized 32B model needs ~20GB VRAM + ~8GB for KV cache during generation. Request a 48GB+ GPU (A40 or A100).

## Quality Checks

- [ ] **Model architecture compatible with quantization:** Dense models use BnB NF4; MoE models use GPTQ via vLLM (NOT direct BnB loading)
- [ ] **Flash attention attempted with fallback:** `flash_attention_2` tried first, `eager` as fallback
- [ ] **Thinking mode disabled:** `enable_thinking=False` set for OCR tasks
- [ ] **Greedy decoding used:** `do_sample=False` for deterministic output
- [ ] **max_new_tokens appropriate:** Set based on expected text density (4096-8192)
- [ ] **CUDA cache cleared periodically:** `torch.cuda.empty_cache()` every 5-10 pages
- [ ] **Native images extracted:** Embedded images used rather than rasterized from PDF
- [ ] **VLM input at appropriate DPI:** 200 DPI for VLM input, native resolution for archival
- [ ] **Temp files cleaned up:** Temporary rasterized images deleted after processing
- [ ] **Output format consistent:** Results saved in same JSON schema as vLLM and API pipelines
