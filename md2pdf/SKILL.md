---
name: md2pdf
description: >
  Converts Markdown files to beautifully formatted PDF documents using Puppeteer
  (via md-to-pdf) or LaTeX (via pandoc). Use this skill when the user asks to
  convert, export, render, or generate a PDF from a Markdown file, OR when the
  user asks to tweak, adjust, or fix the layout of a previously generated PDF.
allowed-tools: shell
---

# md2pdf Skill

You convert Markdown files into professional PDF documents.

## Workflow

### Step 0 — IDENTIFY INPUT

Ask the user which Markdown file(s) to convert. If the current directory contains `.md` files,
list them and let the user pick. If the user already specified a file, proceed directly.

### Step 1 — CHOOSE BACKEND

Check what's available and pick the best backend:

**Option A — Puppeteer (preferred)**

Check if `md-to-pdf` is installed:
```bash
npx md-to-pdf --version 2>/dev/null
```

If not installed, ask the user:
> `md-to-pdf` is needed for high-quality PDF rendering. I can install it with `npm install -g md-to-pdf`. Want me to proceed?

**Option B — LaTeX (fallback)**

If the user prefers LaTeX or Puppeteer isn't available:
```bash
which pandoc && which pdflatex
```

If not installed, offer to install:
> I need `pandoc` and a LaTeX distribution. I can install them with:
> - macOS: `brew install pandoc basictex`
> - Linux: `sudo apt install pandoc texlive-latex-base`

### Step 2 — LOAD CONFIG

Check for a config file:
```bash
cat .github/md2pdf/md2pdf.config.json 2>/dev/null || echo "no config"
```

If a config exists, use its settings (margins, format, headers/footers, page breaks, etc.).
If no config exists, use sensible defaults (A4, 20-25mm margins, no header, page numbers in footer).

### Step 3 — CONVERT

**Puppeteer backend:**
```bash
npx md-to-pdf <input>.md --config-file .github/md2pdf/md2pdf.config.json
```

If no config file exists or md-to-pdf doesn't support the config format, use inline options:
```bash
npx md-to-pdf <input>.md --pdf-options '{"format":"A4","margin":{"top":"25mm","right":"20mm","bottom":"25mm","left":"20mm"},"printBackground":true}'
```

**LaTeX backend:**
```bash
pandoc <input>.md -o <output>.pdf \
  --pdf-engine=pdflatex \
  -V geometry:margin=25mm \
  -V fontsize=11pt
```

**Output filename:** By default, use the same name as the input with `.pdf` extension.
If the config specifies an output directory or filename, use those instead.

### Step 4 — VERIFY

Confirm the PDF was created and report its size:
```bash
ls -lh <output>.pdf
```

Tell the user the output path and file size.

If conversion failed, diagnose the error and try the alternative backend.

## Configuration Reference

The config file at `.github/md2pdf/md2pdf.config.json` supports:

| Key | Description |
|-----|-------------|
| `backend` | `"puppeteer"` or `"latex"` |
| `puppeteer.format` | Page size (A4, Letter, etc.) |
| `puppeteer.margin` | Top/right/bottom/left margins |
| `puppeteer.printBackground` | Include background colors/images |
| `puppeteer.displayHeaderFooter` | Show header/footer |
| `puppeteer.headerTemplate` | HTML template for header |
| `puppeteer.footerTemplate` | HTML template for footer |
| `latex.engine` | LaTeX engine (pdflatex, xelatex, lualatex) |
| `sections.pageBreakBefore` | Insert page breaks before these heading levels |
| `output.directory` | Output directory (default: same as input) |
| `output.filename` | Override output filename |

### Step 5 — TWEAK LOOP (live refinement)

After the initial PDF is generated, the user will often request visual adjustments in a
conversational back-and-forth. This is the core interactive workflow of the skill.

**Golden rule: Choose the right tool for each tweak.**
- **CSS overrides** for visual/layout changes (fonts, spacing, colors, hiding elements, etc.)
- **Markdown edits** for content or structural changes (text fixes, line breaks, reordering, adding/removing sections)
- **Both together** when needed — e.g., moving a `---` in Markdown AND styling the resulting `<hr>` via CSS.

Always keep both files in sync: if a Markdown change affects layout, update the CSS override
to match, and vice versa. Re-render the PDF after every change.

**Visual feedback — signal the user they are in the tweak loop.**

The Copilot CLI UI collapses bash output and does not render ANSI escape codes visually.
Therefore, do NOT use `printf` or bash for visual banners. Instead, use **text-based framing
directly in your markdown responses**.

