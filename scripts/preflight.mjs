#!/usr/bin/env node
import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { join } from "node:path";
import { findRepoRoot, parseArgs, walkFiles } from "./shared.mjs";

const args = parseArgs();
const root = findRepoRoot();
const python = existsSync(join(root, ".venv/bin/python"))
  ? join(root, ".venv/bin/python")
  : process.env.PYTHON || "python3";

function run(command, commandArgs, label) {
  const result = spawnSync(command, commandArgs, {
    cwd: root,
    encoding: "utf8",
    stdio: "inherit"
  });
  if (result.status !== 0) {
    console.error(`${label} failed.`);
    process.exit(result.status || 1);
  }
}

function nodeSyntaxCheck() {
  const files = walkFiles(root, {
    include: (file) => /^(scripts|tests)\/.+\.mjs$/.test(file)
  });
  for (const file of files) {
    run(process.execPath, ["--check", join(root, file)], `Node syntax: ${file}`);
  }
  console.log(`Node syntax check passed for ${files.length} files.`);
}

function pythonSyntaxCheck() {
  const files = walkFiles(root, {
    include: (file) => /^(scripts|src|tests)\/.+\.py$/.test(file)
  });
  if (!files.length) {
    console.log("No Python files found for syntax check.");
    return;
  }
  run(python, ["-m", "py_compile", ...files], "Python syntax check");
}

if (args["syntax-only"]) {
  nodeSyntaxCheck();
  pythonSyntaxCheck();
  process.exit(0);
}

run(process.execPath, ["scripts/check-repo-baseline.mjs"], "Repository baseline check");
run(python, ["scripts/check_feature_memory.py", "--worktree"], "Feature-memory check");
nodeSyntaxCheck();
pythonSyntaxCheck();
run(python, ["-m", "pytest", "tests"], "Python test suite");
run(python, ["scripts/run_regression_evals.py"], "Regression eval slice");
run(python, ["scripts/run_retrieval_experiments.py"], "Retrieval experiment slice");
run(python, ["scripts/run_generated_output_experiments.py"], "Generated-output experiment slice");

for (const script of [
  "export_telegram_posts.py",
  "build_telegram_metrics.py",
  "build_style_memory_index.py",
  "query_style_memory.py",
  "draft_post.py",
  "capture_feedback.py",
  "summarize_feedback.py",
  "run_regression_evals.py",
  "run_retrieval_experiments.py",
  "run_generated_output_experiments.py",
  "run_telegram_bot.py",
  "smoke_telegram_bot.py"
]) {
  run(python, [join("scripts", script), "--help"], `CLI help: ${script}`);
}

console.log("Preflight passed.");
