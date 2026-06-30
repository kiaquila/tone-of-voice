#!/usr/bin/env node
import { execFileSync } from "node:child_process";
import { mkdirSync } from "node:fs";
import { join, resolve } from "node:path";
import { findRepoRoot, parseArgs, readConfig } from "./shared.mjs";

const args = parseArgs();
const root = findRepoRoot();
const config = readConfig(root);
const slug = String(args.slug || args._?.[0] || "").trim();

if (!slug) {
  console.error("Usage: node scripts/new-worktree.mjs --slug <feature-slug>");
  process.exit(1);
}

// Cap to 80 chars after normalization: long slugs produce unwieldy
// branch names and unwieldy worktree paths, and at some path-component
// length limit (varies by OS) `git worktree add` fails with an opaque
// error rather than the obvious "branch name too long". A hard cap here
// turns the failure mode into a clean truncation.
const safeSlug = slug
  .toLowerCase()
  .replace(/[^a-z0-9._-]+/g, "-")
  .replace(/^-+|-+$/g, "")
  .slice(0, 80)
  .replace(/^-+|-+$/g, "");
const branch = args.branch || `codex/${safeSlug}`;
const baseBranch = config.defaultBaseBranch || "main";
const base = args.base || `origin/${baseBranch}`;
const worktreeDir = resolve(root, ".claude", "worktrees", safeSlug);

mkdirSync(join(root, ".claude", "worktrees"), { recursive: true });
execFileSync("git", ["fetch", "origin", baseBranch], { cwd: root, stdio: "inherit" });
execFileSync("git", ["worktree", "add", "-b", branch, worktreeDir, base], {
  cwd: root,
  stdio: "inherit"
});

console.log(`Created worktree ${worktreeDir}`);
console.log(`Branch: ${branch}`);
