# Wizard Question Set

A routing wizard for the corpus-building skills. 6 questions → personalized starter kit (which skills to invoke, which template to copy, which script to run), or an escalation `mailto:` to Steven for hard cases.

**Cold entry**: users who just want to see what this produces can skip the wizard and open a [scenario demo](../examples/) — a walkthrough showing the starter-kit output for a representative project (small-corpus API, small ALICE, small local-GPU). One link at the top of the wizard page, not a second path through it.

**Design rule**: these questions must mirror the decision trees inside the skill files. If they drift, the wizard and plugin will recommend different things. Any change here triggers a skill review.

**Audience**: primarily students at Leiden University and similar; staff secondarily. Page ranges are calibrated to realistic student projects (a single source, maybe 50–200 documents), not multi-corpus research programs.

---

## Questions

### 1. How many pages total?
- Less than 100
- 101–500
- 501–1,000
- 1,001–5,000
- 5,001–10,000
- More than 10,000

*Scale dictates API vs. HPC. Anything under 5,000 is realistic on the API path; above that, HPC starts to dominate on cost.*

### 2. What compute do you have access to?
- ALICE account, ready to use
- LUCDH workstation access
- Different SLURM cluster (adaptation needed)
- Local GPU, 24 GB+ VRAM
- Local GPU, less than 24 GB
- None — laptop only

*Gates which execution skills apply. See the "Learn more" callout on the wizard page for what ALICE and LUCDH offer and how to get access.*

### 3. What languages or scripts are in the documents?
- Latin only (English, European languages)
- CJK (Korean, Chinese, Japanese)
- Historical scripts / Fraktur / older orthographies
- Multiple scripts in one corpus
- Other (specify in the follow-up with Steven)

*Affects model choice and prompt engineering. Non-Latin scripts need explicit character-set enumeration in prompts.*

### 4. What kind of documents?
- Books or book chapters
- Journal articles
- Newspapers or magazines
- Historical manuscripts or letters
- Government or legal documents
- Reports (working papers, white papers, dissertations)
- Forms, tables, or structured data
- Comics / manga / manhwa
- Mixed types in one corpus

*Selects prompt template. Comics use type-classification; newspapers use layout-aware prompting; forms are a different problem entirely and may need OCR + structure extraction.*

### 5. What software will you use? *(optional)*
- Orange Data Mining
- R
- Python
- Not sure yet

*Tailors the suggested metadata schema and output format (Orange prefers flat CSV, R/Python are flexible with tidy CSV or JSON). Does not change the routing path. **Method** questions — topic modeling, NER, embeddings, classification — are downstream of corpus building and handled in a separate future module.*

### 6. Resource constraints?
- No budget; time is flexible
- Small budget (under $100); moderate timeline
- Project grant; flexible timeline
- Need it done this week or month

*Breaks ties between API (fast, costs money) and HPC (slow setup, free compute).*

---

## Routing Matrix

| Pages | Compute | Recommendation |
|-------|---------|----------------|
| ≤ 1,000 | any | API path → `api-ocr-runner` |
| 1,001–5,000 | none or small GPU | API path |
| 1,001–5,000 | ALICE / LUCDH | HPC path → `alice-vllm-deploy` |
| 1,001–5,000 | local 24 GB+ | Local-GPU path → `hf-transformers-ocr` |
| 5,001–10,000 | ALICE / LUCDH | HPC path |
| 5,001–10,000 | local 24 GB+ | Local-GPU (slow but works) |
| 5,001–10,000 | none or small GPU | API with budget flag, or **Escalate** |
| > 10,000 | ALICE / LUCDH | HPC path |
| > 10,000 | none / small GPU | **Escalate** |

---

## Always-On Skills

Regardless of route, every user gets:

- `corpus-from-pdfs` — the end-to-end framing (read first)
- `corpus-metadata-design` — schema design (read before building)

---

## Escalation Triggers (→ mailto Steven)

Send to Steven when:

- More than 10,000 pages and no HPC or local GPU access
- Multi-language historical corpus
- Handwriting-heavy documents
- Mixed content types in one corpus (books + forms + newspapers)
- Timeline under a week on anything over 5,000 pages
- User bails out of the wizard partway, or explicitly requests help

---

## Starter Kit Output

The wizard renders six sections — see `STARTER_KIT.md` for the full spec:

1. **Header**: recommended path, corpus scale, cost, time estimate
2. **Read first**: 2–3 skills in numbered order
3. **Paste into Claude Code / Codex**: agent-ready prompt prefilled from answers
4. **Launch command**: one-line terminal invocation (`claude "..."` or `codex "..."`) to copy-paste
5. **Files to copy + commands**: templates to grab and the shell sequence to run
6. **Escalation**: `mailto:` button, always present, highlighted when an escalation trigger fired
