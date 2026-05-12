#!/usr/bin/env node
import { execFileSync } from "node:child_process";
import { parseArgs } from "./shared.mjs";

const args = parseArgs();
const selected = String(args.to || args._?.[0] || "").trim().toLowerCase();

if (selected !== "codex") {
  console.error("Usage: node scripts/switch-review-agent.mjs --to codex");
  console.error("tone-of-voice is codex-only for required AI Review.");
  process.exit(1);
}

execFileSync("gh", ["variable", "set", "AI_REVIEW_AGENT", "--body", selected], {
  stdio: "inherit"
});
console.log("Repository variable AI_REVIEW_AGENT set to codex.");

if (args.pr) {
  execFileSync("gh", ["pr", "comment", String(args.pr), "--body", "@codex review"], {
    stdio: "inherit"
  });
  console.log(`Posted trusted review trigger on PR ${args.pr}: @codex review`);
}
