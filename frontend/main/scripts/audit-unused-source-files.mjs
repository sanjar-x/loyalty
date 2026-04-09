#!/usr/bin/env node
/*
  Conservatively audit potentially unused source files.

  What it does:
  - Scans common source directories for JS/TS/CSS files.
  - Parses import/require/dynamic import module specifiers with simple regex.
  - Builds a reference set of resolved file paths.
  - Marks Next.js App Router entry files as used (page/layout/loading/error/route/...)
  - Outputs a JSON report with candidates that appear unreferenced.

  It does NOT delete files by default.

  Usage:
    node scripts/audit-unused-source-files.mjs

  Notes:
  - This is heuristic-based and may miss string-based/dynamic paths.
  - Treat results as candidates for manual review.
*/

import fs from "node:fs";
import fsp from "node:fs/promises";
import path from "node:path";

const ROOT = process.cwd();

const SOURCE_DIRS = [
  "app",
  "components",
  "features",
  "lib",
  "store",
  "telegram",
  "ios",
];

const EXTS = [
  ".js",
  ".jsx",
  ".ts",
  ".tsx",
  ".mjs",
  ".cjs",
  ".css",
  ".module.css",
];
const CODE_EXTS = new Set([".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"]);
const TEXT_EXTS = new Set([
  ".js",
  ".jsx",
  ".ts",
  ".tsx",
  ".mjs",
  ".cjs",
  ".css",
]);

const APP_ENTRY_BASENAMES = new Set([
  "page",
  "layout",
  "loading",
  "error",
  "not-found",
  "route",
  "template",
  "default",
]);

function toPosix(p) {
  return p.split(path.sep).join("/");
}

async function listFilesRecursive(dirAbs) {
  /** @type {string[]} */
  const out = [];
  const stack = [dirAbs];
  while (stack.length) {
    const current = stack.pop();
    let entries;
    try {
      entries = await fsp.readdir(current, { withFileTypes: true });
    } catch {
      continue;
    }

    for (const entry of entries) {
      const abs = path.join(current, entry.name);
      if (entry.isDirectory()) {
        if (
          entry.name === "node_modules" ||
          entry.name === ".next" ||
          entry.name === ".git"
        )
          continue;
        stack.push(abs);
      } else if (entry.isFile()) {
        out.push(abs);
      }
    }
  }
  return out;
}

function isSourceFile(abs) {
  const ext = path.extname(abs).toLowerCase();
  if (ext === ".css") return true;
  if (
    ext === ".js" ||
    ext === ".jsx" ||
    ext === ".ts" ||
    ext === ".tsx" ||
    ext === ".mjs" ||
    ext === ".cjs"
  )
    return true;
  return false;
}

function isAppEntryFile(abs) {
  const rel = toPosix(path.relative(ROOT, abs));
  if (!rel.startsWith("app/")) return false;

  const base = path.basename(abs);
  const name = base.replace(/\.(js|jsx|ts|tsx|mjs|cjs)$/i, "");
  if (!APP_ENTRY_BASENAMES.has(name)) return false;
  return true;
}

function stripComments(text) {
  // Very lightweight; good enough for our purposes.
  return text
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/(^|[^:])\/\/.*$/gm, "$1");
}

function extractSpecifiers(text) {
  const cleaned = stripComments(text);
  /** @type {string[]} */
  const specs = [];

  // import ... from "x" / export ... from "x"
  const reFrom =
    /\b(?:import|export)\s+(?:type\s+)?[\s\S]*?\sfrom\s*["']([^"']+)["']/g;
  for (const m of cleaned.matchAll(reFrom)) specs.push(m[1]);

  // side-effect imports: import "x";
  const reSideEffect = /\bimport\s*["']([^"']+)["']/g;
  for (const m of cleaned.matchAll(reSideEffect)) specs.push(m[1]);

  // import("x")
  const reDyn = /\bimport\s*\(\s*["']([^"']+)["']\s*\)/g;
  for (const m of cleaned.matchAll(reDyn)) specs.push(m[1]);

  // require("x")
  const reReq = /\brequire\s*\(\s*["']([^"']+)["']\s*\)/g;
  for (const m of cleaned.matchAll(reReq)) specs.push(m[1]);

  // next/font/local src: "..." or arrays won't be handled; ignore.

  return specs;
}

