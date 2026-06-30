#!/usr/bin/env node
import { execFileSync } from "node:child_process";
import { findRepoRoot, parseArgs, readConfig } from "./shared.mjs";

// Branch-protection apply is destructive: GitHub's PUT replaces the entire
// protection payload, so any field we omit silently reverts to its absent
// state. We add three guard rails before the PUT:
//   1. --dry-run — print the diff against the current protection and exit
//      without calling the API. Safe for verification in CI or local trials.
//   2. Downgrade detection — if the proposed required_status_checks
//      contexts are a strict subset of the current ones, OR the proposed
//      required_approving_review_count is lower than the current one,
//      refuse to apply unless --confirm is passed. This prevents an
//      accidental empty `--checks` from wiping out the required AI Review
//      / baseline / OSV gates, which would be a silent merge-bypass class.
//   3. Diff print on every run — even non-downgrade applies show what
//      changes, so operators can spot drift between .unicorn-hub/config.json
//      and the live protection rule.

const args = parseArgs();
const root = findRepoRoot();
const config = readConfig(root);
const branch = args.branch || config.defaultBaseBranch || "main";
const checks = String(args.checks || (config.requiredChecks || []).join(","))
  .split(",")
  .map((item) => item.trim())
  .filter(Boolean);
const approvals = Number(args.approvals || 0);
const dryRun = args["dry-run"] === true || args["dry-run"] === "true";
const confirmed = args.confirm === true || args.confirm === "true";

const repo = args.repo || execFileSync("gh", ["repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"], {
  cwd: root,
  encoding: "utf8"
}).trim();

function readCurrentProtection(repository, targetBranch) {
  try {
    const out = execFileSync(
      "gh",
      ["api", `/repos/${repository}/branches/${targetBranch}/protection`],
      { cwd: root, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }
    );
    return JSON.parse(out);
  } catch (error) {
    const stderr = String(error?.stderr || error?.message || "");
    // First-time application: no protection yet on this branch. Treat the
    // current state as "no protection" so the operator sees a full diff
    // of what is about to be set.
    if (/HTTP 404/i.test(stderr) || /not found/i.test(stderr)) return null;
    throw error;
  }
}

const current = readCurrentProtection(repo, branch);
const currentContexts = new Set(current?.required_status_checks?.contexts || []);
const proposedContexts = new Set(checks);
const removedChecks = [...currentContexts].filter((value) => !proposedContexts.has(value));
const addedChecks = [...proposedContexts].filter((value) => !currentContexts.has(value));
const currentApprovals = current?.required_pull_request_reviews?.required_approving_review_count ?? 0;
const isDowngrade = removedChecks.length > 0 || approvals < currentApprovals;

const payload = {
  required_status_checks: {
    strict: args.strict === "true",
    contexts: checks
  },
  enforce_admins: true,
  required_pull_request_reviews: {
    dismiss_stale_reviews: true,
    require_code_owner_reviews: false,
    required_approving_review_count: approvals,
    require_last_push_approval: false
  },
  restrictions: null,
  required_conversation_resolution: args.conversations !== "false",
  allow_force_pushes: false,
  allow_deletions: false,
  required_linear_history: false
};

console.log(`Target: ${repo}:${branch}`);
console.log(`Current required checks: [${[...currentContexts].sort().join(", ") || "<none>"}]`);
console.log(`Proposed required checks: [${[...proposedContexts].sort().join(", ") || "<none>"}]`);
if (addedChecks.length) console.log(`  + added: ${addedChecks.sort().join(", ")}`);
if (removedChecks.length) console.log(`  - removed: ${removedChecks.sort().join(", ")}`);
console.log(`Required approvals: current=${currentApprovals}, proposed=${approvals}`);

if (dryRun) {
  console.log("\n--dry-run: no changes applied.");
  console.log("Payload:");
  console.log(JSON.stringify(payload, null, 2));
  process.exit(0);
}

if (isDowngrade && !confirmed) {
  const reasons = [];
  if (removedChecks.length) reasons.push(`removes required checks [${removedChecks.sort().join(", ")}]`);
  if (approvals < currentApprovals) reasons.push(`lowers required approvals from ${currentApprovals} to ${approvals}`);
  console.error(
    `\nERROR: Refusing to apply a downgrade of branch protection on ${repo}:${branch}.\n` +
    `Reason: ${reasons.join("; ")}.\n` +
    "Pass --confirm if this is intentional, or use --dry-run to inspect the diff."
  );
  process.exit(1);
}

execFileSync("gh", [
  "api",
  "--method",
  "PUT",
  `/repos/${repo}/branches/${branch}/protection`,
  "--input",
  "-"
], {
  input: JSON.stringify(payload),
  encoding: "utf8",
  stdio: ["pipe", "inherit", "inherit"]
});

console.log(`Applied branch protection to ${repo}:${branch}`);
