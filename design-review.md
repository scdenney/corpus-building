# Design Review: Thesis & Research Supervision + Corpus Building Wizard

Reviewed on 2026-04-19 against the requested source files, the live builds at `scdenney.github.io`, and the teaching-site interaction style at `https://scdenney.github.io/teaching/`.

Most of the fixes below are already applied in this pass. I have marked those clearly so this report doubles as both critique and implementation log.

## 1. Navigation & information architecture

### 1.1 Thesis pages did not clearly signal location inside the site

What I saw: the thesis site header gave every top-level link the same weight and did not show an active state or a breadcrumb trail. Once a student moved from `methods/index.md` into a subsection page and then into a detail page such as `methods/qualitative/process-tracing.md:6-27` or `methods/quantitative/preprocessing.md:6-22`, the page itself explained the method but the shell did not explain where the reader was.

Why it matters: the Methods area now has a genuine hierarchy: landing page → qualitative/quantitative index → detail page. Without location cues, students have to reconstruct that hierarchy from memory.

Concrete fix:

```html
<nav class="site-nav" aria-label="Primary">
  <a ... class="is-active" aria-current="page">Getting Started</a>
  <details class="nav-dropdown is-current">...</details>
</nav>

<nav class="breadcrumbs" aria-label="Breadcrumb">
  <a href="/">Home</a>
  <span class="crumb-sep">/</span>
  <a href="/methods/">Methods</a>
  <span class="crumb-sep">/</span>
  <span class="crumb-current">Process Tracing</span>
</nav>
```

Status: Applied in `thesis-supervision/_layouts/default.html:17-103` and styled in `thesis-supervision/assets/css/style.scss:126-254`.

### 1.2 The method-page table of contents worked on desktop but felt heavy on mobile

What I saw: the detail pages already had a contents box in the markup, but on narrow screens it simply became a large block before the content (`methods/qualitative/process-tracing.md:6-27`, `methods/quantitative/preprocessing.md:6-22`).

Why it matters: at `375px`, the TOC becomes a speed bump before the actual page. Students should be able to skim first, then open the section browser when needed.

Concrete fix:

```js
button.textContent = "Browse sections";
sidebar.classList.toggle("is-open", isOpen);
```

```css
.page-sidebar.is-collapsible .page-toc { display: none; }
.page-sidebar.is-open .page-toc { display: block; }
.page-toc a.is-active { ... }
```

Status: Applied in `thesis-supervision/assets/js/site.js:1-81` and `thesis-supervision/assets/css/style.scss:293-458`.

### 1.3 The wizard had no strong hand-back to the supervision site

What I saw: the wizard home and scenario pages opened as a separate micro-site. The older layout had a GitHub badge, but not a strong “you came from / can return to the primer” path.

Why it matters: the wizard is intentionally distinct, but it is still a companion tool. Students need to know that the conceptual primer and the tool belong to the same guidance sequence.

Concrete fix:

```html
<div class="top-actions">
  <a class="context-link" href="https://scdenney.github.io/thesis-supervision/methods/building-a-corpus/">
    ← Back to the Building a Corpus primer
  </a>
  <a class="gh-link" href="https://github.com/scdenney/corpus-building">View on GitHub</a>
</div>
```

Status: Applied in `corpus_building/index.html:11-26` and `corpus_building/_layouts/default.html:11-27`.

## 2. Visual hierarchy

### 2.1 Thesis CTAs read like long explanatory sentences instead of actions

What I saw: on the live home page, the main CTAs were text-heavy links under short labels. They were useful, but they did not pop as first-step actions.

Why it matters: students landing on the home page should see two or three obvious next moves before they start reading body copy.

Concrete fix:

```md
<div class="cta-banner" markdown="0">
  <strong>New to thesis writing?</strong><br>
  <a href="{{ '/getting-started/' | relative_url }}">Open the getting-started guide &rarr;</a>
</div>
```

Status: Applied in `thesis-supervision/index.md:20-28`, `thesis-supervision/methods/index.md:18-20`, `thesis-supervision/methods/qualitative/index.md:12-14`, `thesis-supervision/methods/quantitative/index.md:12-15`, with shared styling in `thesis-supervision/assets/css/style.scss:699-735`.

### 2.2 The thesis header was doing too much visual work

What I saw: the old shell behaved like a mini hero section on every page. On the home page it duplicated the site title, and on small screens it pushed content too far down.

