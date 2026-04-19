# Wizard Output: The Starter Kit

What the wizard renders after a student answers the 6 questions in `QUESTIONS.md`. The wizard is a static page; this spec defines the structure of its output card, and the rendered HTML must match it. Three concrete examples at the bottom show what the card looks like for the three canonical routing outcomes.

**Design principles**

- **The paste-into-Claude-Code prompt is the centerpiece.** Everything else (reading list, files, commands) supports the student once they're in the AI-agent conversation. The wizard bootstraps the conversation; it does not replace it.
- **No secrets, no execution, no state.** Static page. All user inputs stay client-side. The `mailto:` escalation is the only outbound path.
- **All three compute paths are first-class.** API, ALICE, local GPU. The card structure is identical across paths; only the contents differ.

---

## Card structure

The rendered page has six sections, in order:

### § 1. Header
```
Recommended path: {API | ALICE | local GPU}
Corpus scale:    {N} pages across {M} documents
Est. cost:       {$range}  (or "free" for HPC/local)
Est. time:       {range}
[ESCALATION badge, if any trigger fired]
```

### § 2. Read first
A numbered reading list of skill files. Always starts with `corpus-from-pdfs` and `corpus-metadata-design`. Then one path-specific skill:

| Path          | Adds                   |
|---------------|------------------------|
| API           | `api-ocr-runner`       |
| ALICE         | `alice-vllm-deploy`    |
| Local GPU     | `hf-transformers-ocr`  |

Each item links to the skill's `.md` on the Pages site. Checkboxes are decorative (client-side only, not persisted).

### § 3. Paste this into Claude Code (or Codex)
A pre-filled paragraph the student copies into the AI-agent chat. Includes:

- Corpus description (from their wizard answers)
- Compute access
- Analysis target
- Explicit request: "Walk me through the `corpus-from-pdfs` pipeline and help me set up the OCR and assembly stages."

Two copy buttons: **Copy for Claude Code** and **Copy for Codex**. The content is the same; labels vary slightly so students know both agents work.

### § 4. Files to copy
A checklist of templates to copy into the student's project directory. Each entry is a link plus a short note on what to fill in:

```
□ templates/prompts.py.template  →  prompts.py    (fill Pattern {A|B} placeholders)
□ templates/manifest.csv.example  →  reference only, not copied
□ templates/run_ocr.slurm.template → run_ocr.slurm  (ALICE path only)
```

### § 5. Commands (pre-filled with your answers)
Four to six shell commands, in order, with the student's answers substituted where possible. Example placeholders use `<...>`; fields like `--pages` are already numeric from the wizard.

### § 6. Stuck? Escalate.
A single button: `mailto:stevencdenney@gmail.com` with subject and body pre-filled from the wizard state. Always visible; highlighted when an escalation trigger fired.

---

## Example outputs

Three canonical routing outcomes at student scale (~75 articles). These are the scenario demos for `examples/`.

---

### Example A — Small-scale API (default student case)

**Wizard answers**
- Pages: 750 (75 articles × ~10 pages)
- Compute: laptop only
- Language: English
- Doctype: journal articles
- Analysis: Python / pandas
- Constraints: modest budget, flexible timeline

**Rendered card**

```
Recommended path: API
Corpus scale:    ~750 pages across 75 articles
Est. cost:       $7.50 – $15.00 on Claude Sonnet (or ~$3 on Gemini Flash)
Est. time:       2–3 hours sustained API calls + ~10 min of local stages
```

**§ 2. Read first**
1. `corpus-from-pdfs` — end-to-end framing
2. `corpus-metadata-design` — schema for your CSV / JSON output
3. `api-ocr-runner` — cost estimation, rate limits, resume logic

**§ 3. Paste this into Claude Code**
> I have 75 English journal articles (roughly 750 pages). I want to extract the text via a cloud API (Claude Sonnet) and analyze it in Python with pandas. I'm on a laptop — no GPU, no HPC. Walk me through the `corpus-from-pdfs` pipeline and help me set up the OCR client and assembly stages. Start by asking about my analysis question so we can design the metadata schema before building.

**§ 4. Files to copy**
- `templates/prompts.py.template` → `prompts.py` (fill Pattern A, English, no character enumeration needed)