function candidateResolutions(importerAbs, spec) {
  // Returns absolute paths that *could* match this spec.
  /** @type {string[]} */
  const out = [];

  const addWithExts = (baseAbs) => {
    for (const ext of [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".css"]) {
      out.push(baseAbs + ext);
    }
    // Common CSS module naming when extension is omitted (rare)
    out.push(baseAbs + ".module.css");
    // index files
    for (const ext of [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"]) {
      out.push(path.join(baseAbs, "index" + ext));
    }
  };

  const specExt = path.extname(spec).toLowerCase();
  const isExplicitSourceExt =
    spec.endsWith(".module.css") ||
    [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".css"].includes(specExt);

  if (spec.startsWith("@/")) {
    const base = spec.slice(2);
    const resolvedBase = path.join(ROOT, base);
    if (isExplicitSourceExt) out.push(resolvedBase);
    else addWithExts(resolvedBase);
    return out;
  }

  if (spec.startsWith("./") || spec.startsWith("../")) {
    const resolvedBase = path.resolve(path.dirname(importerAbs), spec);
    if (isExplicitSourceExt) out.push(resolvedBase);
    else addWithExts(resolvedBase);
    return out;
  }

  // Absolute from public like "/icons/x.svg" isn't a source file.
  // Bare specifiers (react, next, etc) ignored.
  return out;
}

async function main() {
  /** @type {string[]} */
  const allSourceFiles = [];

  for (const relDir of SOURCE_DIRS) {
    const absDir = path.join(ROOT, relDir);
    if (!fs.existsSync(absDir)) continue;
    const files = await listFilesRecursive(absDir);
    for (const abs of files) {
      if (!isSourceFile(abs)) continue;
      allSourceFiles.push(abs);
    }
  }

  // Load file contents for code/text files
  /** @type {Map<string,string>} */
  const contents = new Map();
  for (const abs of allSourceFiles) {
    const ext = path.extname(abs).toLowerCase();
    if (!TEXT_EXTS.has(ext)) continue;
    try {
      contents.set(abs, await fsp.readFile(abs, "utf8"));
    } catch {
      // ignore
    }
  }

  /** @type {Set<string>} */
  const referenced = new Set();

  // All app entry files are considered referenced
  for (const abs of allSourceFiles) {
    if (isAppEntryFile(abs)) referenced.add(abs);
  }

  // Add explicit references via imports/requires
  for (const [importerAbs, text] of contents.entries()) {
    const ext = path.extname(importerAbs).toLowerCase();
    if (!CODE_EXTS.has(ext) && ext !== ".css") continue;

    const specs = extractSpecifiers(text);
    for (const spec of specs) {
      const cands = candidateResolutions(importerAbs, spec);
      for (const cand of cands) referenced.add(path.normalize(cand));
    }
  }

  // Normalize file list for set membership
  const allSet = new Set(allSourceFiles.map((p) => path.normalize(p)));

  // Keep only referenced paths that actually exist in our source set
  const referencedExisting = new Set();
  for (const p of referenced) {
    const norm = path.normalize(p);
    if (allSet.has(norm)) referencedExisting.add(norm);
  }

  /** @type {{rel:string, reason:string}[]} */
  const candidates = [];
  for (const abs of allSet) {
    if (referencedExisting.has(abs)) continue;

    // Always keep app router special files even if not detected (already handled)
    if (isAppEntryFile(abs)) continue;

    const rel = toPosix(path.relative(ROOT, abs));

    // Keep any file under app/ that isn't one of the known entry names: could be used by route group layouts etc.
    if (rel.startsWith("app/")) {
      candidates.push({ rel, reason: "unreferenced-non-entry-under-app" });
      continue;
    }

    candidates.push({ rel, reason: "unreferenced" });
  }

  // Conservative filter: do not suggest deletion for app/* candidates; report them separately.
  const appCandidates = candidates.filter((c) => c.rel.startsWith("app/"));
  const otherCandidates = candidates.filter((c) => !c.rel.startsWith("app/"));

  const report = {
    totalSourceFiles: allSourceFiles.length,
    referenced: referencedExisting.size,
    candidates: {
      app: appCandidates,
      other: otherCandidates,
    },
  };

  const reportPath = path.join(ROOT, "unused-source-files.report.json");
  await fsp.writeFile(
    reportPath,
    JSON.stringify(report, null, 2) + "\n",
    "utf8",
  );

  console.log(
    JSON.stringify(
      {
        totalSourceFiles: report.totalSourceFiles,
        referenced: report.referenced,
        candidateOther: otherCandidates.length,
        candidateApp: appCandidates.length,
        report: "unused-source-files.report.json",
      },
      null,
      2,
    ),
  );
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
