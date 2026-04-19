// wizard.js — client-side routing for the corpus-building wizard.
// No network calls, no storage. The student's answers stay in the browser.

(function () {
  "use strict";

  const form = document.getElementById("wizard");
  const output = document.getElementById("output");

  // -------------------------------------------------------------------------
  // Routing — mirrors wizard/QUESTIONS.md
  // -------------------------------------------------------------------------

  function pickPath(a) {
    const big = a.pages === "gt10k";
    const weakCompute = a.compute === "none";

    // Large corpus, laptop only → escalate.
    if (big && weakCompute) return "escalate";

    if (a.compute === "alice" || a.compute === "other_slurm") return "alice";
    if (a.compute === "gpu_big" || a.compute === "gpu_small" || a.compute === "lucdh") return "local_gpu";

    return "api";
  }

  function softFlags(a, path) {
    const flags = [];

    if (a.compute === "lucdh") {
      flags.push("LUCDH Digital Lab workstations are a shared resource and don't retain local files between sessions. Use external or cloud storage, and check workstation availability before committing.");
    }
    if (a.compute === "other_slurm") {
      flags.push("Non-ALICE SLURM clusters need minor adaptation — partition names, module loads, and paths. The `alice-vllm-deploy` skill covers the patterns; most adapt cleanly.");
    }
    if (a.compute === "gpu_small" && (a.pages === "5k_10k" || a.pages === "gt10k")) {
      flags.push("Under 16 GB of VRAM comfortably runs an 8B model, but throughput is the bottleneck on large corpora. Expect 8–10 seconds per page; budget accordingly. A 16 GB+ card (or API/HPC) would be markedly faster on a 10k-page run.");
    }
    if (path === "api" && (a.pages === "5k_10k" || a.pages === "gt10k")) {
      flags.push("Large corpus on the API path. Budget will run $100+ on Claude or GPT. Consider whether ALICE / LUCDH access is worth requesting before committing to API.");
    }
    if (a.constraints === "fast" && (a.pages === "5k_10k" || a.pages === "gt10k")) {
      flags.push("Tight timeline on a large corpus. Expect to parallelise or trim scope.");
    }
    if (a.language === "historical" && a.pages !== "lt100" && a.pages !== "101_500") {
      flags.push("Historical orthographies usually need prompt tuning on a small test tranche before running the full corpus.");
    }
    if (a.doctype === "forms") {
      flags.push("Forms and tables are a layout-extraction problem, not pure OCR. Prompts will need structure-aware tweaks.");
    }
    if (a.doctype === "manuscript") {
      flags.push("Handwritten manuscripts are a significantly harder problem than print OCR. The VLM path works for clean scripts; for degraded or idiosyncratic hands, consider Transkribus as a specialized alternative.");
    }
    return flags;
  }

  // -------------------------------------------------------------------------
  // Lookups
  // -------------------------------------------------------------------------

  const PAGE_BALLPARK = {
    lt100:    { midpoint: 60,    descriptor: "under 100" },
    "101_500":{ midpoint: 300,   descriptor: "roughly 300" },
    "501_1k": { midpoint: 750,   descriptor: "roughly 750" },
    "1k_5k":  { midpoint: 2500,  descriptor: "roughly 2,500" },
    "5k_10k": { midpoint: 7500,  descriptor: "roughly 7,500" },
    gt10k:    { midpoint: 15000, descriptor: "over 10,000" },
  };

  const LANGUAGE_DESC = {
    latin:      "English or Latin-script",
    cjk:        "CJK (Korean, Chinese, or Japanese)",
    historical: "in a historical or pre-reform orthography",
    mixed:      "with multiple scripts mixed in",
    other:      "",
  };

  const DOCTYPE_DESC = {
    book:       "scanned book chapters",
    journal:    "scanned journal articles",
    news:       "newspaper or magazine scans",
    manuscript: "historical manuscripts or letters",
    govlegal:   "government or legal documents",
    report:     "reports (working papers, white papers, dissertations)",
    forms:      "form or table scans",
    comic:      "comic or manhwa pages",
    mixed:      "mixed document types",
  };

  const ANALYSIS_DESC = {
    orange:  "Orange Data Mining",
    r:       "R",
    python:  "Python",
    unsure:  "",
  };

  const COMPUTE_LINE = {
    alice:      "I have an ALICE account and want to run vLLM on a GPU partition there.",
    lucdh:      "I have access to a LUCDH Digital Lab workstation and want to run a vision-language model locally.",
    other_slurm:"I have access to a (non-ALICE) SLURM cluster and will need to adapt the deployment patterns.",
    gpu_big:    "I have a local GPU with 16 GB or more of VRAM and want to use a 13B-class vision-language model (Qwen3-VL-13B or similar) with 4-bit quantization. If I have 24 GB+, I'll step up to a 32B.",
    gpu_small:  "I have a local GPU with less than 16 GB of VRAM (e.g. RTX 3060 12 GB, RTX 4070, or an 8 GB card like the RTX 4060) and want to use an 8B vision-language model (Qwen3-VL-8B or MiniCPM-V) with 4-bit quantization.",
    none:       "I'm on a laptop with no GPU; I want to use a cloud API (Claude or Gemini).",
  };

  // -------------------------------------------------------------------------
  // Estimates
  // -------------------------------------------------------------------------

  function estimateAPI(pages) {
    const low = pages * 0.010;
    const high = pages * 0.020;
    const gemLow = pages * 0.002;
    const gemHigh = pages * 0.005;
    return `$${low.toFixed(2)} – $${high.toFixed(2)} on Claude/GPT (≈ $${gemLow.toFixed(2)}–$${gemHigh.toFixed(2)} on Gemini Flash)`;
  }

  function timeAPI(pages) {
    const mins = Math.round(pages / 6);
    if (mins < 60) return `~${mins} min of sustained API calls + ~10 min for local stages`;
    const hours = (mins / 60).toFixed(1);
    return `~${hours} h sustained API calls (at ~6 pages/min) + ~10 min for local stages`;
  }

  function timeLocalGPU(pages, compute) {
    // Rough ballpark: 8B at NF4 on a 12 GB consumer card = ~8 s/page
    //                 13B on a 16 GB card = ~12 s/page
    //                 32B on a 24 GB card = ~15 s/page
    const secPerPage = compute === "gpu_big" ? 12 : 8;
    const mins = Math.round((pages * secPerPage) / 60);
    if (mins < 60) return `~2 min model load + ~${mins} min sequential OCR + ~10 min assembly`;
    const hours = (mins / 60).toFixed(1);
    return `~2 min model load + ~${hours} h sequential OCR + ~10 min assembly`;
  }

  function timeHPC(pages) {
    const ocrMins = Math.round(pages / 10); // ~6 s/page
    if (ocrMins < 60) return `~13 min cold start + ~${ocrMins} min OCR + ~10 min CPU stages`;
    const hours = (ocrMins / 60).toFixed(1);
    return `~13 min cold start + ~${hours} h OCR + ~10 min CPU stages`;
  }

  // -------------------------------------------------------------------------
  // Starter-kit content per path
  // -------------------------------------------------------------------------

  function renderKit(path, a) {
    const pages = PAGE_BALLPARK[a.pages].midpoint;
    const pagesDesc = PAGE_BALLPARK[a.pages].descriptor;
    const langDesc = LANGUAGE_DESC[a.language] || "";
    const docDesc = DOCTYPE_DESC[a.doctype] || "documents";
    const analysisDesc = ANALYSIS_DESC[a.analysis] || "";
    const computeLine = COMPUTE_LINE[a.compute] || "";

    if (path === "escalate") {
      return escalateKit(a, pagesDesc, docDesc);
    }

    const prompt = buildPrompt(a, pagesDesc, langDesc, docDesc, analysisDesc, computeLine, path);
    const flags = softFlags(a, path);

    const base = {
      prompt,
      launch: { claude: shellCommand("claude", prompt), codex: shellCommand("codex", prompt) },
      softFlags: flags,
    };

    if (path === "api") {
      return Object.assign(base, {
        header: {
          path: "Cloud API",
          scale: `${pagesDesc} pages`,
          cost: estimateAPI(pages),
          time: timeAPI(pages),
        },
        readFirst: ["corpus-from-pdfs", "corpus-metadata-design", "api-ocr-runner"],
        scenario: "examples/small_api.html",
        files: ["templates/prompts.py.template → prompts.py (Pattern A)"],
        commands:
`python3 scripts/inventory_builder.py --pdf-dir ./pdfs --output manifest.csv
python3 scripts/cost_estimator.py --pages ${pages} --compare
# OCR step — client script built with Claude Code, sends page images
#   to the Claude API, writes ocr_output/<pdf_id>/results_raw.json
python3 scripts/corpus_assembler.py --ocr-dir ocr_output --manifest manifest.csv --output corpus/`,
      });
    }

    if (path === "alice") {
      return Object.assign(base, {
        header: {
          path: "ALICE (HPC via SLURM)",
          scale: `${pagesDesc} pages`,
          cost: "free (HPC compute)",
          time: timeHPC(pages),
        },
        readFirst: ["corpus-from-pdfs", "corpus-metadata-design", "alice-vllm-deploy"],
        scenario: "examples/small_alice.html",
        files: [
          "templates/prompts.py.template → prompts.py",
          "templates/run_ocr.slurm.template → run_ocr.slurm",
        ],
        commands:
`python3 scripts/inventory_builder.py --pdf-dir ./pdfs --output manifest.csv
bash scripts/alice_deploy.sh \\
    --host alice3 \\
    --code-src ./pipeline --data-src ./pdfs \\
    --manifest ./manifest.csv \\
    --remote-base /zfsstore/user/<netid>/<project>
ssh alice3 "cd /zfsstore/user/<netid>/<project>/pipeline && sbatch run_ocr.slurm"
# …wait for the SLURM job to finish (monitor squeue + log tail)…
rsync -avz alice3:/zfsstore/user/<netid>/<project>/ocr_output/ ./ocr_output/
python3 scripts/corpus_assembler.py --ocr-dir ocr_output --manifest manifest.csv --output corpus/`,
      });
    }

    if (path === "local_gpu") {
      return Object.assign(base, {
        header: {
          path: "Local GPU",
          scale: `${pagesDesc} pages`,
          cost: "free (your electricity)",
          time: timeLocalGPU(pages, a.compute),
        },
        readFirst: ["corpus-from-pdfs", "corpus-metadata-design", "hf-transformers-ocr"],
        scenario: "examples/small_local_gpu.html",
        files: ["templates/prompts.py.template → prompts.py (Pattern A)"],
        commands:
`python3 scripts/inventory_builder.py --pdf-dir ./pdfs --output manifest.csv
# OCR step — HF Transformers client built with Claude Code:
#   loads Qwen3-VL-32B with BnB NF4, processes each page,
#   writes ocr_output/<pdf_id>/results_raw.json. Use tmux or nohup for long runs.
python3 scripts/corpus_assembler.py --ocr-dir ocr_output --manifest manifest.csv --output corpus/`,
      });
    }
  }

  function buildPrompt(a, pagesDesc, langDesc, docDesc, analysisDesc, computeLine, path) {
    const pathLabel = { api: "API", alice: "ALICE", local_gpu: "local-GPU" }[path] || path;
    const bits = [
      `I have ${docDesc} (${pagesDesc} pages).`,
      langDesc ? `The text is ${langDesc}.` : "",
      computeLine,
      analysisDesc ? `I'll load the corpus into ${analysisDesc} for analysis.` : "",
      `Walk me through the corpus-from-pdfs pipeline and help me set up the OCR and assembly stages for the ${pathLabel} path.`,
      `Start by asking about my analysis question so we can design the metadata schema before building.`,
    ];
    return bits.filter(Boolean).join(" ");
  }

  function escalateKit(a, pagesDesc, docDesc) {
    return {
      escalate: true,
      header: {
        path: "Escalation recommended",
        scale: `${pagesDesc} pages`,
        cost: "—",
        time: "—",
      },
      note: "This combination — a large corpus with no HPC access and no adequate local GPU — is outside the self-serve wizard's scope. Email Steven with your answers; the button below is prefilled. Good options to explore in that conversation: requesting ALICE access, trying the LUCDH AI Lab, or scoping the project down to a pilot you can run on the API path.",
      readFirst: ["corpus-from-pdfs"],
      scenario: "examples/small_api.html",
    };
  }

  // Shell-safe double-quote wrap for a generated prompt string.
  function shellCommand(bin, prompt) {
    const escaped = prompt.replace(/[\\$`"]/g, (c) => "\\" + c);
    return `${bin} "${escaped}"`;
  }

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  function render(kit, answers) {
    const el = document.createElement("div");
    el.className = "kit" + (kit.escalate ? " escalate" : "");

    el.appendChild(header(kit.header));

    if (kit.note) {
      const p = document.createElement("p");
      p.className = "note";
      p.textContent = kit.note;
      el.appendChild(p);
    }

    el.appendChild(section("§ 1. Read these first",
      list(kit.readFirst.map(s => {
        const a = document.createElement("a");
        a.href = `skills/${s}/SKILL.html`;
        a.textContent = s;
        return a;
      }))
    ));

    if (kit.launch) {
      const s = sectionHeader("§ 2. Start a Claude Code or Codex session");

      const intro = document.createElement("p");
      intro.className = "section-note";
      intro.textContent = "Open a terminal, cd into a fresh project directory, then paste one of these commands:";
      s.appendChild(intro);

      const launchLabel = document.createElement("div");
      launchLabel.className = "launch-label";
      launchLabel.textContent = "Claude Code";
      s.appendChild(launchLabel);
      const cPre = document.createElement("pre");
      cPre.className = "code launch";
      cPre.textContent = kit.launch.claude;
      s.appendChild(cPre);
      s.appendChild(copyButton(kit.launch.claude, "Copy Claude Code command"));

      const codexLabel = document.createElement("div");
      codexLabel.className = "launch-label";
      codexLabel.textContent = "Codex";
      s.appendChild(codexLabel);
      const xPre = document.createElement("pre");
      xPre.className = "code launch";
      xPre.textContent = kit.launch.codex;
      s.appendChild(xPre);
      s.appendChild(copyButton(kit.launch.codex, "Copy Codex command"));

      const altIntro = document.createElement("p");
      altIntro.className = "section-note alt";
      altIntro.textContent = "Already have a session open? Paste this as your first message instead:";
      s.appendChild(altIntro);
      const pPre = document.createElement("pre");
      pPre.className = "prompt";
      pPre.textContent = kit.prompt;
      s.appendChild(pPre);
      s.appendChild(copyButton(kit.prompt, "Copy prompt only"));

      el.appendChild(s);
    }

    if (kit.files && kit.files.length) {
      el.appendChild(section("§ 3. Files to copy", list(kit.files.map(f => textNode(f)))));
    }

    if (kit.commands) {
      const s = sectionHeader("§ 4. Commands (pre-filled)");
      const pre = document.createElement("pre");
      pre.className = "code";
      pre.textContent = kit.commands;
      s.appendChild(pre);
      s.appendChild(copyButton(kit.commands, "Copy commands"));
      el.appendChild(s);
    }

    if (kit.scenario) {
      const s = sectionHeader("§ 5. See a fleshed-out walkthrough");
      const a = document.createElement("a");
      a.href = kit.scenario;
      a.textContent = kit.scenario;
      s.appendChild(a);
      el.appendChild(s);
    }

    if (kit.softFlags && kit.softFlags.length) {
      el.appendChild(section("Things to watch",
        list(kit.softFlags.map(f => textNode(f)))));
    }

    // Escalation mailto — always shown, highlighted if escalate flag set.
    const mailto = buildMailto(answers, kit.escalate);
    const s = sectionHeader(kit.escalate ? "Next step: email Steven" : "Stuck? Email Steven");
    const a = document.createElement("a");
    a.href = mailto;
    a.className = "mailto";
    a.textContent = "Open pre-filled email";
    s.appendChild(a);
    el.appendChild(s);

    return el;
  }

  function buildMailto(a, escalated) {
    const subject = encodeURIComponent(
      escalated ? "corpus-building: escalation" : "corpus-building: help"
    );
    const lines = [
      "Wizard answers:",
      `  pages:       ${a.pages}`,
      `  compute:     ${a.compute}`,
      `  language:    ${a.language}`,
      `  doctype:     ${a.doctype}`,
      `  analysis:    ${a.analysis || "(not set)"}`,
      `  constraints: ${a.constraints}`,
      "",
      "Tell Steven what you're trying to do and where you got stuck.",
    ];
    const body = encodeURIComponent(lines.join("\n"));
    return `mailto:stevencdenney@gmail.com?subject=${subject}&body=${body}`;
  }

  // -------------------------------------------------------------------------
  // DOM helpers
  // -------------------------------------------------------------------------

  function header(h) {
    const wrap = document.createElement("div");
    wrap.className = "kit-header";
    wrap.innerHTML =
      `<div class="kit-path">${h.path}</div>` +
      `<dl>` +
        `<dt>Corpus scale</dt><dd>${h.scale}</dd>` +
        `<dt>Est. cost</dt><dd>${h.cost}</dd>` +
        `<dt>Est. time</dt><dd>${h.time}</dd>` +
      `</dl>`;
    return wrap;
  }

  function section(title, body) {
    const wrap = sectionHeader(title);
    wrap.appendChild(body);
    return wrap;
  }

  function sectionHeader(title) {
    const wrap = document.createElement("section");
    const h = document.createElement("h3");
    h.textContent = title;
    wrap.appendChild(h);
    return wrap;
  }

  function list(items) {
    const ul = document.createElement("ul");
    items.forEach(it => {
      const li = document.createElement("li");
      li.appendChild(it);
      ul.appendChild(li);
    });
    return ul;
  }

  function textNode(text) {
    const span = document.createElement("span");
    span.textContent = text;
    return span;
  }

  function copyButton(text, label) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "copy";
    b.textContent = label;
    b.addEventListener("click", () => {
      navigator.clipboard.writeText(text).then(
        () => { b.textContent = "Copied"; setTimeout(() => b.textContent = label, 1500); },
        () => { b.textContent = "Copy failed"; setTimeout(() => b.textContent = label, 1500); }
      );
    });
    return b;
  }

  // -------------------------------------------------------------------------
  // Main
  // -------------------------------------------------------------------------

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const data = new FormData(form);
    const answers = {
      pages:       data.get("pages"),
      compute:     data.get("compute"),
      language:    data.get("language"),
      doctype:     data.get("doctype"),
      analysis:    data.get("analysis"),
      constraints: data.get("constraints"),
    };
    const path = pickPath(answers);
    const kit = renderKit(path, answers);
    output.innerHTML = "";
    output.appendChild(render(kit, answers));
    output.classList.remove("hidden");
    output.scrollIntoView({ behavior: "smooth", block: "start" });
  });

  // -------------------------------------------------------------------------
  // URL-parameter pre-fill: lets other pages (the supervision-site embed, a
  // shared link) route a visitor straight to a pre-populated wizard. If every
  // required field is already filled by the URL, auto-submit so the starter
  // kit renders on arrival.
  // -------------------------------------------------------------------------

  function prefillFromURL() {
    const params = new URLSearchParams(window.location.search);
    const fields = ["pages", "compute", "language", "doctype", "analysis", "constraints"];
    let anySet = false;

    for (const name of fields) {
      const v = params.get(name);
      if (!v) continue;
      const el = form.elements[name];
      if (!el) continue;
      // Only set the value if the URL param matches one of the <option>s.
      const valid = Array.from(el.options).some(o => o.value === v);
      if (!valid) continue;
      el.value = v;
      anySet = true;
    }

    if (!anySet) return;

    const required = ["pages", "compute", "language", "doctype", "constraints"];
    const allFilled = required.every(name => form.elements[name].value);
    if (allFilled) {
      requestAnimationFrame(() => {
        if (typeof form.requestSubmit === "function") form.requestSubmit();
        else form.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
      });
    }
  }
  prefillFromURL();
})();
