#!/bin/bash
# setup.sh — First-run setup for md2pdf skill
# Creates a local .md2pdf/ working directory with Node.js dependencies.
# Usage: bash <SKILL_DIR>/setup.sh [project-dir]
#
# This script is idempotent — safe to run multiple times.

set -e

PROJECT_DIR="${1:-.}"
WORK_DIR="$PROJECT_DIR/.md2pdf"
PACKAGE_JSON="$WORK_DIR/package.json"

# ─── Colors ───────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()  { echo -e "${BLUE}ℹ${NC} $1"; }
ok()    { echo -e "${GREEN}✓${NC} $1"; }
warn()  { echo -e "${YELLOW}⚠${NC} $1"; }
fail()  { echo -e "${RED}✗${NC} $1"; exit 1; }

echo ""
echo "┌──────────────────────────────────────┐"
echo "│     ✦  md2pdf — Setup               │"
echo "└──────────────────────────────────────┘"
echo ""

# ─── Check prerequisites ─────────────────────────────────────────────

info "Checking prerequisites..."

# Node.js
if ! command -v node &>/dev/null; then
    fail "Node.js is required but not installed. Install it from https://nodejs.org/ or with: brew install node"
fi

NODE_VERSION=$(node -v | sed 's/v//' | cut -d. -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    fail "Node.js 18+ is required. Current version: $(node -v)"
fi
ok "Node.js $(node -v)"

# npm
if ! command -v npm &>/dev/null; then
    fail "npm is required but not installed."
fi
ok "npm $(npm -v)"

# Optional: LaTeX
if command -v pdflatex &>/dev/null; then
    ok "LaTeX found (pdflatex) — LaTeX backend available"
    HAS_LATEX=true
elif command -v xelatex &>/dev/null; then
    ok "LaTeX found (xelatex) — LaTeX backend available"
    HAS_LATEX=true
else
    warn "LaTeX not found — only Puppeteer backend will be available"
    warn "  To enable LaTeX: brew install --cask mactex-no-gui (macOS) or apt install texlive (Linux)"
    HAS_LATEX=false
fi

# ─── Create working directory ─────────────────────────────────────────

if [ -d "$WORK_DIR" ] && [ -f "$PACKAGE_JSON" ]; then
    info "Working directory already exists at $WORK_DIR"
    info "Checking if dependencies are installed..."

    if [ -d "$WORK_DIR/node_modules/puppeteer" ]; then
        ok "Dependencies already installed. Setup is complete!"
        echo ""
        echo "  Run: node <SKILL_DIR>/render.mjs <file.md> to convert a file."
        echo ""
        exit 0
    else
        info "Dependencies missing. Reinstalling..."
    fi
else
    info "Creating working directory at $WORK_DIR ..."
    mkdir -p "$WORK_DIR"
fi

# ─── Initialize npm project ──────────────────────────────────────────

if [ ! -f "$PACKAGE_JSON" ]; then
    info "Initializing npm project..."
    cd "$WORK_DIR"
    npm init -y --silent > /dev/null 2>&1

    # Set the project as ESM
    node -e "
const pkg = require('./package.json');
pkg.name = 'md2pdf-workspace';
pkg.type = 'module';
pkg.private = true;
pkg.description = 'Local workspace for md2pdf skill dependencies';
require('fs').writeFileSync('./package.json', JSON.stringify(pkg, null, 2));
"
    cd - > /dev/null
fi

# ─── Install dependencies ────────────────────────────────────────────

info "Installing dependencies (this may take a minute on first run)..."

DEPS=(
    "puppeteer"            # Headless Chrome for HTML → PDF
    "unified"              # MD processing pipeline
    "remark-parse"         # MD → AST parser
    "remark-gfm"           # GitHub Flavored Markdown support
    "remark-rehype"        # AST → HTML AST
    "rehype-stringify"     # HTML AST → HTML string
    "rehype-raw"           # Pass-through raw HTML in MD
    "gray-matter"          # YAML frontmatter parsing
    "github-slugger"       # Heading → slug ID generation
)

cd "$WORK_DIR"
npm install --save "${DEPS[@]}" 2>&1 | tail -1
cd - > /dev/null

ok "All dependencies installed"

# ─── Add .md2pdf to .gitignore ────────────────────────────────────────

GITIGNORE="$PROJECT_DIR/.gitignore"
if [ -f "$GITIGNORE" ]; then
    if ! grep -q ".md2pdf" "$GITIGNORE" 2>/dev/null; then
        echo "" >> "$GITIGNORE"
        echo "# md2pdf working directory" >> "$GITIGNORE"
        echo ".md2pdf/" >> "$GITIGNORE"
        ok "Added .md2pdf/ to .gitignore"
    fi
else
    echo "# md2pdf working directory" > "$GITIGNORE"
    echo ".md2pdf/" >> "$GITIGNORE"
    ok "Created .gitignore with .md2pdf/"
fi

# ─── Summary ──────────────────────────────────────────────────────────

echo ""
echo "┌──────────────────────────────────────┐"
echo "│     ✓  Setup complete!               │"
echo "├──────────────────────────────────────┤"
echo "│                                      │"
echo "│  Working dir: $WORK_DIR"
echo "│  Backend:     Puppeteer (HTML→PDF)   │"
if [ "$HAS_LATEX" = true ]; then
echo "│  LaTeX:       Available              │"
else
echo "│  LaTeX:       Not available          │"
fi
echo "│                                      │"
echo "│  Usage:                              │"
echo "│  node <SKILL_DIR>/render.mjs doc.md  │"
echo "│                                      │"
echo "└──────────────────────────────────────┘"
echo ""
