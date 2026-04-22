# md2pdf — Incremental Markdown → PDF Skill

A [Copilot CLI](https://docs.github.com/copilot/concepts/agents/about-copilot-cli) / [Claude Code](https://docs.anthropic.com/en/docs/claude-code/skills) skill that converts Markdown to professional PDFs with **incremental rendering** — change one section, and only that section is re-rendered.

## ✨ Features

- **Incremental rendering** — Sections are cached by content hash. Edit one section → sub-second re-render instead of full rebuild.
- **Chat-driven editing** — Tell the AI "fix the introduction" and it edits only that section in the MD, then re-renders incrementally.
- **Two backends** — Puppeteer (HTML→PDF, fast, CSS-customizable) and LaTeX (pro typographic quality).
- **GitHub-inspired theme** — Clean default CSS with page breaks, headers/footers, code blocks, tables.
- **YAML frontmatter** — Title, author, date metadata rendered as a styled header.
- **Section-aware** — Splits documents on H1/H2 headings. Each section is independently cached and renderable.

## 📦 Installation

### Option 1 — For a specific project (Claude Code)

```bash
cp -r md2pdf your-project/.claude/skills/
```

### Option 2 — For all your projects (Claude Code)

```bash
cp -r md2pdf ~/.claude/skills/
```

### Option 3 — For a specific project (Copilot CLI)

```bash
cp -r md2pdf your-project/.github/skills/
```

### Option 4 — Git submodule (easy updates)

```bash
cd your-project
git submodule add https://github.com/<your-username>/public-projects.git .claude/skills/public-projects
```

To update later:
```bash
git submodule update --remote
```

## 🚀 Usage

Once the skill is installed, just ask:

```
Convert my-doc.md to PDF
```

The AI will:
1. Run `setup.sh` (first time only — installs Puppeteer + remark)
2. Parse the MD into sections
3. Render each section → assemble HTML → export PDF
4. Open the PDF for preview

### Incremental editing

```
Fix the introduction — make it more concise
```

The AI will:
1. Identify the "Introduction" section
2. Edit only those lines in the MD file
3. Run incremental render (only the changed section is re-processed)
4. Report: "Updated! ⚡ 1/8 sections re-rendered (0.7s)"

### Other commands

```
Switch to LaTeX backend
List all sections in my-doc.md
Use a custom CSS theme
Change the margins to 15mm
```

## 🏗 Architecture

```
Markdown file
    ↓
┌─────────────────────────────────────────┐
│  Parser (remark)                         │
│  Split on H1/H2 → sections with hashes  │
└────────────────┬────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│  Cache Manager                           │
│  Compare hashes → find changed sections  │
│  Load cached HTML for unchanged sections │
└────────────────┬────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│  Renderer (Puppeteer or LaTeX)           │
│  Render only changed sections to HTML    │
│  Assemble full document → export PDF     │
└─────────────────────────────────────────┘
```

### Cache structure

```
.md2pdf/
├── node_modules/        # Dependencies (Puppeteer, remark, etc.)
├── package.json
└── cache/
    ├── manifest.json    # Section IDs → content hashes
    ├── sections/
    │   ├── 00-preamble.html
    │   ├── 01-introduction.html
    │   └── ...
    └── assembled.html   # Last full HTML (for debugging)
```

## ⚙️ Configuration

Copy the config template to your project root:

```bash
cp <skill-dir>/md2pdf.config.json ./md2pdf.config.json
```

| Option | Default | Description |
|--------|---------|-------------|
| `backend` | `"puppeteer"` | Rendering backend: `puppeteer` or `latex` |
| `puppeteer.format` | `"A4"` | Page size (A4, Letter, Legal, etc.) |
| `puppeteer.margin` | `25mm / 20mm` | Page margins |
| `puppeteer.displayHeaderFooter` | `true` | Show page numbers |
| `theme` | `null` | Path to custom CSS file (null = built-in theme) |
| `sections.splitOn` | `["h1", "h2"]` | Heading levels that define section boundaries |
| `cache.enabled` | `true` | Enable section-level caching |

## 🎨 Custom Themes

1. Copy the default theme: `cp <skill-dir>/default.css ./my-theme.css`
2. Edit to taste
3. Set in config: `"theme": "./my-theme.css"`

Or tell the AI: *"make the headings blue and use serif fonts"* — it will create and apply a custom theme for you.

## 📋 Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Skill definition — instructions for the AI |
| `setup.sh` | First-run setup script — installs Node.js dependencies |
| `render.mjs` | Core rendering engine — MD parsing, caching, PDF export |
| `default.css` | Default PDF stylesheet (GitHub-inspired) |
| `md2pdf.config.json` | Configuration template |
| `README.md` | This file |
| `LICENSE` | MIT |

## 🔧 Prerequisites

- **Node.js 18+** — Required for the rendering engine
- **LaTeX** (optional) — Only needed for the LaTeX backend. Install with `brew install --cask mactex-no-gui` (macOS) or `sudo apt install texlive` (Linux)

## License

MIT
