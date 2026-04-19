# Sources & Bibliography

The instructions within these skills are drawn from the following sources, organized by topic area. Sources may appear in multiple subsections when they are relevant to more than one skill area.

---

## Digitization Standards & OCR Methodology

Baseline standards and long-form methodology for OCR of cultural-heritage and research materials:

* **Federal Agencies Digital Guidelines Initiative (FADGI).** (2023). *Technical Guidelines for Digitizing Cultural Heritage Materials* (3rd ed.). Still Image Working Group. Available at digitizationguidelines.gov.
* **Rieger, O. Y.** (2008). *Preservation in the Age of Large-Scale Digitization: A White Paper*. Council on Library and Information Resources (CLIR).
* **University of Pittsburgh Library System.** *OCR Best Practices*. Digital Scholarship Services. pitt.libguides.com.
* **IMPACT Centre of Competence.** *Recommendations for OCR and Text Recognition Projects*. digitisation.eu.
* **Smith, R.** (2007). "An Overview of the Tesseract OCR Engine." *International Conference on Document Analysis and Recognition*.

## Vision-Language Model OCR

Technical specifications and research on the VLMs used in the pipelines:

* **Bai, J., Bai, S., Chu, Y., et al.** (2023). "Qwen-VL: A Versatile Vision-Language Model for Understanding, Localization, Text Reading, and Beyond." *arXiv* preprint arXiv:2308.12966.
* **Qwen Team.** (2024). *Qwen3-VL Technical Report*. Alibaba Cloud. Available via qwenlm.github.io.
* **Qwen Team.** (2025). *Qwen3.5-VL and A3B Mixture-of-Experts Models*. Model cards on HuggingFace (`Qwen/Qwen3.5-35B-A3B`, `Qwen/Qwen3.5-35B-A3B-GPTQ-Int4`).
* **Chen, Z., Wu, J., Wang, W., et al.** (2024). "InternVL: Scaling up Vision Foundation Models and Aligning for Generic Visual-Linguistic Tasks." *CVPR*.
* **Yao, Y., Yu, T., Zhang, A., et al.** (2024). "MiniCPM-V: A GPT-4V Level MLLM on Your Phone." *arXiv* preprint arXiv:2408.01800.
* **Liu, C., Wei, H., Chen, J., et al.** (2024). "DeepSeek-OCR: Contexts Optical Compression." DeepSeek-AI model card and paper.
* **OCRBench:** Liu, Y., Li, Z., Huang, M., et al. (2024). "OCRBench: On the Hidden Mystery of OCR in Large Multimodal Models." *Science China Information Sciences*. OCRBench leaderboard at ocrbench.github.io.

## Inference Infrastructure

Tools and techniques for running models locally and at scale:

* **Kwon, W., Li, Z., Zhuang, S., et al.** (2023). "Efficient Memory Management for Large Language Model Serving with PagedAttention." *Proceedings of the 29th Symposium on Operating Systems Principles (SOSP)*.
* **vLLM Project.** *vLLM Documentation*. docs.vllm.ai. Covers the OpenAI-compatible API, quantization backends (including `gptq_marlin`), and deployment patterns.
* **HuggingFace.** *Transformers Documentation*. huggingface.co/docs/transformers. Covers `AutoModelForImageTextToText`, device maps, and generation interfaces.
* **Dettmers, T., Lewis, M., Shleifer, S., & Zettlemoyer, L.** (2022). "LLM.int8(): 8-bit Matrix Multiplication for Transformers at Scale." *NeurIPS*.
* **Dettmers, T., Pagnoni, A., Holtzman, A., & Zettlemoyer, L.** (2023). "QLoRA: Efficient Finetuning of Quantized LLMs." *NeurIPS*. Source of the NF4 quantization format used via `bitsandbytes`.
* **Frantar, E., Ashkboos, S., Hoefler, T., & Alistarh, D.** (2023). "GPTQ: Accurate Post-Training Quantization for Generative Pre-trained Transformers." *ICLR*.
* **Dao, T.** (2023). "FlashAttention-2: Faster Attention with Better Parallelism and Work Partitioning." *arXiv* preprint arXiv:2307.08691.
* **bitsandbytes GitHub issue #1849.** MoE incompatibility with NF4 quantization on transformers v5 — documented source for the GPTQ-via-vLLM routing in `hf-transformers-ocr`.

