#!/usr/bin/env node
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import {
  extractClaudeOutcome,
  isTrustedReviewLogin
} from "./ai-review-helpers.mjs";
import { readConfig } from "./shared.mjs";

const rerunnableConclusions = new Set(["failure", "cancelled", "timed_out", "action_required"]);
const activeStatuses = new Set(["queued", "in_progress", "waiting", "requested", "pending"]);

function normalizeAgent(agent) {
  return String(agent || "codex").trim().toLowerCase() || "codex";
}

function parseTime(value) {
  const time = Date.parse(value || "");
  return Number.isFinite(time) ? time : null;
}

function runFinishedAt(run) {
  return parseTime(run?.updated_at || run?.completed_at || run?.created_at);
}

export function shouldRouteAiReviewRerunEvent(event, selectedAgent = "codex", config = {}) {
  const agent = normalizeAgent(selectedAgent);

  if (event?.review) {
    if (!["codex", "gemini"].includes(agent)) return false;
    if (!isTrustedReviewLogin(event.review.user?.login, agent, config)) return false;
    // Drop stale-head reviews: a trusted bot may submit a review whose
    // commit_id is no longer the PR head (e.g. after force-push, or a
    // late delivery for a superseded SHA). Re-running ai-review.yml for
    // the current head SHA off the back of that review burns CI minutes
    // and, in adversarial timing, can keep retriggering completed runs
    // until rate limits cause a false-fail on the required check.
    const headSha = event.pull_request?.head?.sha;
    const reviewSha = event.review?.commit_id;
    if (headSha && reviewSha && reviewSha !== headSha) return false;
    return true;
  }

  // Ignore edits to issue_comment events. The original `created` event
  // already carries the gate evidence; allowing `edited` lets a trusted
  // bot (or a compromised token re-editing the bot's comment) re-trigger
  // the rerun pipeline indefinitely for the same SHA. This is paired
  // with `issue_comment.types: [created]` in ai-review-rerun.yml — both
  // layers must agree, since one layer is workflow-level and the other
  // is required-check-aware code.
  if (event?.action === "edited") return false;

  if (!event?.issue?.pull_request || !event?.comment) return false;
  const body = String(event.comment.body || "");
  const login = event.comment.user?.login;

  if (agent === "codex") {
    return /^Codex Review:/i.test(body) && isTrustedReviewLogin(login, "codex", config);
  }

  if (agent === "claude") {
    return Boolean(extractClaudeOutcome(body)) && isTrustedReviewLogin(login, "claude", config);
  }

  return false;
}

export function selectAiReviewRun(runs = [], headSha, evidenceCreatedAt = null) {
  const matchingRuns = runs
    .filter((run) => run.event === "pull_request" && run.head_sha === headSha)
    .sort((left, right) => Date.parse(right.created_at || "") - Date.parse(left.created_at || ""));

  const activeRun = matchingRuns.find((run) => activeStatuses.has(run.status));
  if (activeRun) {
    return { action: "already_running", run: activeRun };
  }

  const completedRuns = matchingRuns.filter((run) => run.status === "completed");
  const evidenceTime = parseTime(evidenceCreatedAt);
  if (evidenceTime !== null) {
    const successfulRunAfterEvidence = completedRuns.find((run) =>
      run.conclusion === "success" && (runFinishedAt(run) ?? 0) >= evidenceTime
    );
    if (successfulRunAfterEvidence) {
      return { action: "already_success", run: successfulRunAfterEvidence };
    }

    const rerunCandidate = completedRuns.find((run) =>
      run.conclusion === "success" || rerunnableConclusions.has(run.conclusion)
    );
    if (rerunCandidate) {
      return { action: "rerun", run: rerunCandidate };
    }

    return { action: "not_found", run: null };
  }

  const rerunnableRun = matchingRuns.find((run) =>
    run.status === "completed" && rerunnableConclusions.has(run.conclusion)
  );
  if (rerunnableRun) {
    return { action: "rerun", run: rerunnableRun };
  }

  const successfulRun = matchingRuns.find((run) =>
    run.status === "completed" && run.conclusion === "success"
  );
  if (successfulRun) {
    return { action: "already_success", run: successfulRun };
  }

  return { action: "not_found", run: null };
}

