import test from "node:test";
import assert from "node:assert/strict";
import {
  rerunAiReviewForPrHead,
  selectAiReviewRun,
  shouldRouteAiReviewRerunEvent
} from "../scripts/ai-review-rerun.mjs";

test("AI Review rerun event filter accepts trusted selected-agent evidence", () => {
  assert.equal(
    shouldRouteAiReviewRerunEvent(
      {
        issue: { pull_request: {} },
        comment: {
          body: "Codex Review: Didn't find any major issues.",
          user: { login: "chatgpt-codex-connector[bot]" }
        }
      },
      "codex"
    ),
    true
  );

  assert.equal(
    shouldRouteAiReviewRerunEvent(
      {
        issue: { pull_request: {} },
        comment: {
          body: "Codex Review: Didn't find any major issues.",
          user: { login: "random-user" }
        }
      },
      "codex"
    ),
    false
  );
});

test("AI Review rerun event filter rejects edited issue_comment events", () => {
  // Even a trusted bot's edited comment must not retrigger rerun: the
  // creation event already carried the gate evidence, and an edited
  // event lets a bot (or a compromised token) loop the rerun pipeline
  // by re-editing the same comment.
  assert.equal(
    shouldRouteAiReviewRerunEvent(
      {
        action: "edited",
        issue: { pull_request: {} },
        comment: {
          body: "Codex Review: Didn't find any major issues.",
          user: { login: "chatgpt-codex-connector[bot]" }
        }
      },
      "codex"
    ),
    false
  );

  // `created` (or any non-edited) action still routes.
  assert.equal(
    shouldRouteAiReviewRerunEvent(
      {
        action: "created",
        issue: { pull_request: {} },
        comment: {
          body: "Codex Review: Didn't find any major issues.",
          user: { login: "chatgpt-codex-connector[bot]" }
        }
      },
      "codex"
    ),
    true
  );
});

test("AI Review rerun event filter rejects stale-head reviews", () => {
  // A trusted bot review whose commit_id is not the current PR head SHA
  // must NOT trigger a rerun. Otherwise an old review delivered late
  // (e.g. after a force-push) would burn a rerun against the wrong
  // workflow run and, in adversarial timing, keep retriggering until
  // rate limits cause a false-fail on the required check.
  assert.equal(
    shouldRouteAiReviewRerunEvent(
      {
        pull_request: { head: { sha: "newhead" } },
        review: {
          commit_id: "oldhead",
          user: { login: "chatgpt-codex-connector[bot]" }
        }
      },
      "codex"
    ),
    false
  );

  // Same review on the current head still routes.
  assert.equal(
    shouldRouteAiReviewRerunEvent(
      {
        pull_request: { head: { sha: "newhead" } },
        review: {
          commit_id: "newhead",
          user: { login: "chatgpt-codex-connector[bot]" }
        }
      },
      "codex"
    ),
    true
  );

  // Untrusted reviewer with matching SHA must still be rejected — the
  // trust check is independent of the SHA check.
  assert.equal(
    shouldRouteAiReviewRerunEvent(
      {
        pull_request: { head: { sha: "newhead" } },
        review: {
          commit_id: "newhead",
          user: { login: "random-user" }
        }
      },
      "codex"
    ),
    false
  );
});

test("AI Review rerun selector ignores dispatch runs and reports success states", () => {
  const successRun = {
    id: 11,
    event: "pull_request",
    head_sha: "abc",
    status: "completed",
    conclusion: "success",
    created_at: "2026-05-12T09:00:00Z"
  };
  assert.deepEqual(selectAiReviewRun([successRun], "abc"), {
    action: "already_success",
    run: successRun
  });

  const dispatchRun = {
    id: 12,
    event: "workflow_dispatch",
    head_sha: "abc",
    status: "completed",
    conclusion: "failure",
    created_at: "2026-05-12T09:30:00Z"
  };
  assert.deepEqual(
    selectAiReviewRun([dispatchRun], "abc"),
    { action: "not_found", run: null }
  );
});

