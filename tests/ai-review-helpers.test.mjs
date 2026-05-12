import test from "node:test";
import assert from "node:assert/strict";
import {
  classifyCodexNativeReview,
  createAiReviewRequestMarkerBody,
  extractAiReviewRequestMarker,
  hasHeadUpdateBetweenTimestamps,
  isAiReviewRequestMarkerComment,
  isAcceptableCodexSummaryComment,
  isTrustedAssociation,
  latestAiReviewRequestMarker
} from "../scripts/ai-review-helpers.mjs";

test("trusted actor associations are explicit", () => {
  assert.equal(isTrustedAssociation("OWNER"), true);
  assert.equal(isTrustedAssociation("MEMBER"), true);
  assert.equal(isTrustedAssociation("COLLABORATOR"), true);
  assert.equal(isTrustedAssociation("CONTRIBUTOR"), false);
});

test("AI review request markers bind trusted comments to a head SHA", () => {
  const body = createAiReviewRequestMarkerBody({
    agent: "codex",
    headSha: "abc123def456",
    requestId: "10-abc123def456",
    sourceCommentId: "10",
    sourceCommentCreatedAt: "2026-05-12T19:29:46Z",
    requestedAt: "2026-05-12T19:29:46Z"
  });

  assert.deepEqual(extractAiReviewRequestMarker(body), {
    requestId: "10-abc123def456",
    agent: "codex",
    sha: "abc123def456",
    sourceCommentId: "10",
    sourceCommentCreatedAt: "2026-05-12T19:29:46Z",
    requestedAt: "2026-05-12T19:29:46Z"
  });

  const markerComment = {
    id: 11,
    body,
    created_at: "2026-05-12T19:29:47Z",
    user: { login: "github-actions[bot]" }
  };
  assert.equal(isAiReviewRequestMarkerComment(markerComment, "codex", "abc123def456"), true);
  assert.equal(latestAiReviewRequestMarker([markerComment], "codex", "abc123def456").requestId, "10-abc123def456");
  assert.equal(isAiReviewRequestMarkerComment({
    ...markerComment,
    user: { login: "repo-owner" }
  }, "codex", "abc123def456"), false);
});

test("Codex no-findings summary requires trusted bot and matching marker when no SHA is present", () => {
  const requestMarker = {
    agent: "codex",
    sha: "abc123def456",
    requestedAt: "2026-05-12T19:29:46Z",
    sourceCommentCreatedAt: "2026-05-12T19:29:46Z",
    commentCreatedAt: "2026-05-12T19:30:00Z",
    sourceCommentId: "10"
  };

  assert.equal(
    isAcceptableCodexSummaryComment({
      body: "Codex Review: Didn't find any major issues.",
      user: { login: "chatgpt-codex-connector[bot]" },
      created_at: "2026-05-12T19:32:55Z"
    }, "abc123def456", requestMarker),
    true
  );

  assert.equal(
    isAcceptableCodexSummaryComment({
      body: "Codex Review: Didn't find any major issues.",
      user: { login: "random-user" },
      created_at: "2026-05-12T19:32:55Z"
    }, "abc123def456", requestMarker),
    false
  );

  assert.equal(
    isAcceptableCodexSummaryComment({
      body: "Codex Review: Didn't find any major issues.",
      user: { login: "chatgpt-codex-connector[bot]" },
      created_at: "2026-05-12T19:32:55Z"
    }, "abc123def456"),
    false
  );
});

test("head-update detection uses created_at boundaries", () => {
  const trigger = "2026-05-12T19:29:46Z";
  const summary = "2026-05-12T19:32:55Z";

  assert.equal(hasHeadUpdateBetweenTimestamps([
    { event: "commented", created_at: "2026-05-12T19:30:00Z" }
  ], trigger, summary), false);

  assert.equal(hasHeadUpdateBetweenTimestamps([
    { event: "committed", created_at: "2026-05-12T19:31:00Z" }
  ], trigger, summary), true);
});

test("Codex commented reviews are classified by inline priorities", () => {
  const review = {
    id: 123,
    commit_id: "abc",
    state: "COMMENTED",
    user: { login: "chatgpt-codex-connector[bot]" }
  };

  assert.equal(classifyCodexNativeReview(review, [], "abc"), "pass");
  assert.equal(classifyCodexNativeReview(review, [
    {
      pull_request_review_id: 123,
      body: "![P3 Badge] advisory",
      user: { login: "chatgpt-codex-connector[bot]" }
    }
  ], "abc"), "pass");
  assert.equal(classifyCodexNativeReview(review, [
    {
      pull_request_review_id: 123,
      body: "![P1 Badge] blocker",
      user: { login: "chatgpt-codex-connector[bot]" }
    }
  ], "abc"), "fail");
  assert.equal(classifyCodexNativeReview(review, [], "new-head"), null);
});
