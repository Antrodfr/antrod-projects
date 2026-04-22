#!/usr/bin/env node
/**
 * render.mjs — MD → PDF rendering engine with incremental section caching.
 *
 * Usage:
 *   node render.mjs <input.md> [options]
 *
 * Options:
 *   --output, -o <file>       Output PDF path (default: <input>.pdf)
 *   --backend, -b <name>      Rendering backend: puppeteer (default) or latex
 *   --incremental, -i         Only re-render changed sections (uses cache)
 *   --full                    Force full re-render (ignore cache)
 *   --theme, -t <file>        Custom CSS theme file
 *   --config, -c <file>       Config file path (default: md2pdf.config.json)
 *   --section <id>            Re-render only the specified section by slug ID
 *   --list-sections           List all sections with their IDs and hashes
 *   --cache-dir <dir>         Cache directory (default: .md2pdf/cache)
 *   --open                    Open PDF after rendering (macOS: open, Linux: xdg-open)
 *   --quiet, -q               Suppress output except errors
 *
 * The script works by:
 * 1. Parsing the MD file into sections (split on H1/H2 headings)
 * 2. Hashing each section's content
 * 3. Comparing hashes with the cache to find changed sections
 * 4. Re-rendering only changed sections to HTML
 * 5. Assembling the full HTML document with CSS
 * 6. Exporting to PDF via Puppeteer (or LaTeX)
 *
 * Cache structure:
 *   .md2pdf/cache/
 *     manifest.json       — { sections: [{ id, hash, index }], fullHash }
 *     sections/
 *       01-intro.html     — Cached HTML fragment per section
 *       02-problem.html
 *     assembled.html      — Last full assembled HTML
 *     last-render.pdf     — Last generated PDF
 */