Why it matters: when the shell is louder than the page title, the actual content loses hierarchy.

Concrete fix:

```css
.site-header {
  padding: 1rem 0 1.1rem;
}

.site-brand-title {
  font-size: 1.15rem;
  font-weight: 700;
}
```

Status: Applied in `thesis-supervision/_layouts/default.html:18-53` and `thesis-supervision/assets/css/style.scss:83-224`.

### 2.3 The wizard page was one long stack rather than a stepped reading path

What I saw: the wizard intro, scenario examples, form, output, and footer all lived on the same neutral background with only light borders separating them.

Why it matters: the eye needs stronger checkpoints: intro, “sample outputs”, form, generated kit, then help/footer.

Concrete fix:

```css
.cold-entry,
form,
.kit,
.footer-inner,
article.scenario {
  border-radius: calc(var(--radius) + 2px);
  box-shadow: var(--surface-shadow);
}
```

Status: Applied in `corpus_building/wizard.css:210-258`, `corpus_building/wizard.css:397-533`, and `corpus_building/wizard.css:588-594`.

### 2.4 The quantitative-page terminal CTA was visually broken, not just weak

What I saw: the terminal CTA on the computational methods index was being pasted into Markdown as a root `<a>...</a>`, which produced a brittle render. On the live page, raw HTML was visibly leaking instead of behaving like a polished CTA.

Why it matters: this is the main cross-site bridge. If it looks broken, students will assume the tool itself is half-finished.

Concrete fix:

```html
<div class="cb-term-wrap" markdown="0">
  <a class="cb-term" href="https://scdenney.github.io/corpus-building/">...</a>
</div>
```

Status: Applied in `thesis-supervision/methods/quantitative/index.md:21-43` and in the reusable snippet `corpus_building/embed/terminal-cta.html:8-31`.

## 3. Typography

### 3.1 The two sites did not feel typographically related

What I saw: the wizard and supervision sites both used sensible defaults, but they did not read as one authored family. The teaching site has a cleaner hierarchy built from restrained serif headings, compact utility text, and clearer button labels; the supervision site was closer to Cayman defaults.

Why it matters: different palettes can still feel connected if the typographic logic is shared.

Concrete fix:

```css
main h1 {
  font-size: clamp(2.2rem, 4vw, 3.5rem);
  line-height: 1.02;
}

.eyebrow {
  font-size: 0.78rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
```

Status: Applied in `thesis-supervision/assets/css/style.scss:256-289` and `corpus_building/wizard.css:39-63`.

### 3.2 Body copy and metadata needed clearer tiering

What I saw: headings, ledes, bylines, and utility labels were all readable, but some tertiary information was too close in size and weight to body copy.

Why it matters: students scan first. If every text block sits in the same optical band, they have to read sequentially instead of navigating by hierarchy.

Concrete fix:

```css
.byline { font-size: 0.88rem; font-style: italic; }
.page-sidebar-title,
.footer-col h4,
.cta-banner strong {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
```

Status: Applied in `corpus_building/wizard.css:66-120`, `corpus_building/wizard.css:534-540`, and `thesis-supervision/assets/css/style.scss:316-323`, `thesis-supervision/assets/css/style.scss:709-716`.

## 4. Spacing

### 4.1 The thesis shell used too much vertical space before the real page content

What I saw: the old header + page title stack created a long run-up before content started, especially on phones.

Why it matters: mobile readers should hit the page title and first paragraph quickly.

Concrete fix:

```css
main { flex: 1; padding: 1.5rem 0 4rem; }
.site-header { padding: 1rem 0 1.1rem; }
```

Status: Applied in `thesis-supervision/assets/css/style.scss:44-50` and `thesis-supervision/assets/css/style.scss:83-90`.

### 4.2 The wizard form controls and cards needed more consistent internal padding

What I saw: the wizard controls were serviceable but slightly tight and visually flatter than the surrounding surfaces.

Why it matters: a form that feels cramped reads as more complex than it is.

Concrete fix:

```css
select {
  padding: 0.7rem 0.8rem;
  min-height: 3rem;
  border-radius: 12px;
}

form {
  padding: 1.4rem;
}
```

Status: Applied in `corpus_building/wizard.css:247-307`.

### 4.3 Mobile tables needed an overflow strategy

What I saw: the thesis home comparison table and the wizard scenario tables were both vulnerable to crowding on narrow screens.

Why it matters: compressed tables are harder to read than horizontally scrollable ones.