test("AI Review rerun selector reruns prior success after newer trusted evidence", () => {
  const priorSuccess = {
    id: 21,
    event: "pull_request",
    head_sha: "abc",
    status: "completed",
    conclusion: "success",
    created_at: "2026-05-12T10:00:00Z",
    updated_at: "2026-05-12T10:01:00Z"
  };

  assert.deepEqual(
    selectAiReviewRun([priorSuccess], "abc", "2026-05-12T10:05:00Z"),
    { action: "rerun", run: priorSuccess }
  );

  const laterSuccess = {
    ...priorSuccess,
    id: 22,
    created_at: "2026-05-12T10:10:00Z",
    updated_at: "2026-05-12T10:11:00Z"
  };

  assert.deepEqual(
    selectAiReviewRun([priorSuccess, laterSuccess], "abc", "2026-05-12T10:05:00Z"),
    { action: "already_success", run: laterSuccess }
  );
});

test("AI Review rerun selector prefers active runs, then latest rerunnable failures", () => {
  const runs = [
    {
      id: 1,
      event: "pull_request",
      head_sha: "abc",
      status: "completed",
      conclusion: "failure",
      created_at: "2026-05-12T10:00:00Z"
    },
    {
      id: 2,
      event: "pull_request",
      head_sha: "abc",
      status: "completed",
      conclusion: "failure",
      created_at: "2026-05-12T10:05:00Z"
    }
  ];

  assert.deepEqual(selectAiReviewRun(runs, "abc"), { action: "rerun", run: runs[1] });

  const queued = {
    id: 4,
    event: "pull_request",
    head_sha: "abc",
    status: "queued",
    conclusion: null,
    created_at: "2026-05-12T10:15:00Z"
  };

  assert.deepEqual(selectAiReviewRun([...runs, queued], "abc"), {
    action: "already_running",
    run: queued
  });
});

test("AI Review rerun helper calls the workflow rerun endpoint for current-head failure", async () => {
  const calls = [];
  const request = async (_token, _repository, path, options = {}) => {
    calls.push({ path, method: options.method || "GET" });
    if (path.includes("/actions/workflows/ai-review.yml/runs")) {
      return {
        workflow_runs: [
          {
            id: 42,
            event: "pull_request",
            head_sha: "abc",
            status: "completed",
            conclusion: "failure",
            created_at: "2026-05-12T10:00:00Z"
          }
        ]
      };
    }
    return null;
  };

  const result = await rerunAiReviewForPrHead({
    token: "token",
    repository: "owner/repo",
    headSha: "abc",
    request
  });

  assert.equal(result.action, "rerun");
  assert.match(result.message, /Requested AI Review rerun/);
  assert.deepEqual(calls, [
    {
      path: "/repos/owner/repo/actions/workflows/ai-review.yml/runs?event=pull_request&head_sha=abc&per_page=100&page=1",
      method: "GET"
    },
    {
      path: "/repos/owner/repo/actions/runs/42/rerun",
      method: "POST"
    }
  ]);
});

test("AI Review rerun helper reruns a successful run that predates evidence", async () => {
  const calls = [];
  const request = async (_token, _repository, path, options = {}) => {
    calls.push({ path, method: options.method || "GET" });
    if (path.includes("/actions/workflows/ai-review.yml/runs")) {
      return {
        workflow_runs: [
          {
            id: 77,
            event: "pull_request",
            head_sha: "abc",
            status: "completed",
            conclusion: "success",
            created_at: "2026-05-12T10:00:00Z",
            updated_at: "2026-05-12T10:01:00Z"
          }
        ]
      };
    }
    return null;
  };

  const result = await rerunAiReviewForPrHead({
    token: "token",
    repository: "owner/repo",
    headSha: "abc",
    evidenceCreatedAt: "2026-05-12T10:05:00Z",
    request
  });

  assert.equal(result.action, "rerun");
  assert.deepEqual(calls, [
    {
      path: "/repos/owner/repo/actions/workflows/ai-review.yml/runs?event=pull_request&head_sha=abc&per_page=100&page=1",
      method: "GET"
    },
    {
      path: "/repos/owner/repo/actions/runs/77/rerun",
      method: "POST"
    }
  ]);
});
