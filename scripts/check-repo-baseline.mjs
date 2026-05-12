#!/usr/bin/env node
import { existsSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { findRepoRoot, parseArgs, readConfig } from "./shared.mjs";

const args = parseArgs();
const root = resolve(args.target || findRepoRoot());
const config = readConfig(root);
const missing = [];

function requirePath(path) {
  if (!existsSync(join(root, path))) missing.push(path);
}

for (const path of [
  "README.md",
  "AGENTS.md",
  "CLAUDE.md",
  ".unicorn-hub/config.json",
  ".specify/memory/constitution.md",
  ".specify/templates/spec-template.md",
  ".specify/templates/plan-template.md",
  ".specify/templates/tasks-template.md",
  config.docsDir || "docs",
  config.specsDir || "specs",
  "scripts/check_feature_memory.py",
  "scripts/check-repo-baseline.mjs",
  "scripts/preflight.mjs",
  ".github/workflows/ci.yml",
  ".github/workflows/pr-guard.yml",
  ".github/workflows/ai-command-policy.yml",
  ".github/workflows/ai-review.yml",
  ".github/workflows/ai-review-rerun.yml",
  ".github/workflows/osv-scan.yml"
]) {
  requirePath(path);
}

if (missing.length) {
  console.error("Missing required baseline files:");
  for (const path of missing) console.error(`- ${path}`);
  process.exit(1);
}

const requiredChecks = new Set(config.requiredChecks || []);
for (const check of ["baseline-checks", "guard", "AI Review", "osv-scan"]) {
  if (!requiredChecks.has(check)) {
    console.error(`.unicorn-hub/config.json requiredChecks must include '${check}'.`);
    process.exit(1);
  }
}

const packageJson = JSON.parse(readFileSync(join(root, "package.json"), "utf8"));
if (!packageJson.packageManager?.startsWith("pnpm@")) {
  console.error("package.json must pin packageManager to pnpm@<version>.");
  process.exit(1);
}

console.log("Repository baseline check passed.");
