#!/usr/bin/env node
import { readFileSync } from "node:fs";
import { createAiReviewRequestMarkerBody, isTrustedAssociation } from "./ai-review-helpers.mjs";
import { rerunAiReviewForPrHead } from "./ai-review-rerun.mjs";

const token = process.env.GITHUB_TOKEN;
const repository = process.env.GITHUB_REPOSITORY;
const eventPath = process.env.GITHUB_EVENT_PATH;

if (!token || !repository || !eventPath) {
  console.error("GITHUB_TOKEN, GITHUB_REPOSITORY, and GITHUB_EVENT_PATH are required.");
  process.exit(1);
}

const [owner, repo] = repository.split("/");
const event = JSON.parse(readFileSync(eventPath, "utf8"));
const body = (event.comment?.body || "").toLowerCase();
const prNumber = event.issue?.number;
const authorAssociation = event.comment?.author_association;
const commentAuthorType = event.comment?.user?.type;
const commentAuthorLogin = String(event.comment?.user?.login || "").toLowerCase();

if (commentAuthorType === "Bot" || commentAuthorLogin === "github-actions[bot]") {
  console.log("AI command ignored: comment was posted by a bot.");
  process.exit(0);
}

function requestedCommand(commandBody) {
  if (commandBody.includes("@codex review")) return { kind: "review", agent: "codex" };
  if (commandBody.includes("@claude review once")) return { kind: "review", agent: "claude" };
  if (commandBody.includes("/gemini review") || commandBody.includes("@gemini-code-assist review")) {
    return { kind: "review", agent: "gemini" };
  }
  if (commandBody.includes("@claude")) return { kind: "implementation", agent: "claude" };
  if (commandBody.includes("@codex")) return { kind: "implementation", agent: "codex" };
  return null;
}

async function request(path, options = {}) {
  const response = await fetch(`https://api.github.com${path}`, {
    ...options,
    headers: {
      authorization: `Bearer ${token}`,
      accept: "application/vnd.github+json",
      "x-github-api-version": "2022-11-28",
      ...(options.headers || {})
    }
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}: ${await response.text()}`);
  }
  if (response.status === 204) return null;
  return response.json();
}

async function createComment(commentBody) {
  return request(`/repos/${owner}/${repo}/issues/${prNumber}/comments`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ body: commentBody })
  });
}

const requested = requestedCommand(body);
if (!requested) {
  console.log("AI command ignored: no supported command was found.");
  process.exit(0);
}

const defaults = { implementation: "claude", review: "codex" };
const selected = (requested.kind === "review"
  ? process.env.AI_REVIEW_AGENT || defaults.review
  : process.env.AI_IMPLEMENTATION_AGENT || defaults.implementation).trim().toLowerCase();
const allowed = requested.kind === "review"
  ? new Set(["codex"])
  : new Set(["claude", "codex"]);

const lines = [];
if (!event.issue?.pull_request) {
  lines.push("AI command rejected: this command only runs on pull requests.");
}
if (!isTrustedAssociation(authorAssociation)) {
  lines.push("AI command rejected: only OWNER, MEMBER, and COLLABORATOR comments are trusted.");
}
if (!allowed.has(selected)) {
  lines.push(`AI command rejected: unsupported selected ${requested.kind} agent '${selected}'.`);
}
if (requested.kind === "review" && requested.agent !== selected) {
  lines.push(`AI command rejected: requested review agent '${requested.agent}' but repository policy selects '${selected}'.`);
}
if (requested.kind === "implementation" && requested.agent !== selected) {
  lines.push(`AI command rejected: requested implementation agent '${requested.agent}' but repository policy selects '${selected}'.`);
}

if (lines.length) {
  await createComment(lines.join("\n"));
  console.error(lines.join(" "));
  process.exit(1);
}

if (requested.kind === "review") {
  const pull = await request(`/repos/${owner}/${repo}/pulls/${prNumber}`);
  const headSha = pull.head?.sha;
  const sourceCommentId = String(event.comment.id);
  const requestedAt = event.comment.created_at || new Date().toISOString();
  const requestId = `${sourceCommentId}-${String(headSha).slice(0, 12)}`;

  await createComment(createAiReviewRequestMarkerBody({
    agent: selected,
    headSha,
    requestId,
    sourceCommentId,
    sourceCommentCreatedAt: event.comment.created_at,
    requestedAt
  }));

  try {
    const rerunResult = await rerunAiReviewForPrHead({
      token,
      repository,
      headSha,
      evidenceCreatedAt: requestedAt
    });
    console.log(rerunResult.message);
  } catch (error) {
    console.warn(`AI Review rerun request failed after marker was recorded: ${error.message}`);
  }
}

console.log(`Trusted AI ${requested.kind} command for ${selected}.`);
