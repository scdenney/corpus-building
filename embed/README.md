---
title: "Embed snippets"
---

# Embed snippets

Two copy-paste blocks for linking from the thesis-supervision site (or anywhere else) into the corpus-building wizard.

Both snippets are self-contained HTML + CSS — no JavaScript, no build step, no external dependencies. Drop them anywhere a raw HTML block renders (including most Jekyll / Hugo / plain-HTML pages).

## 1. `mini-wizard.html` — inline mini-wizard

A short two-question form (pages + compute) that opens the full wizard with those answers pre-filled via URL parameters. Good for the Building-a-Corpus > Using Computational Tools section of the supervision site.

The main wizard reads the parameters on page load. If enough fields are pre-filled, the starter kit renders immediately; otherwise the form opens with those two dropdowns pre-selected and the student completes the remaining questions.

Accepted URL parameters (all optional):

- `pages` — one of `lt100`, `101_500`, `501_1k`, `1k_5k`, `5k_10k`, `gt10k`
- `compute` — one of `alice`, `lucdh`, `other_slurm`, `gpu_big`, `gpu_small`, `none`
- `language` — one of `latin`, `cjk`, `historical`, `mixed`, `other`
- `doctype` — one of `book`, `journal`, `news`, `manuscript`, `govlegal`, `report`, `forms`, `comic`, `mixed`
- `analysis` — one of `orange`, `r`, `python`, `unsure`
- `constraints` — one of `free_time`, `small_budget`, `grant`, `fast`

## 2. `terminal-cta.html` — faux-terminal call-to-action

A dark terminal-window block with a typed command and blinking cursor. Clicking anywhere on the block opens the wizard. Good for the Methods > Computational & quantitative approaches landing page.

Respects `prefers-reduced-motion` — the typing animation disables for users who've opted out.

## Styling notes

Both snippets use a scoped class prefix (`cb-`) to avoid conflicts with host-site CSS. Core tokens (accent colour, fonts) are declared as CSS custom properties at the top of each block's style — tweak them to match a host site's palette if needed.