**§ 5. Commands**
```
python3 scripts/inventory_builder.py --pdf-dir ./articles --output manifest.csv
python3 scripts/cost_estimator.py --pages 750 --compare
# OCR step — client script written with Claude Code's help, sends base64
# page images to the Claude API, writes results_raw.json per article
python3 scripts/corpus_assembler.py --ocr-dir ocr_output --manifest manifest.csv --output corpus/
```

---

### Example B — Small-scale ALICE (HPC path, same scale)

**Wizard answers**
- Pages: 800 (75 historical newspapers × ~10 pages)
- Compute: ALICE account
- Language: Polish (historical orthography)
- Doctype: newspaper scans
- Analysis: R / stm
- Constraints: no budget, flexible timeline

**Rendered card**

```
Recommended path: ALICE
Corpus scale:    ~800 pages across 75 documents
Est. cost:       free (HPC compute)
Est. time:       ~13 min cold start + ~90 min OCR + ~10 min post-processing
```

**§ 2. Read first**
1. `corpus-from-pdfs` — end-to-end framing
2. `corpus-metadata-design` — schema for R `stm`
3. `alice-vllm-deploy` — SLURM, cold-start timing, SSH discipline

**§ 3. Paste this into Claude Code**
> I have 75 Polish historical newspaper scans (roughly 800 pages). The text uses Polish diacritics (ą, ć, ę, ł, ń, ó, ś, ź, ż) and occasional pre-reform spelling. I have an ALICE account and want to run vLLM on `gpu_lucdh`. My analysis target is `stm` in R. Walk me through the `corpus-from-pdfs` pipeline. Start by helping me fill in the SLURM template and the Polish prompt. Then help me deploy and monitor the job.

**§ 4. Files to copy**
- `templates/prompts.py.template` → `prompts.py` (fill Pattern A, Polish diacritics enumerated)
- `templates/run_ocr.slurm.template` → `run_ocr.slurm` (fill project name, `gpu_lucdh`, model)

**§ 5. Commands**
```
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

### Example C — Small-scale local GPU

**Wizard answers**
- Pages: 750
- Compute: local GPU (RTX 4090, 24 GB)
- Language: English
- Doctype: journal articles
- Analysis: Python / spaCy
- Constraints: no budget, fast iteration

**Rendered card**

```
Recommended path: Local GPU
Corpus scale:    ~750 pages across 75 articles
Est. cost:       free (your electricity)
Est. time:       ~5 min model load + ~3 hours sequential OCR + ~10 min assembly
```

**§ 2. Read first**
1. `corpus-from-pdfs` — end-to-end framing
2. `corpus-metadata-design` — schema for pandas / spaCy
3. `hf-transformers-ocr` — BnB NF4 loading, inference patterns, cache hygiene

**§ 3. Paste this into Claude Code**
> I have 75 English journal articles (roughly 750 pages) and a local RTX 4090 (24 GB). I want to use Qwen3-VL-32B with BitsAndBytes NF4 quantization. Analysis target is spaCy in Python. Walk me through the `corpus-from-pdfs` pipeline. Help me set up the model loading script, run OCR, and assemble the corpus. Keep CUDA memory tidy — clear cache every 5–10 pages.

**§ 4. Files to copy**
- `templates/prompts.py.template` → `prompts.py` (fill Pattern A, English)

**§ 5. Commands**
```
python3 scripts/inventory_builder.py --pdf-dir ./articles --output manifest.csv
# OCR step — HF Transformers client (built with Claude Code's help):
# loads Qwen3-VL-32B with BnB NF4, processes each page, writes results_raw.json
python3 scripts/corpus_assembler.py --ocr-dir ocr_output --manifest manifest.csv --output corpus/
```

---

## Cross-cutting notes

- **Codex variant.** The "Paste this into Claude Code" prompt works for Codex unchanged. The Copy-for-Codex button exists only to make the path obvious to non-Claude-Code users. Don't introduce different wording — the prompt should be agent-agnostic.
- **The OCR step is always guided, never copy-pasted.** The commands in § 5 omit the OCR client invocation for API and local-GPU paths deliberately: the client is built inside Claude Code, with the agent reading the appropriate skill and helping the student write the ~50 lines of glue. Scripting this as a one-liner would defeat the teaching purpose.
- **Escalation triggers (from `QUESTIONS.md`) still apply.** When one fires, § 6 is highlighted and the § 3 prompt gains a suffix: "I may need help from Steven — I've sent him the wizard output."
- **No analytics.** The wizard does not POST user answers anywhere. The `mailto:` is the only way answers leave the browser, and only when the student clicks.