## HPC & SLURM

Scheduling and cluster operations:

* **Yoo, A. B., Jette, M. A., & Grondona, M.** (2003). "SLURM: Simple Linux Utility for Resource Management." *Job Scheduling Strategies for Parallel Processing (JSSPP)*, Springer LNCS 2862.
* **SchedMD.** *SLURM Workload Manager Documentation*. slurm.schedmd.com. Covers partitions, `sbatch`, `squeue`, `srun --overlap`, and resource specifications.
* **ALICE HPC (Leiden University).** *ALICE User Documentation*. Covers ZFS storage, GPU partitions (`gpu-short`, `gpu_lucdh`, `gpu-a100-80g`), and offline-node constraints.

## Cloud APIs for OCR

Provider documentation for the API-based path:

* **Anthropic.** *Claude API Documentation*. docs.claude.com. Covers vision inputs, structured outputs, rate limits, and the official Python SDK (`anthropic`).
* **OpenAI.** *OpenAI API Documentation*. platform.openai.com/docs. Covers vision via chat completions, the Python SDK (`openai`), and rate-limit handling. The same client pattern works with vLLM's OpenAI-compatible endpoint.
* **Google DeepMind.** *Gemini API Documentation*. ai.google.dev/gemini-api. Covers Gemini 2.5 Flash for cost-sensitive bulk OCR.

## PDF Processing

Libraries for extracting images and text from PDFs:

* **PyMuPDF / MuPDF.** *PyMuPDF Documentation*. pymupdf.readthedocs.io. Covers `Document`, `Page.get_images()`, `Page.get_text()`, and rendering. Primary library for the inventory and image-extraction stages.
* **pdfplumber.** *pdfplumber Documentation*. github.com/jsvine/pdfplumber. Useful for layout-aware text extraction when born-digital PDFs have selectable text.

## Unicode & Filesystem Encoding

The silent-failure class that hits Korean, Japanese, and accented-language corpora:

* **Unicode Consortium.** *Unicode Normalization Forms* (UAX #15). unicode.org/reports/tr15. Covers NFC, NFD, NFKC, NFKD. Essential reading for understanding the HFS+/APFS NFD issue.
* **Apple Developer Documentation.** *File System Programming Guide*. Covers HFS+/APFS filename encoding behavior and why NFC normalization is required before regex matching.
* **Python Documentation.** `unicodedata.normalize()`. docs.python.org/3/library/unicodedata.html.

## Analysis Tool Compatibility

Targets for corpus output formats:

* **Demšar, J., Curk, T., Erjavec, A., et al.** (2013). "Orange: Data Mining Toolbox in Python." *Journal of Machine Learning Research*, 14, 2349–2353.
* **Orange Data Mining.** *Orange Documentation*. orangedatamining.com/widget-catalog. Covers the text-mining add-on, word cloud widget, and CSV import requirements.
* **Silge, J., & Robinson, D.** (2017). *Text Mining with R: A Tidy Approach*. O'Reilly. Available online at tidytextmining.com.
* **Roberts, M. E., Stewart, B. M., & Tingley, D.** (2019). "stm: An R Package for Structural Topic Models." *Journal of Statistical Software*, 91(2).
* **McKinney, W.** (2010). "Data Structures for Statistical Computing in Python." *Proceedings of the 9th Python in Science Conference*. Source reference for `pandas`.

## Open Science & Skill Authoring

Conventions followed across the skill set:

* **Anthropic.** *Claude Agent Skills: Best Practices*. platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices. Reference for frontmatter structure, trigger-rich descriptions, and progressive disclosure.
* **open-science-skills project.** *SOURCES.md and CLAUDE.md conventions.* Referenced at `resources/open-science-skills/` in this monorepo. The bibliography format, checklist-at-end pattern, and "use when" trigger phrasing follow that project's conventions.

---

*Last updated: 2026-04-19. When adding new citations, prefer primary sources (papers, documentation) over secondary write-ups; include a DOI or stable URL where available.*