import { readFileSync, writeFileSync, mkdirSync, existsSync, readdirSync, unlinkSync } from "node:fs";
import { resolve, dirname, basename, extname, join } from "node:path";
import { createHash } from "node:crypto";
import { execSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// ─── Argument parsing ────────────────────────────────────────────────

function parseArgs(argv) {
  const args = {
    input: null,
    output: null,
    backend: "puppeteer",
    incremental: true,
    full: false,
    theme: null,
    config: null,
    section: null,
    listSections: false,
    cacheDir: null,
    open: false,
    quiet: false,
  };

  const positional = [];
  for (let i = 2; i < argv.length; i++) {
    const arg = argv[i];
    switch (arg) {
      case "--output":
      case "-o":
        args.output = argv[++i];
        break;
      case "--backend":
      case "-b":
        args.backend = argv[++i];
        break;
      case "--incremental":
      case "-i":
        args.incremental = true;
        break;
      case "--full":
        args.full = true;
        args.incremental = false;
        break;
      case "--theme":
      case "-t":
        args.theme = argv[++i];
        break;
      case "--config":
      case "-c":
        args.config = argv[++i];
        break;
      case "--section":
        args.section = argv[++i];
        break;
      case "--list-sections":
        args.listSections = true;
        break;
      case "--cache-dir":
        args.cacheDir = argv[++i];
        break;
      case "--open":
        args.open = true;
        break;
      case "--quiet":
      case "-q":
        args.quiet = true;
        break;
      default:
        if (!arg.startsWith("-")) positional.push(arg);
        break;
    }
  }

  args.input = positional[0] || null;
  return args;
}

// ─── Config loading ──────────────────────────────────────────────────

function loadConfig(configPath) {
  const defaults = {
    backend: "puppeteer",
    puppeteer: {
      format: "A4",
      margin: { top: "25mm", right: "20mm", bottom: "25mm", left: "20mm" },
      printBackground: true,
      displayHeaderFooter: false,
      headerTemplate: "<span></span>",
      footerTemplate:
        '<div style="font-size:9px;color:#6b7280;width:100%;text-align:center;padding:0 20mm;"><span class="pageNumber"></span> / <span class="totalPages"></span></div>',
    },
    theme: null,
    output: { directory: ".", filename: null },
    cache: { enabled: true, directory: ".md2pdf/cache" },
    sections: { splitOn: ["h1", "h2"], pageBreakBefore: ["h1"] },
  };

  const searchPaths = configPath
    ? [configPath]
    : ["md2pdf.config.json", ".md2pdf/config.json"];

  for (const p of searchPaths) {
    if (existsSync(p)) {
      try {
        const userConfig = JSON.parse(readFileSync(p, "utf-8"));
        return deepMerge(defaults, userConfig);
      } catch {
        // Ignore invalid config, use defaults
      }
    }
  }
  return defaults;
}

function deepMerge(target, source) {
  const result = { ...target };
  for (const key of Object.keys(source)) {
    if (key.startsWith("$") || key.startsWith("_")) continue;
    if (
      source[key] &&
      typeof source[key] === "object" &&
      !Array.isArray(source[key])
    ) {
      result[key] = deepMerge(target[key] || {}, source[key]);
    } else {
      result[key] = source[key];
    }
  }
  return result;
}

// ─── Frontmatter parsing ────────────────────────────────────────────

function parseFrontmatter(content) {
  const match = content.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
  if (!match) return { frontmatter: {}, body: content };

  const yamlStr = match[1];
  const body = match[2];
  const frontmatter = {};

  for (const line of yamlStr.split("\n")) {
    const kv = line.match(/^(\w[\w-]*):\s*(.+)$/);
    if (kv) frontmatter[kv[1]] = kv[2].trim();
  }

  return { frontmatter, body };
}

// ─── Section splitting ───────────────────────────────────────────────

function slugify(text) {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .trim();
}

function splitIntoSections(markdown, splitOn = ["h1", "h2"]) {
  const lines = markdown.split("\n");
  const sections = [];
  let currentLines = [];
  let currentHeading = null;
  let currentLevel = 0;
  let index = 0;

  const headingPattern = splitOn.includes("h1") && splitOn.includes("h2")
    ? /^(#{1,2})\s+(.+)$/
    : splitOn.includes("h1")
      ? /^(#)\s+(.+)$/
      : /^(##)\s+(.+)$/;

  function flushSection() {
    if (currentLines.length > 0 || currentHeading) {
      const content = currentLines.join("\n").trim();
      if (content) {
        const id = currentHeading
          ? `${String(index).padStart(2, "0")}-${slugify(currentHeading)}`
          : `${String(index).padStart(2, "0")}-preamble`;
        sections.push({
          id,
          heading: currentHeading,
          level: currentLevel,
          content,
          hash: hashContent(content),
          index,
        });
        index++;
      }
    }
  }

  for (const line of lines) {
    const match = line.match(headingPattern);
    if (match) {
      flushSection();
      currentLines = [line];
      currentHeading = match[2].trim();
      currentLevel = match[1].length;
    } else {
      currentLines.push(line);
    }
  }
  flushSection();

  return sections;
}

function hashContent(content) {
  return createHash("sha256").update(content).digest("hex").slice(0, 12);
}

// ─── HTML rendering (per section) ────────────────────────────────────

async function loadMarkdownPipeline(workDir) {
  const modulesDir = join(workDir, "node_modules");

  const { unified } = await import(join(modulesDir, "unified", "index.js"));
  const remarkParse = (await import(join(modulesDir, "remark-parse", "index.js"))).default;
  const remarkGfm = (await import(join(modulesDir, "remark-gfm", "index.js"))).default;
  const remarkRehype = (await import(join(modulesDir, "remark-rehype", "index.js"))).default;
  const rehypeRaw = (await import(join(modulesDir, "rehype-raw", "index.js"))).default;
  const rehypeStringify = (await import(join(modulesDir, "rehype-stringify", "index.js"))).default;

  return unified()
    .use(remarkParse)
    .use(remarkGfm)
    .use(remarkRehype, { allowDangerousHtml: true })
    .use(rehypeRaw)
    .use(rehypeStringify);
}

async function renderSectionToHtml(pipeline, section) {
  const result = await pipeline.process(section.content);
  return `<section data-section="${section.id}" data-hash="${section.hash}">\n${String(result)}\n</section>`;
}

// ─── HTML assembly ───────────────────────────────────────────────────

function assembleHtml(sectionHtmls, cssContent, frontmatter = {}) {
  const title = frontmatter.title || "Document";
  const author = frontmatter.author || "";
  const date = frontmatter.date || "";

  let headerBlock = "";
  if (frontmatter.title) {
    headerBlock = `
    <header class="doc-header">
      <h1 class="doc-title">${title}</h1>
      ${author ? `<p class="doc-author">${author}</p>` : ""}
      ${date ? `<p class="doc-date">${date}</p>` : ""}
    </header>`;
  }

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${title}</title>
  <style>
${cssContent}

/* ─── Document header ─── */
.doc-header { text-align: center; margin-bottom: 2em; }
.doc-title { font-size: 2.5em; border: none; page-break-before: avoid; }
.doc-author { color: #59636e; font-size: 1.1em; margin: 0.25em 0; }
.doc-date { color: #6b7280; font-size: 0.95em; margin: 0.25em 0; }
  </style>
</head>
<body>
${headerBlock}
${sectionHtmls.join("\n\n")}
</body>
</html>`;
}

// ─── Cache management ────────────────────────────────────────────────

function loadManifest(cacheDir) {
  const manifestPath = join(cacheDir, "manifest.json");
  if (existsSync(manifestPath)) {
    try {
      return JSON.parse(readFileSync(manifestPath, "utf-8"));
    } catch {
      return { sections: [], fullHash: null };
    }
  }
  return { sections: [], fullHash: null };
}

function saveManifest(cacheDir, manifest) {
  mkdirSync(cacheDir, { recursive: true });
  writeFileSync(join(cacheDir, "manifest.json"), JSON.stringify(manifest, null, 2));
}

function getCachedSectionHtml(cacheDir, sectionId) {
  const path = join(cacheDir, "sections", `${sectionId}.html`);
  if (existsSync(path)) return readFileSync(path, "utf-8");
  return null;
}

function saveSectionHtml(cacheDir, sectionId, html) {
  const sectionsDir = join(cacheDir, "sections");
  mkdirSync(sectionsDir, { recursive: true });
  writeFileSync(join(sectionsDir, `${sectionId}.html`), html);
}

function cleanStaleSections(cacheDir, currentSectionIds) {
  const sectionsDir = join(cacheDir, "sections");
  if (!existsSync(sectionsDir)) return;

  const currentSet = new Set(currentSectionIds);
  for (const file of readdirSync(sectionsDir)) {
    const id = file.replace(/\.html$/, "");
    if (!currentSet.has(id)) {
      unlinkSync(join(sectionsDir, file));
    }
  }
}

// ─── Puppeteer PDF export ────────────────────────────────────────────

async function exportPdfPuppeteer(html, outputPath, config, workDir) {
  const puppeteerPath = join(workDir, "node_modules", "puppeteer");
  const puppeteer = await import(join(puppeteerPath, "lib/esm/puppeteer/puppeteer.js"));
  const browser = await puppeteer.launch({ headless: true, args: ["--no-sandbox"] });

  try {
    const page = await browser.newPage();
    await page.setContent(html, { waitUntil: "networkidle0" });

    const pdfOptions = {
      path: outputPath,
      format: config.puppeteer.format,
      margin: config.puppeteer.margin,
      printBackground: config.puppeteer.printBackground,
      displayHeaderFooter: config.puppeteer.displayHeaderFooter,
    };

    if (config.puppeteer.displayHeaderFooter) {
      pdfOptions.headerTemplate = config.puppeteer.headerTemplate;
      pdfOptions.footerTemplate = config.puppeteer.footerTemplate;
    }

    await page.pdf(pdfOptions);
  } finally {
    await browser.close();
  }
}

// ─── LaTeX export ────────────────────────────────────────────────────

function markdownToLatex(markdown) {
  // Lightweight MD → LaTeX conversion for basic elements
  let tex = markdown;

  // Headings
  tex = tex.replace(/^# (.+)$/gm, "\\section{$1}");
  tex = tex.replace(/^## (.+)$/gm, "\\subsection{$1}");
  tex = tex.replace(/^### (.+)$/gm, "\\subsubsection{$1}");
  tex = tex.replace(/^#### (.+)$/gm, "\\paragraph{$1}");

  // Bold and italic
  tex = tex.replace(/\*\*(.+?)\*\*/g, "\\textbf{$1}");
  tex = tex.replace(/\*(.+?)\*/g, "\\textit{$1}");

  // Inline code
  tex = tex.replace(/`([^`]+)`/g, "\\texttt{$1}");

  // Code blocks
  tex = tex.replace(/```[\w]*\n([\s\S]*?)```/g, "\\begin{verbatim}\n$1\\end{verbatim}");

  // Unordered lists
  tex = tex.replace(/^- (.+)$/gm, "\\item $1");
  // Wrap consecutive \item lines in itemize
  tex = tex.replace(/((?:^\\item .+\n?)+)/gm, "\\begin{itemize}\n$1\\end{itemize}\n");

  // Blockquotes
  tex = tex.replace(/^> (.+)$/gm, "\\begin{quote}\n$1\n\\end{quote}");

  // Horizontal rules
  tex = tex.replace(/^---+$/gm, "\\hrulefill");

  // Escape special LaTeX characters in remaining text (simplified)
  // Note: this is intentionally minimal — complex docs should use Puppeteer
  tex = tex.replace(/&/g, "\\&");
  tex = tex.replace(/%/g, "\\%");

  return tex;
}

function assembleLatex(sectionTexts, frontmatter = {}) {
  const title = frontmatter.title || "Document";
  const author = frontmatter.author || "";
  const date = frontmatter.date || "\\today";

  return `\\documentclass[11pt,a4paper]{article}
\\usepackage[margin=25mm]{geometry}
\\usepackage[utf8]{inputenc}
\\usepackage[T1]{fontenc}
\\usepackage{hyperref}
\\usepackage{graphicx}
\\usepackage{enumitem}
\\usepackage{fancyhdr}
\\usepackage{xcolor}

\\title{${title}}
\\author{${author}}
\\date{${date}}

\\pagestyle{fancy}
\\fancyhf{}
\\rfoot{\\thepage}
\\renewcommand{\\headrulewidth}{0pt}

\\begin{document}
${frontmatter.title ? "\\maketitle" : ""}

${sectionTexts.join("\n\n")}

\\end{document}
`;
}

function exportPdfLatex(texContent, outputPath) {
  const tempDir = dirname(outputPath);
  const texFile = join(tempDir, ".md2pdf-temp.tex");

  writeFileSync(texFile, texContent);

  const engine = existsSync("/usr/bin/xelatex") || existsSync("/usr/local/bin/xelatex")
    ? "xelatex"
    : "pdflatex";

  try {
    // Run twice for references
    execSync(`${engine} -interaction=nonstopmode -output-directory="${tempDir}" "${texFile}"`, {
      stdio: "pipe",
    });
    execSync(`${engine} -interaction=nonstopmode -output-directory="${tempDir}" "${texFile}"`, {
      stdio: "pipe",
    });

    const generatedPdf = join(tempDir, ".md2pdf-temp.pdf");
    if (existsSync(generatedPdf)) {
      execSync(`mv "${generatedPdf}" "${outputPath}"`);
    }
  } finally {
    // Cleanup temp files
    for (const ext of [".tex", ".aux", ".log", ".out", ".toc"]) {
      const f = join(tempDir, `.md2pdf-temp${ext}`);
      if (existsSync(f)) unlinkSync(f);
    }
  }
}

// ─── Main ────────────────────────────────────────────────────────────

async function main() {
  const args = parseArgs(process.argv);
  const log = args.quiet ? () => {} : console.log;
  const startTime = Date.now();

  // Validate input
  if (!args.input && !args.listSections) {
    console.error("Usage: node render.mjs <input.md> [options]");
    console.error("       node render.mjs --help for more information");
    process.exit(1);
  }

  if (!args.input || !existsSync(args.input)) {
    console.error(`Error: Input file not found: ${args.input}`);
    process.exit(1);
  }

  // Load config
  const config = loadConfig(args.config);
  const backend = args.backend || config.backend || "puppeteer";

  // Resolve paths
  const inputPath = resolve(args.input);
  const inputDir = dirname(inputPath);
  const inputName = basename(inputPath, extname(inputPath));
  const outputPath = args.output
    ? resolve(args.output)
    : resolve(config.output.directory || ".", config.output.filename || `${inputName}.pdf`);
  const cacheDir = resolve(args.cacheDir || config.cache.directory || ".md2pdf/cache");
  const workDir = resolve(".md2pdf");

  // Check work directory exists
  if (!existsSync(workDir) || !existsSync(join(workDir, "node_modules"))) {
    console.error("Error: md2pdf is not set up. Run setup.sh first:");
    console.error(`  bash <SKILL_DIR>/setup.sh`);
    process.exit(1);
  }

  // Read and parse input
  const rawContent = readFileSync(inputPath, "utf-8");
  const { frontmatter, body } = parseFrontmatter(rawContent);
  const splitOn = config.sections.splitOn || ["h1", "h2"];
  const sections = splitIntoSections(body, splitOn);

  // ─── List sections mode ────────────────────────────────────────
  if (args.listSections) {
    log("Sections found:\n");
    for (const s of sections) {
      const level = "#".repeat(s.level || 0);
      log(`  ${s.id}  [${s.hash}]  ${level} ${s.heading || "(preamble)"}`);
    }
    log(`\nTotal: ${sections.length} sections`);
    return;
  }

  // ─── Determine what changed ────────────────────────────────────
  const manifest = loadManifest(cacheDir);
  const oldSectionMap = new Map(manifest.sections.map((s) => [s.id, s.hash]));

  let changedSections;
  let unchangedSections;

  if (args.full || !config.cache.enabled) {
    changedSections = sections;
    unchangedSections = [];
    log("🔄 Full render (cache bypassed)");
  } else if (args.section) {
    const target = sections.find((s) => s.id === args.section || s.heading === args.section);
    if (!target) {
      console.error(`Error: Section not found: ${args.section}`);
      console.error("Use --list-sections to see available sections.");
      process.exit(1);
    }
    changedSections = [target];
    unchangedSections = sections.filter((s) => s.id !== target.id);
    log(`🎯 Targeting section: ${target.id}`);
  } else {
    changedSections = sections.filter((s) => oldSectionMap.get(s.id) !== s.hash);
    unchangedSections = sections.filter((s) => oldSectionMap.get(s.id) === s.hash);
  }

  const totalSections = sections.length;
  const changedCount = changedSections.length;

  if (changedCount === 0 && existsSync(join(cacheDir, "..", "cache", "..", "cache", "manifest.json") ? outputPath : outputPath)) {
    if (existsSync(outputPath)) {
      log("✓ No changes detected. PDF is up to date.");
      if (args.open) openFile(outputPath);
      return;
    }
  }

  if (changedCount < totalSections && changedCount > 0) {
    log(`⚡ Incremental: ${changedCount}/${totalSections} sections changed`);
  } else if (changedCount === totalSections) {
    log(`🔄 Full render: ${totalSections} sections`);
  }

  // ─── Render sections to HTML ───────────────────────────────────

  if (backend === "puppeteer" || backend === "html") {
    const pipeline = await loadMarkdownPipeline(workDir);
    const sectionHtmls = [];

    for (const section of sections) {
      const isChanged = changedSections.some((s) => s.id === section.id);

      if (isChanged) {
        const html = await renderSectionToHtml(pipeline, section);
        saveSectionHtml(cacheDir, section.id, html);
        sectionHtmls.push(html);
        if (!args.quiet && changedCount < totalSections) {
          log(`  ✎ Re-rendered: ${section.id}`);
        }
      } else {
        const cached = getCachedSectionHtml(cacheDir, section.id);
        if (cached) {
          sectionHtmls.push(cached);
        } else {
          // Cache miss — render anyway
          const html = await renderSectionToHtml(pipeline, section);
          saveSectionHtml(cacheDir, section.id, html);
          sectionHtmls.push(html);
        }
      }
    }

    // Load CSS theme
    const themePath = args.theme || config.theme || join(__dirname, "default.css");
    const cssContent = existsSync(themePath)
      ? readFileSync(themePath, "utf-8")
      : readFileSync(join(__dirname, "default.css"), "utf-8");

    // Assemble full HTML
    const fullHtml = assembleHtml(sectionHtmls, cssContent, frontmatter);
    mkdirSync(dirname(outputPath), { recursive: true });

    // Save assembled HTML (for debugging / cache)
    const assembledPath = join(cacheDir, "assembled.html");
    mkdirSync(dirname(assembledPath), { recursive: true });
    writeFileSync(assembledPath, fullHtml);

    // Export PDF
    log("📄 Generating PDF...");
    await exportPdfPuppeteer(fullHtml, outputPath, config, workDir);

  } else if (backend === "latex") {
    const sectionTexts = [];

    for (const section of sections) {
      const tex = markdownToLatex(section.content);
      sectionTexts.push(`% ── Section: ${section.id} ──\n${tex}`);
    }

    const fullTex = assembleLatex(sectionTexts, frontmatter);
    log("📄 Generating PDF via LaTeX...");
    exportPdfLatex(fullTex, outputPath);

  } else {
    console.error(`Error: Unknown backend: ${backend}`);
    process.exit(1);
  }

  // ─── Update cache manifest ─────────────────────────────────────

  const newManifest = {
    sections: sections.map((s) => ({ id: s.id, hash: s.hash, index: s.index })),
    fullHash: hashContent(rawContent),
    lastRender: new Date().toISOString(),
    backend,
  };
  saveManifest(cacheDir, newManifest);

  // Clean stale cached sections
  cleanStaleSections(cacheDir, sections.map((s) => s.id));

  // ─── Done ──────────────────────────────────────────────────────

  const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
  log(`✓ PDF saved: ${outputPath} (${elapsed}s)`);

  if (args.open) openFile(outputPath);
}

function openFile(path) {
  try {
    const cmd = process.platform === "darwin" ? "open" : "xdg-open";
    execSync(`${cmd} "${path}"`, { stdio: "ignore" });
  } catch {
    // Silently fail if unable to open
  }
}

main().catch((err) => {
  console.error("Error:", err.message || err);
  process.exit(1);
});