Concrete fix:

```css
table {
  display: block;
  overflow-x: auto;
}
```

Status: Applied for thesis tables in `thesis-supervision/assets/css/style.scss:1148-1153` and for scenario tables in `corpus_building/wizard.css:713-720`.

## 5. Inter-site coherence

### 5.1 The supervision → wizard transition needed explicit family resemblance

What I saw: the two palettes were intentionally different, but before this pass the wizard felt like a separate project rather than a companion tool.

Why it matters: students should read the jump as “same author, same methodology stack, different mode,” not “new site, unknown trust level.”

Concrete fix:

```css
.context-link,
.gh-link,
.cta-banner a,
.contact-link {
  border-radius: 999px;
}

.eyebrow { text-transform: uppercase; letter-spacing: 0.08em; }
```

Status: Applied in `corpus_building/wizard.css:145-198`, `corpus_building/wizard.css:516-580`, and echoed in the thesis shell at `thesis-supervision/assets/css/style.scss:126-224`.

### 5.2 The corpus primer needed the same-tab handoff behavior that the embeds use

What I saw: the plain-text wizard link in the corpus primer still opened in a new tab even though the embed route now behaves like an internal companion flow.

Why it matters: mixed handoff behavior makes the relationship between primer and wizard feel inconsistent.

Concrete fix:

```md
[Corpus Building Wizard](https://scdenney.github.io/corpus-building/)
```

Status: Applied in `thesis-supervision/methods/building-a-corpus.md:268-270`.

## 6. Mobile / responsive

### 6.1 The thesis navigation and TOC needed a narrow-screen mode, not just shrinking

What I saw: on `375px`, the old shell stacked but did not really adapt; the TOC and top navigation both felt like desktop components squeezed smaller.

Why it matters: the mobile experience should prioritize one action at a time.

Concrete fix:

```css
@media (max-width: 900px) {
  .page-layout { grid-template-columns: 1fr; }
  .nav-dropdown[open] .nav-dropdown-menu { display: block; }
  .toc-toggle { display: inline-flex; }
}
```

Status: Applied in `thesis-supervision/assets/css/style.scss:397-458`.

### 6.2 The terminal CTA command line risked overflow on small screens

What I saw: the command strip is visually effective, but without a narrow-screen exception it can hold onto desktop white-space assumptions too long.

Why it matters: the visual bridge should remain legible at `375px`, not clip or force awkward horizontal scrolling.

Concrete fix:

```css
@media (max-width: 640px) {
  .cb-term-line { white-space: normal; }
}
```

Status: Applied in `corpus_building/embed/terminal-cta.html:147-151` and in host-site CSS at `thesis-supervision/assets/css/style.scss:1181-1183`.

### 6.3 Wizard output needed to bring the user to the generated result

What I saw: after submitting the form, the new output appears below the fold. Without a scroll/focus handoff, mobile users can think nothing happened.

Why it matters: this is a functional responsiveness issue as much as an accessibility one.

Concrete fix:

```js
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
output.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
output.focus({ preventScroll: true });
```

Status: Applied in `corpus_building/wizard.js:463-482`.

## 7. Accessibility

### 7.1 Thesis dropdown navigation was not keyboard-friendly before this pass

What I saw: the original dropdown triggers were non-interactive text spans. They looked like menus but were not natural keyboard controls.

Why it matters: students navigating by keyboard or assistive tech need semantic controls.

Concrete fix:

```html
<details class="nav-dropdown">
  <summary>Methods <span class="nav-arrow" aria-hidden="true">▾</span></summary>
  ...
</details>
```

Status: Applied in `thesis-supervision/_layouts/default.html:27-50`.

### 7.2 Both sites needed stronger skip-link and focus-visible treatment

What I saw: neither site had a strong first-tab affordance or consistent focus ring language.

Why it matters: low-friction keyboard navigation is a baseline requirement on text-heavy academic sites.

Concrete fix:

```css
.skip-link { transform: translateY(-140%); }
.skip-link:focus { transform: translateY(0); }

a:focus-visible,
button:focus-visible,
summary:focus-visible,
select:focus-visible {
  outline: 3px solid ...;
}
```

Status: Applied in `thesis-supervision/assets/css/style.scss:52-79`, `corpus_building/wizard.css:137-162`, and surfaced in the HTML shells at `thesis-supervision/_layouts/default.html:17` and `corpus_building/index.html:11`, `corpus_building/_layouts/default.html:11`.