async function defaultRequest(token, repository, path, options = {}) {
  const response = await fetch(`https://api.github.com${path}`, {
    ...options,
    headers: {
      authorization: `Bearer ${token}`,
      accept: "application/vnd.github+json",
      "x-github-api-version": "2022-11-28",
      ...(options.headers || {})
    }
  });
  const text = await response.text();
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}: ${text}`);
  }
  return text ? JSON.parse(text) : null;
}

// Hard-cap pagination to keep this rerun helper from exhausting the
// GitHub API quota for a single job. Ten pages = 1000 workflow runs,
// which is far beyond the window where the head SHA we care about can
// still be relevant. Without a cap, a noisy workflow history can stall
// the required check long enough to hit a rate-limit-induced false-fail.
const LIST_PAGINATED_MAX_PAGES = 10;

async function listPaginated(request, token, repository, path) {
  const items = [];
  const separator = path.includes("?") ? "&" : "?";
  for (let page = 1; page <= LIST_PAGINATED_MAX_PAGES; page += 1) {
    const data = await request(token, repository, `${path}${separator}per_page=100&page=${page}`);
    const batch = data.workflow_runs || data;
    items.push(...batch);
    if (batch.length < 100) return items;
  }
  return items;
}

export async function rerunAiReviewForPrHead({
  token,
  repository,
  headSha,
  evidenceCreatedAt = null,
  request = defaultRequest
}) {
  if (!token || !repository || !headSha) {
    throw new Error("token, repository, and headSha are required to rerun AI Review.");
  }

  const [owner, repo] = repository.split("/");
  const runs = await listPaginated(
    request,
    token,
    repository,
    `/repos/${owner}/${repo}/actions/workflows/ai-review.yml/runs?event=pull_request&head_sha=${encodeURIComponent(headSha)}`
  );
  const selected = selectAiReviewRun(runs, headSha, evidenceCreatedAt);

  if (selected.action === "rerun") {
    await request(
      token,
      repository,
      `/repos/${owner}/${repo}/actions/runs/${selected.run.id}/rerun`,
      { method: "POST" }
    );
    return {
      ...selected,
      message: `Requested AI Review rerun for ${headSha} from run ${selected.run.id}.`
    };
  }

  const runId = selected.run?.id ? ` run ${selected.run.id}` : "";
  const messages = {
    already_running: `AI Review is already running for ${headSha}${runId}.`,
    already_success: `AI Review already passed for ${headSha}${runId}.`,
    not_found: `No completed AI Review pull_request run found for ${headSha}.`
  };

  return {
    ...selected,
    message: messages[selected.action]
  };
}

async function resolvePullContext({ token, repository, event, request = defaultRequest }) {
  if (event?.pull_request) {
    return {
      prNumber: event.pull_request.number,
      headSha: event.pull_request.head?.sha,
      evidenceCreatedAt: event.review?.submitted_at || null
    };
  }

  if (!event?.issue?.pull_request || !event?.issue?.number) {
    throw new Error("Could not resolve pull request from event.");
  }

  const [owner, repo] = repository.split("/");
  const pull = await request(token, repository, `/repos/${owner}/${repo}/pulls/${event.issue.number}`);
  return {
    prNumber: pull.number,
    headSha: pull.head?.sha,
    evidenceCreatedAt: event.comment?.created_at || null
  };
}

async function main() {
  const token = process.env.GITHUB_TOKEN;
  const repository = process.env.GITHUB_REPOSITORY;
  const eventPath = process.env.GITHUB_EVENT_PATH;
  const selectedAgent = normalizeAgent(process.env.AI_REVIEW_AGENT);
  const config = readConfig();

  if (!token || !repository || !eventPath) {
    console.error("GITHUB_TOKEN, GITHUB_REPOSITORY, and GITHUB_EVENT_PATH are required.");
    process.exit(1);
  }

  const event = JSON.parse(readFileSync(eventPath, "utf8"));
  if (!shouldRouteAiReviewRerunEvent(event, selectedAgent, config)) {
    console.log("AI Review rerun skipped: event is not trusted review evidence for the selected agent.");
    return;
  }

  const context = await resolvePullContext({ token, repository, event });
  const result = await rerunAiReviewForPrHead({
    token,
    repository,
    headSha: context.headSha,
    evidenceCreatedAt: context.evidenceCreatedAt
  });
  console.log(result.message);
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  try {
    await main();
  } catch (error) {
    console.error(`AI Review rerun failed: ${error.message}`);
    process.exit(1);
  }
}
