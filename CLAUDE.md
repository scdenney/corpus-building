# Corpus Building Skills & Tooling

Standalone skills, scripts, and teaching materials for building text corpora from PDFs using VLMs on HPC infrastructure. Developed by Steven Denney.

## What We're Building

A set of **Claude Code skills** and **companion shell scripts** that walk students and researchers through the process of building a text corpus from PDF documents using vision-language models. The skills are designed to be:

1. **Standalone**: each skill works independently as a `.md` file or shell script
2. **Teaching-oriented**: walks users through decisions, not just executes steps
3. **Modular**: mix and match for different corpus types (scanned books, comics, newspapers, etc.)
4. **HPC-ready**: knows how to work with SLURM, vLLM, and GPU scheduling
5. **Installable**: follows the open-science-skills plugin format for Claude Code integration

## Lessons Driving This

### From GEI Textbooks (`/research/gei_textbooks/`)
- **vLLM is the working path** for Qwen3.5-35B-A3B on ALICE. Direct transformers loading with BnB/GPTQ has compatibility issues. vLLM with `gptq_marlin` works reliably.
- **Two-phase SLURM pattern**: start vLLM server in background → run client script against it → shut down. Health check loop with 900s timeout for cold starts.
- **Multi-stage pipeline**: OCR → diagnostics → rule fixes → assembly. Each stage is a separate script with structured JSON I/O.
- **Tranche/gate strategy**: test small batch, human-evaluate, then bulk. Prevents wasting GPU-hours on broken prompts.
- **Language-specific prompts**: explicit character set enumeration in prompts matters enormously for non-Latin scripts.
- **Cold start from ZFS takes ~13 minutes** on A100: Python imports (4 min) → config (2 min) → weight loading (2.5 min) → torch.compile (2.5 min) → warmup (1.5 min) → CUDA graph capture (10s). Subsequent runs faster due to cached compilation.

### From Webtoon Thesis (`/Thesis/`)
- **Comic OCR needs type classification**: dialogue, narration, SFX are linguistically distinct. VLM can classify during extraction with tag-based prompts.
- **Naver UI detection**: page 0 of Korean webtoon PDFs has selectable nav text; auto-detect and skip via PyMuPDF.
- **macOS NFD normalization**: Korean filenames decompose on HFS+/APFS; must NFC-normalize before regex matching.
- **Manifest-driven pipelines**: a CSV manifest is the single source of truth linking PDFs to metadata. Generate ALICE-path variants for deployment.
- **Orange Data Mining compatibility**: CSV must be tidy, small, text-only rows. Split columns (dialogue/narration/sfx) plus combined text column gives researchers both filtered and full-text options.

### From open-science-skills (`/resources/open-science-skills/`)
- **Skill format**: YAML frontmatter (name, description with trigger phrases, argument-hint) + procedural markdown body + quality checklist
- **Trigger-rich descriptions**: enumerate 4-8 "use when" scenarios for auto-invocation
- **Progressive disclosure**: instructions in skill, bibliography in SOURCES.md
- **Existing OCR skills**: `vlm-ocr-pipeline` (model selection, batch strategy, accuracy eval) and `post-ocr-cleanup` (LLM correction, rule fixes, diagnostics) already exist. The new skills complement these rather than duplicate them.

## Planned Skills

### 1. `corpus-from-pdfs`
**What it does**: Walks the user through the full journey from a folder of PDFs to a structured corpus (JSON + CSV). Covers: inventory building, metadata schema design, OCR approach selection (VLM vs. traditional vs. API), output format for their analysis tool (Orange, R, Python).

**Why it's needed**: The existing `vlm-ocr-pipeline` and `post-ocr-cleanup` skills cover the technical how, but students need help with the what and why — what metadata to track, how to structure the corpus for their specific analysis, which OCR approach fits their situation.