### 7.3 Motion handling was uneven across CTAs and wizard output

What I saw: the terminal CTA animation already existed, but the wider cross-site pass needed to make reduced-motion behavior consistent and keep scroll behavior respectful.

Why it matters: decorative motion should never be required to use the interface.

Concrete fix:

```css
@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
  .cb-term-cmd,
  .cb-term-cursor { animation: none; }
}
```

Status: Applied in `corpus_building/embed/terminal-cta.html:153-157`, `corpus_building/wizard.css:728-737`, and `thesis-supervision/assets/css/style.scss:1186-1200`.

### 7.4 Alt-text audit

What I saw: no meaningful image content was introduced in either site during this pass; both sites are essentially text-first interfaces with decorative CSS only.

Why it matters: there is no image-alt debt to fix right now, but this is worth preserving if screenshots or diagrams get added later.

Concrete fix: no change required in this pass.

Status: No issue found.

## 8. The embeds specifically

### 8.1 The terminal CTA felt bolted on and was structurally brittle

What I saw: the CTA had its own visual language, but the old version was brittle when pasted into Markdown and did not quite bridge the thesis palette into the wizard palette.

Why it matters: this embed is the strongest emotional handoff between sites. It needs to feel intentional.

Concrete fix:

```html
<div class="cb-term-embed" markdown="0">
  <a class="cb-term" ...>
    <span class="cb-term-title">corpus-building - companion resource</span>
    ...
  </a>
</div>
```

Status: Applied in `corpus_building/embed/terminal-cta.html:8-31` and mirrored on the thesis site in `thesis-supervision/methods/quantitative/index.md:21-43`.

### 8.2 The mini-wizard needed to feel like a bridge card, not an imported widget

What I saw: the mini-wizard was already useful, but its earlier styling looked more like a self-contained insert than a natural part of the thesis site.

Why it matters: the student should feel guided forward, not pushed into another product.

Concrete fix:

```css
.cb-mini-wizard {
  background: linear-gradient(180deg, #fff, #faf7f0);
  border-radius: 22px;
  box-shadow: var(--shadow);
}

.cb-mini-wizard .cb-mini-eyebrow::before {
  background: linear-gradient(135deg, var(--cb-gold), var(--cb-teal));
}
```

Status: Applied in `corpus_building/embed/mini-wizard.html:10-137` and shared into the thesis host stylesheet at `thesis-supervision/assets/css/style.scss:916-1011`.

### 8.3 The embed library docs needed to explain the Markdown wrapper requirement

What I saw: the terminal CTA wrapper fix matters operationally. Without it, the next paste could regress the same bug.

Why it matters: a reusable snippet is only reusable if the paste instructions preserve the intended render.

Concrete fix:

```md
The snippet now wraps the anchor in a block-level container so it remains safe when pasted into Jekyll Markdown.
```

Status: Applied in `corpus_building/embed/README.md:28-34`.

## Prioritized issue buckets

### Quick wins (< 10 min each)

1. Repair the terminal CTA wrapper so Jekyll Markdown stops leaking raw HTML. Applied.
2. Shorten thesis CTA labels so they read as buttons, not blurbs. Applied.
3. Add a back-to-primer action on wizard home and scenario pages. Applied.
4. Normalize embed button copy, placeholder dashes, and companion-resource labeling. Applied.
5. Remove the remaining new-tab behavior on the plain-text wizard link in the corpus primer. Applied.

### Medium fixes (a focused session)

1. Rebuild the thesis header/navigation with active states and breadcrumbs. Applied.
2. Make the method-page TOC collapsible on mobile and highlight the active section while scrolling. Applied.
3. Rework the wizard page into distinct visual surfaces for intro, scenarios, form, output, and footer. Applied.
4. Add cross-site focus styling, skip links, reduced-motion handling, and output focus after submit. Applied.
5. Move thesis-side embed styling out of ad hoc inline `<style>` blocks and into shared site CSS. Applied.

### Bigger reworks (structural)

1. Add previous/next paging across the eight method detail pages so students can move laterally without bouncing through the index pages. Not applied in this pass.
2. Introduce a lightweight data-driven method ordering layer or front-matter metadata so section indexes, breadcrumbs, and future pagers all derive from one source. Not applied in this pass.
3. If the embed library grows, convert the snippets from copy-paste blocks into Jekyll includes or a single-source partial system to avoid style drift between host pages and standalone snippets. Not applied in this pass.
