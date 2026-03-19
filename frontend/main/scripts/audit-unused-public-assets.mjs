#!/usr/bin/env node
/*
  Conservatively detect unused assets under /public and optionally delete them.

  Heuristics:
  - Marks an asset as used if any source file contains:
      - `/${rel}`
      - `public/${rel}`
      - `@/public/${rel}`
      - `"${rel}"` (rare)
  - If a directory path like `/icons/global/` is referenced anywhere, all assets
    in that directory (and subdirs) are treated as used (dynamic path safety).

  Usage:
    node scripts/audit-unused-public-assets.mjs            # report only
    node scripts/audit-unused-public-assets.mjs --delete   # delete unused candidates
*/

import fs from "node:fs";
import fsp from "node:fs/promises";
import path from "node:path";

const ROOT = process.cwd();
const PUBLIC_DIR = path.join(ROOT, "public");

const args = new Set(process.argv.slice(2));
const shouldDelete = args.has("--delete") || args.has("-d");

const SKIP_PUBLIC_PREFIXES = [
  "fonts/", // usually referenced via CSS/font-face; treat as used
];

const SOURCE_DIRS = [
  "app",
  "components",
  "features",
  "lib",
  "store",
  "telegram",
  "ios",
];

const SOURCE_EXTS = new Set([
  ".js",
  ".jsx",
  ".ts",
  ".tsx",
  ".css",
  ".mjs",
  ".cjs",
  ".json",
  ".md",
  ".txt",
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

async function readAllSourceText() {
  /** @type {string[]} */
  const parts = [];

  for (const relDir of SOURCE_DIRS) {
    const absDir = path.join(ROOT, relDir);
    if (!fs.existsSync(absDir)) continue;

    const files = await listFilesRecursive(absDir);
    for (const file of files) {
      const ext = path.extname(file).toLowerCase();
      if (!SOURCE_EXTS.has(ext)) continue;

      try {
        const text = await fsp.readFile(file, "utf8");
        parts.push(text);
      } catch {}
    }
  }

  const rootFiles = await fsp.readdir(ROOT, { withFileTypes: true });
  for (const e of rootFiles) {
    if (!e.isFile()) continue;
    const ext = path.extname(e.name).toLowerCase();
    if (!SOURCE_EXTS.has(ext)) continue;
    try {
      parts.push(await fsp.readFile(path.join(ROOT, e.name), "utf8"));
    } catch {}
  }

  return parts.join("\n\n/*__FILE_SPLIT__*/\n\n");
}

function shouldSkipPublicRel(relPosix) {
  return SKIP_PUBLIC_PREFIXES.some((prefix) => relPosix.startsWith(prefix));
}

function getAllParentDirs(relPosix) {
  const dirs = [];
  const parts = relPosix.split("/");
  parts.pop();
  for (let i = 1; i <= parts.length; i++) {
    dirs.push(parts.slice(0, i).join("/") + "/");
  }
  return dirs;
}

async function main() {
  if (!fs.existsSync(PUBLIC_DIR)) {
    console.error("No public/ directory found.");
    process.exit(1);
  }

  const publicFilesAbs = (await listFilesRecursive(PUBLIC_DIR)).filter(
    (abs) => {
      const rel = toPosix(path.relative(PUBLIC_DIR, abs));
      if (!rel) return false;
      if (rel.startsWith(".")) return false;
      return true;
    },
  );

  const sourceText = await readAllSourceText();

  // Precompute which public directories are referenced (dynamic path safety)
  /** @type {Set<string>} */
  const referencedDirs = new Set();
  for (const abs of publicFilesAbs) {
    const rel = toPosix(path.relative(PUBLIC_DIR, abs));
    if (shouldSkipPublicRel(rel)) continue;

    for (const dir of getAllParentDirs(rel)) {
      const needle = "/" + dir;
      if (sourceText.includes(needle)) referencedDirs.add(dir);
    }
  }

  /** @type {{rel:string, abs:string, reason:string}[]} */
  const used = [];
  /** @type {{rel:string, abs:string, reason:string}[]} */
  const unused = [];

  for (const abs of publicFilesAbs) {
    const rel = toPosix(path.relative(PUBLIC_DIR, abs));

    if (shouldSkipPublicRel(rel)) {
      used.push({ rel, abs, reason: "skip-prefix" });
      continue;
    }

    const parentDirs = getAllParentDirs(rel);
    const isInReferencedDir = parentDirs.some((d) => referencedDirs.has(d));
    if (isInReferencedDir) {
      used.push({ rel, abs, reason: "dir-referenced" });
      continue;
    }

    const needles = [
      "/" + rel,
      "public/" + rel,
      "@/public/" + rel,
      '"' + "/" + rel + '"',
      '"' + rel + '"',
    ];

    const isUsed = needles.some((n) => sourceText.includes(n));
    if (isUsed) used.push({ rel, abs, reason: "path-match" });
    else unused.push({ rel, abs, reason: "no-match" });
  }

  /** @type {{deleted:string[], kept:string[], unusedCandidates:string[]}} */
  const report = {
    deleted: [],
    kept: [],
    unusedCandidates: unused.map((x) => x.rel),
  };

  if (shouldDelete) {
    for (const f of unused) {
      try {
        await fsp.unlink(f.abs);
        report.deleted.push(f.rel);
      } catch {
        report.kept.push(f.rel);
      }
    }

    // Clean up empty directories inside public (bottom-up)
    const allDirs = new Set(
      publicFilesAbs
        .map((abs) => path.dirname(abs))
        .filter((d) => d.startsWith(PUBLIC_DIR)),
    );
    const dirsSorted = Array.from(allDirs).sort((a, b) => b.length - a.length);
    for (const d of dirsSorted) {
      try {
        const entries = await fsp.readdir(d);
        if (entries.length === 0) await fsp.rmdir(d);
      } catch {
        // ignore
      }
    }
  }

  const reportPath = path.join(ROOT, "unused-public-assets.report.json");
  await fsp.writeFile(
    reportPath,
    JSON.stringify(report, null, 2) + "\n",
    "utf8",
  );

  console.log(
    JSON.stringify(
      {
        publicFiles: publicFilesAbs.length,
        used: used.length,
        unusedCandidates: unused.length,
        deleted: report.deleted.length,
        kept: report.kept.length,
        report: "unused-public-assets.report.json",
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