**Teaching angle**: Decision tree for OCR approach (Do you have GPU access? → How many pages? → What languages? → What's your budget?). Concrete examples from GEI textbooks and Webtoon projects.

### 2. `alice-vllm-deploy`
**What it does**: Guides deployment and execution of a vLLM-based OCR pipeline on ALICE HPC (or similar SLURM clusters). Covers: syncing code/data, verifying venv and model weights, SLURM job configuration, partition selection, monitoring, and troubleshooting.

**Why it's needed**: The gap between "I have a working script" and "it's running on the cluster" is where most students get stuck. SSH rules, ZFS paths, offline mode, venv management, job submission — all of this is tribal knowledge.

**Teaching angle**: Step-by-step walkthrough with checkpoints. "Before you submit, verify: (1) model weights cached, (2) venv has dependencies, (3) manifest paths are ALICE paths, (4) logs directory exists."

### 3. `corpus-metadata-design`
**What it does**: Helps design metadata schemas for text corpora. Covers: choosing the right granularity (document, page, paragraph, sentence), mandatory vs. optional fields, CSV vs. JSON tradeoffs, compatibility with analysis tools (Orange, R tidytext, Python pandas).

**Why it's needed**: Students often under-specify metadata (just filename + text) or over-engineer it. A good schema is the difference between a usable corpus and a pile of text files.

**Teaching angle**: Start from the analysis question ("What will you filter/group/compare?"), derive the schema backwards. Concrete examples for different corpus types.

### 4. `api-ocr-runner`
**What it does**: Guides OCR via cloud APIs (Claude, GPT, Gemini) as an alternative to HPC. Covers: cost estimation, provider selection, rate limiting, resume logic, when API makes sense vs. HPC.

**Why it's needed**: Not every student has ALICE access. For small corpora (<1000 pages), API is simpler and faster to set up. For testing prompts before HPC deployment, API gives immediate feedback.

**Teaching angle**: Cost calculator (pages × resolution → tokens → cost). Decision framework: API for prototyping and small corpora, HPC for bulk.

### 5. `hf-transformers-ocr`
**What it does**: Guides direct HuggingFace Transformers model loading for VLM OCR. Covers: model loading, BnB vs. GPTQ quantization, memory management, inference patterns, optional LLM post-correction stage.

**Why it's needed**: The pseudohistory project used this approach (Qwen3-VL-32B + BnB NF4) before the GEI project moved to vLLM. It's the right path for dense models, local GPU development, and when vLLM has compatibility issues. Students need to understand the tradeoffs.

**Teaching angle**: When direct loading works and when it doesn't (the BnB + MoE incompatibility). Code patterns for model loading, inference, and the optional LLM cleanup stage.

## Companion Scripts

Each skill may have companion shell scripts or Python scripts that implement the patterns described in the skill. These live alongside the skill files and are referenced from the skill content.

```
corpus_building/
├── CLAUDE.md                          # This file
├── skills/
│   ├── corpus-from-pdfs/
│   │   └── SKILL.md
│   ├── alice-vllm-deploy/
│   │   └── SKILL.md
│   ├── corpus-metadata-design/
│   │   └── SKILL.md
│   ├── api-ocr-runner/
│   │   └── SKILL.md
│   └── hf-transformers-ocr/
│       └── SKILL.md
├── scripts/
│   ├── inventory_builder.py           # Generic PDF inventory/manifest tool
│   ├── vllm_health_check.sh           # vLLM server readiness checker
│   ├── alice_deploy.sh                # Sync code + data to ALICE
│   ├── cost_estimator.py              # API cost calculator
│   └── corpus_assembler.py            # Generic JSON+CSV corpus assembly
├── templates/
│   ├── run_ocr.slurm.template         # SLURM job template (vLLM pattern)
│   ├── manifest.csv.example           # Example manifest format
│   └── prompts.py.template            # Prompt module template
├── SOURCES.md                         # Bibliography (follows open-science-skills pattern)
├── wizard/
│   └── QUESTIONS.md                   # Routing wizard question set + matrix
└── examples/
    ├── small_english_api.md           # Scenario demo: <500 pages, English, API path
    ├── historical_hpc.md              # Scenario demo: 10k pages, non-Latin script, ALICE
    └── comics_classification.md       # Scenario demo: manga/manhwa with type-classification
```

## Relationship to open-science-skills

These skills **complement** the existing `vlm-ocr-pipeline` and `post-ocr-cleanup` skills:

| Existing skill | Focus | New skill | Focus |
|---------------|-------|-----------|-------|
| `vlm-ocr-pipeline` | Technical OCR pipeline design | `corpus-from-pdfs` | End-to-end corpus building journey |
| `vlm-ocr-pipeline` | Model selection, batch strategy | `alice-vllm-deploy` | Practical HPC deployment |
| `post-ocr-cleanup` | Text cleanup methodology | `corpus-metadata-design` | Corpus structure and schema |
| — | — | `api-ocr-runner` | Cloud API alternative path |

When mature, these skills can be added to the open-science-skills plugin. For now, they develop independently here.

## Status

### Done
- [x] 6 skill SKILL.md files written (corpus-from-pdfs, source-file-extraction, alice-vllm-deploy, corpus-metadata-design, api-ocr-runner, hf-transformers-ocr)
- [x] Directory structure created (skills/, scripts/, templates/, examples/, wizard/)
- [x] CLAUDE.md with lessons from GEI, Webtoons, Pseudohistory, and open-science-skills
- [x] Wizard question set drafted (`wizard/QUESTIONS.md`) — 6 questions, routing matrix, escalation triggers
- [x] Delivery model decided: plugin as spine + thin static web wizard front door + escalation `mailto:` to Steven for hard cases (middle path)
- [x] **SOURCES.md** — Bibliography organized by topic (digitization standards, VLM OCR, inference infrastructure, HPC/SLURM, cloud APIs, PDF processing, Unicode, analysis tools, skill authoring)
- [x] **Templates** — `run_ocr.slurm.template` (parameterized two-phase vLLM pattern with `{{PLACEHOLDERS}}`), `manifest.csv.example` (annotated with `#`-comment header), `prompts.py.template` (two patterns: scanned text with character-set enumeration; structured output with type tags)
- [x] **Companion scripts** — `vllm_health_check.sh` (standalone /health poller), `cost_estimator.py` (ballpark API cost calculator), `inventory_builder.py` (generic PDF→manifest tool with PyMuPDF page counts and NFC normalization), `alice_deploy.sh` (rsync + manifest path rewriting), `corpus_assembler.py` (generic JSON+CSV assembly with optional tag parsing and `--group-by`)
- [x] **Starter-kit spec** — `wizard/STARTER_KIT.md` defines the six sections the wizard renders (header, read-first, paste-into-agent prompt, files, commands, escalation) and shows three worked routing outcomes
- [x] **Scenario demos** — `examples/small_api.md`, `examples/small_alice.md`, `examples/small_local_gpu.md`. Each: student-scale (~75 articles, ~750 pages), one routing path, narrative + commands + expected outputs + analysis snippet
- [x] **Static web wizard** — `index.html` + `wizard.js` + `wizard.css` at repo root. Six-question form, routing logic mirroring `QUESTIONS.md`, starter-kit card per path, copy buttons for prompt / commands, prefilled `mailto:` escalation. Ready for GitHub Pages (serve from root).

### Still To Build
- [ ] **Slash commands** — `commands/<skill-name>.md` files for plugin installation. Follow open-science-skills pattern.
- [ ] **Plugin config** — `plugin.json` for marketplace compatibility. Defer until skills are stable.
- [ ] **Review pass** — Audit all skills against Anthropic skill authoring best practices (https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices). Check trigger descriptions, progressive disclosure, citation density.
- [ ] **GitHub repo + Pages enablement** — Promote `corpus_building/` to its own GitHub repo, push, enable Pages on `main` (serve from root).
- [ ] **Integration with open-science-skills** — When ready, copy skills + commands into the plugin and update the existing `vlm-ocr-pipeline` and `post-ocr-cleanup` skills to cross-reference these new skills.

## Conventions

Follow open-science-skills patterns:
- **YAML frontmatter**: `name`, `description` (trigger-rich, 4-8 "use when" clauses), `argument-hint`
- **Procedural content**: numbered guidelines, not textbook definitions
- **Quality checklist**: checkbox items at the end of each skill
- **Citations**: Author (year) format, full references in SOURCES.md
- **No duplication**: reference existing skills rather than rewriting their content