Rules:
1. While in tweak mode, **every response** must be visually prefixed with the tweak-mode
   indicator so the user always knows they are "inside" the loop.
2. Use Unicode box-drawing and emoji in your text output — no bash printf.

**Enter tweak loop** — output this text after initial PDF generation (Step 4):

```
🔄 ┌ PDF Tweak Mode
   │
   │ 📄 <filename>.pdf
   │
   │ Ask me to adjust layout, spacing,
   │ fonts, page breaks, colors …
   │
   │ Say "looks good" when you're done.
```

**During the loop — use `ask_user` as a persistent chat input:**

After the entry banner and after every tweak, immediately call `ask_user` to keep the
loop open. This creates an always-open input area the user explicitly exits.

```
question: "🔄 Tweak mode │ Type your change (or \"done\" to exit)"
allow_freeform: true
```

The freeform text input is the primary interaction — the user just types their instruction.
No choices are shown. Typing "done" (or "looks good", "exit", etc.) exits the loop.

- If the user types a tweak description → apply it, re-render, show confirmation
  prefixed with `🔄│`, then call `ask_user` again.
- If the user types "done" / "looks good" / "exit" → close the loop (see below).

After each successful re-render, prefix your confirmation with the gutter before showing
the next `ask_user` prompt:

```
🔄│ ✏️ Applied: <short description>
🔄│ 📄 Re-rendered <filename>.pdf (<size>)
```

This creates a tight, immersive input loop that the user explicitly exits.

**Close the loop** — output this when user confirms they're satisfied:

```
   │
   │ ✅ PDF Finalized
   │
   │ 📄 <filename>.pdf
   │ 🎨 <filename>.overrides.css saved
   │
   └──────────────────────────────────
```

Replace `<filename>`, `<short description>`, and `<size>` with actual values.

**How it works:**

1. Maintain a CSS override file next to the PDF: `<input-basename>.overrides.css`
   (e.g. `Antonio_Rodrigues_CV.overrides.css`). Create it on first tweak request.
2. Each tweak **appends** new rules to this file, preserving all previous adjustments.
3. Re-render the PDF passing `--stylesheet <file>.overrides.css` alongside the existing
   config/pdf-options.
4. Report the result and wait for the next tweak or confirmation.

**Re-render command (Puppeteer):**
```bash
npx --yes md-to-pdf <input>.md \
  --stylesheet <input-basename>.overrides.css \
  --pdf-options '{ ... same options as Step 3 ... }'
```

**When the user says it looks good**, let them know the overrides file is saved and can be
reused for future renders of the same document.

### CSS Tweak Recipes

Common adjustments the user may request and their CSS solutions:

| Request | CSS |
|---------|-----|
| Put element X on its own line | `<selector> { display: block; }` |
| Line break before a specific link | `a[href*="keyword"]::before { content: "\A"; white-space: pre; }` |
| Hide a separator or text node before/after a link | Wrap with `<span>` in the override is not possible — use `display:block` on surrounding elements instead |
| Increase/decrease font size of a section | `h2, h3 { font-size: 1.1em; }` or target specific selectors |
| Add spacing between sections | `h2 { margin-top: 2em; }` |
| Reduce spacing to fit content on fewer pages | `h2 { margin-top: 0.8em; } p, li { margin: 0.2em 0; }` |
| Force a page break before a heading | `h2:nth-of-type(N) { page-break-before: always; }` or use a class |
| Change link colors | `a { color: #0366d6; }` |
| Hide an element | `<selector> { display: none; }` |
| Center the header block | `h1, h1 + p { text-align: center; }` |
| Two-column layout for a section | `ul { columns: 2; }` |
| Adjust margins | Pass updated `--pdf-options` margin values |

**Selector tips for targeting specific elements:**
- By link URL: `a[href*="github.com"]`, `a[href*="linkedin.com"]`
- By position: `h2:nth-of-type(3)`, `ul:first-of-type`
- By heading content proximity: `h2 + p` (paragraph right after an h2)
- By nesting: `li > ul` (nested lists)

## Notes

- Prefer the Puppeteer backend for Markdown with complex formatting, HTML elements, or CSS styling.
- Prefer the LaTeX backend for academic/formal documents or when Puppeteer is unavailable.
- If the Markdown contains front-matter YAML, `md-to-pdf` will use it for additional configuration.
- After initial conversion, expect an iterative tweak loop. Stay responsive and re-render quickly.
- Keep the overrides CSS file clean and commented so the user can review or reuse it later.
