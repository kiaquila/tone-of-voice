const reviewerBotLogins = new Set([
  "chatgpt-codex-connector[bot]",
  "gemini-code-assist[bot]",
  "claude[bot]",
]);

export const codexReviewerLogins = new Set(["chatgpt-codex-connector[bot]"]);

// Only trigger comments from trusted authors are honored as authoritative
// review boundaries. Without this check, an untrusted commenter on a
// public PR can post `@codex review`, Codex Cloud responds with a
// "create an environment" / "connect Codex account" setup error, and
// `pickAuthoritativeCodexSkipModeComment` would treat that error as
// the latest gate verdict — failing the required AI Review check
// even when a valid Codex review already exists for the head SHA.
// `ai-command-policy.yml` enforces the same restriction at the
// command-routing layer, but the gate's own timeline analysis runs
// independently and must enforce it too.
const trustedTriggerAssociations = new Set([
  "OWNER",
  "MEMBER",
  "COLLABORATOR",
]);

export const trustedAssociations = trustedTriggerAssociations;

export function isTrustedAssociation(value) {
  return trustedAssociations.has(String(value || "").toUpperCase());
}

const codexSummaryPrefix = /^Codex Review:/i;
const codexNoIssuesPattern =
  /did(?:\s+not|\s*n['’]?t)\s+find\s+any\s+major\s+issues/i;
const codexEnvironmentPattern = /create an environment for this repo/i;
const codexAccountPattern = /create a codex account and connect to github/i;
const codexTriggerPattern = /@codex review\b/i;

const getBody = (entry) => (entry?.body || "").trim();
const getLogin = (entry) => entry?.user?.login || "";

const isCommentEvent = (entry) => !entry?.event || entry.event === "commented";

const isCodexBotComment = (entry) =>
  isCommentEvent(entry) && codexReviewerLogins.has(getLogin(entry));

const isHumanCodexTriggerComment = (entry) =>
  isCommentEvent(entry) &&
  codexTriggerPattern.test(getBody(entry)) &&
  !reviewerBotLogins.has(getLogin(entry)) &&
  trustedTriggerAssociations.has(entry?.author_association || "");

// Comments that LOOK like Codex triggers but come from an untrusted
// human (author_association NOT in trustedTriggerAssociations). The
// gate must NOT advance its boundary on these (handled in
// isHumanCodexTriggerComment), AND must NOT pick the Codex bot's
// reply to them as the latest verdict — Codex Cloud will respond with
// a "create environment" / "connect account" setup error to any
// trigger from an unconnected account, and treating that error as
// authoritative would let an outsider DoS the required check.
const isUntrustedCodexTriggerComment = (entry) =>
  isCommentEvent(entry) &&
  codexTriggerPattern.test(getBody(entry)) &&
  !reviewerBotLogins.has(getLogin(entry)) &&
  !trustedTriggerAssociations.has(entry?.author_association || "");

const isCurrentHeadActivationEvent = (entry, headSha) =>
  (entry?.event === "committed" && entry?.sha === headSha) ||
  ((entry?.event === "head_ref_force_pushed" ||
    entry?.event === "head_ref_restored") &&
    entry?.commit_id === headSha);

// Review states the gate knows how to classify. Anything outside this
// set (notably `DISMISSED` and `PENDING`) must NOT be matched here,
// otherwise `pickLatestCodexReview` would keep returning that
// unclassifiable review on every poll iteration, the classifier would
// answer "pending", and the loop would stall until the 20-minute
// timeout — turning a recoverable state into a guaranteed false-fail
// (an earlier qualifying review on the same SHA would never be
// considered).
export const supportedReviewStates = new Set([
  "APPROVED",
  "CHANGES_REQUESTED",
  "COMMENTED",
]);

// Match Codex reviews on identity + head SHA + a classifiable state.
// Avoid relying on the review body containing the literal
// "Codex Review" — connector templates change over time and a valid
// review with an empty body would otherwise time out the gate.
// State must be in `supportedReviewStates` so the polling loop falls
// through to earlier reviews when the latest one is e.g. DISMISSED.
export const matchesCodexReview = (review, headSha) =>
  review?.commit_id === headSha &&
  codexReviewerLogins.has(review?.user?.login || "") &&
  supportedReviewStates.has(review?.state || "");

export const matchesCodexSummaryComment = (comment) =>
  isCodexBotComment(comment) && codexSummaryPrefix.test(getBody(comment));

export const classifyCodexSetupReply = (comment) => {
  const body = getBody(comment);

  if (codexEnvironmentPattern.test(body)) {
    return {
      outcome: "fail",
      reason:
        "Codex could not start the selected review because no Codex cloud environment is configured for this repository.",
      details: [comment.html_url],
    };
  }

  if (codexAccountPattern.test(body)) {
    return {
      outcome: "fail",
      reason:
        "Codex could not start the selected review because the trigger did not come from a connected human Codex account.",
      details: [comment.html_url],
    };
  }

  return null;
};

export const classifyCodexSummaryComment = (comment) => {
  const body = getBody(comment);

  if (codexNoIssuesPattern.test(body)) {
    return {
      outcome: "pass",
      reason: "Codex completed review with no major issues.",
      details: [comment.html_url],
    };
  }

  return {
    outcome: "pending",
    reason:
      "Codex summary comment did not match a recognized no-findings reply.",
    details: [comment.html_url],
  };
};

export const findLatestHeadActivationIndex = (timelineEvents, headSha) => {
  if (!Array.isArray(timelineEvents) || !headSha) {
    return -1;
  }

  for (let index = timelineEvents.length - 1; index >= 0; index -= 1) {
    if (isCurrentHeadActivationEvent(timelineEvents[index], headSha)) {
      return index;
    }
  }

  return -1;
};

export const pickAuthoritativeCodexSkipModeComment = ({
  timelineEvents,
  headSha,
}) => {
  if (
    !Array.isArray(timelineEvents) ||
    timelineEvents.length === 0 ||
    !headSha
  ) {
    return null;
  }

  const activationIndex = findLatestHeadActivationIndex(
    timelineEvents,
    headSha,
  );
  if (activationIndex < 0) {
    return null;
  }

  let boundaryIndex = activationIndex;
  for (
    let index = activationIndex + 1;
    index < timelineEvents.length;
    index += 1
  ) {
    if (isHumanCodexTriggerComment(timelineEvents[index])) {
      boundaryIndex = index;
    }
  }

  // Walk forward from boundaryIndex+1 to pick the latest AUTHORITATIVE
  // Codex bot comment. A bot comment is authoritative only if no
  // untrusted `@codex review` trigger appears between the latest
  // trusted boundary and that bot comment — otherwise the bot comment
  // is the bot's reply to the untrusted trigger (typically a
  // "connect account" / "create environment" setup error) and must
  // NOT be treated as the gate verdict. Once the zone is tainted by
  // an untrusted trigger, all subsequent bot replies are ignored
  // until a new trusted trigger advances the boundary (which would
  // restart this walk on a future invocation).
  let latestCodexComment = null;
  let zoneTaintedByUntrustedTrigger = false;
  for (
    let index = boundaryIndex + 1;
    index < timelineEvents.length;
    index += 1
  ) {
    const entry = timelineEvents[index];
    if (isUntrustedCodexTriggerComment(entry)) {
      zoneTaintedByUntrustedTrigger = true;
      continue;
    }
    if (isCodexBotComment(entry) && !zoneTaintedByUntrustedTrigger) {
      latestCodexComment = entry;
    }
  }

  if (!latestCodexComment) {
    return null;
  }

  const setupClassification = classifyCodexSetupReply(latestCodexComment);
  if (setupClassification) {
    return {
      comment: latestCodexComment,
      classification: setupClassification,
      reviewState: "SETUP_REQUIRED",
      boundaryType:
        boundaryIndex === activationIndex ? "head-activation" : "human-trigger",
    };
  }

  if (!matchesCodexSummaryComment(latestCodexComment)) {
    return null;
  }

  const summaryClassification = classifyCodexSummaryComment(latestCodexComment);
  if (summaryClassification.outcome === "pending") {
    return null;
  }

  return {
    comment: latestCodexComment,
    classification: summaryClassification,
    reviewState: "COMMENTED_NO_FINDINGS",
    boundaryType:
      boundaryIndex === activationIndex ? "head-activation" : "human-trigger",
  };
};

export function extractClaudeOutcome(body) {
  const match = String(body || "").match(/^AI_REVIEW_OUTCOME:\s*(pass|advisory|block)\s*$/im);
  return match?.[1]?.toLowerCase() || null;
}

export function extractMarkerSha(body) {
  const match = String(body || "").match(/^AI_REVIEW_SHA:\s*([a-f0-9]{7,40})\s*$/im);
  return match?.[1] || null;
}

export function createAiReviewRequestMarkerBody({
  agent,
  headSha,
  requestId,
  sourceCommentId,
  sourceCommentCreatedAt,
  requestedAt
}) {
  const recordedAt = requestedAt || new Date().toISOString();
  return [
    `AI review request recorded for \`${String(headSha || "").slice(0, 10)}\`.`,
    "",
    "<!-- unicorn-hub:ai-review-request",
    `AI_REVIEW_REQUEST_ID: ${requestId}`,
    `AI_REVIEW_AGENT: ${String(agent || "").trim().toLowerCase()}`,
    `AI_REVIEW_SHA: ${headSha}`,
    `AI_REVIEW_SOURCE_COMMENT_ID: ${sourceCommentId}`,
    `AI_REVIEW_SOURCE_COMMENT_CREATED_AT: ${sourceCommentCreatedAt || recordedAt}`,
    `AI_REVIEW_REQUESTED_AT: ${recordedAt}`,
    "-->"
  ].join("\n");
}

export function extractAiReviewRequestMarker(body) {
  const text = String(body || "");
  if (!text.includes("unicorn-hub:ai-review-request")) return null;

  const field = (name) => text.match(new RegExp(`^${name}:\\s*(.+?)\\s*$`, "im"))?.[1]?.trim() || null;
  const requestId = field("AI_REVIEW_REQUEST_ID");
  const agent = field("AI_REVIEW_AGENT")?.toLowerCase();
  const sha = field("AI_REVIEW_SHA");
  const sourceCommentId = field("AI_REVIEW_SOURCE_COMMENT_ID");
  const sourceCommentCreatedAt = field("AI_REVIEW_SOURCE_COMMENT_CREATED_AT");
  const requestedAt = field("AI_REVIEW_REQUESTED_AT");

  if (!requestId || !agent || !sha || !sourceCommentId || !requestedAt) return null;
  if (!/^[a-f0-9]{7,40}$/i.test(sha)) return null;

  return {
    requestId,
    agent,
    sha,
    sourceCommentId,
    sourceCommentCreatedAt,
    requestedAt
  };
}

export function normalizeLogin(login) {
  return String(login || "").toLowerCase();
}

const defaultTrustedReviewLogins = {
  codex: ["chatgpt-codex-connector[bot]"],
  claude: ["claude[bot]"],
  gemini: ["gemini-code-assist[bot]"]
};

export function trustedReviewLoginsForAgent(agent, config = {}) {
  return new Set([
    ...(defaultTrustedReviewLogins[agent] || []),
    ...(config.trustedReviewLogins || []),
    ...(config.trustedReviewLoginsByAgent?.[agent] || [])
  ].map(normalizeLogin));
}

export function isTrustedReviewLogin(login, agent, config = {}) {
  return trustedReviewLoginsForAgent(agent, config).has(normalizeLogin(login));
}

export function isAiReviewRequestMarkerComment(comment, agent, headSha) {
  const login = normalizeLogin(comment?.user?.login);
  if (login !== "github-actions[bot]") return false;
  const marker = extractAiReviewRequestMarker(comment?.body);
  if (!marker) return false;
  return marker.agent === String(agent || "").toLowerCase() && marker.sha === headSha;
}

export function latestAiReviewRequestMarker(comments = [], agent, headSha) {
  return comments
    .map((comment) => {
      const marker = extractAiReviewRequestMarker(comment?.body);
      if (!marker) return null;
      return {
        ...marker,
        commentId: String(comment.id || ""),
        commentCreatedAt: comment.created_at || null,
        author: comment.user?.login || null
      };
    })
    .filter((marker) =>
      marker &&
      normalizeLogin(marker.author) === "github-actions[bot]" &&
      marker.agent === String(agent || "").toLowerCase() &&
      marker.sha === headSha
    )
    .sort((left, right) =>
      Date.parse(right.commentCreatedAt || right.requestedAt || "") -
      Date.parse(left.commentCreatedAt || left.requestedAt || "")
    )[0] || null;
}

export function containsBlockingSeverity(body, agent) {
  const text = String(body || "");
  if (agent === "codex") {
    return /\bP[0-2]\b/.test(text);
  }
  if (agent === "gemini") {
    return /\b(critical|high)\b/i.test(text);
  }
  return false;
}

export function extractCodexPriority(body) {
  const match = String(body || "").match(/\bP([0-3])\b/i);
  return match ? Number(match[1]) : null;
}

export function isAcceptableCodexSummaryComment(comment, headSha, requestMarker = null, config = {}) {
  const body = String(comment?.body || "").trim();
  const login = normalizeLogin(comment?.user?.login);
  if (!isTrustedReviewLogin(login, "codex", config)) return false;
  if (!/^Codex Review:/i.test(body)) return false;
  if (!/did(?:\s+not|\s*n['’]?t)\s+find\s+any\s+major\s+issues/i.test(body)) return false;

  const shortSha = String(headSha || "").slice(0, 10);
  if (shortSha && (body.includes(headSha) || body.includes(shortSha))) return true;

  if (!requestMarker || requestMarker.agent !== "codex" || requestMarker.sha !== headSha) return false;
  const requestedAt = Date.parse(
    requestMarker.sourceCommentCreatedAt ||
    requestMarker.requestedAt ||
    requestMarker.commentCreatedAt ||
    ""
  );
  const createdAt = Date.parse(comment?.created_at || "");
  return Number.isFinite(requestedAt) && Number.isFinite(createdAt) && createdAt >= requestedAt;
}

export function hasHeadUpdateBetweenTimestamps(timeline = [], startCreatedAt, endCreatedAt) {
  const startTime = Date.parse(startCreatedAt || "");
  const endTime = Date.parse(endCreatedAt || "");
  if (!Number.isFinite(startTime) || !Number.isFinite(endTime) || startTime > endTime) return true;
  return timeline.some((event) => {
    if (event.event !== "committed" && event.event !== "head_ref_force_pushed") return false;
    const eventTime = Date.parse(event.created_at || event.committer?.date || "");
    return Number.isFinite(eventTime) && eventTime > startTime && eventTime <= endTime;
  });
}

export function classifyCodexNativeReview(review, reviewComments = [], headSha, config = {}) {
  if (!review) return null;
  if (review.commit_id && headSha && review.commit_id !== headSha) return null;
  const login = normalizeLogin(review.user?.login);
  if (!isTrustedReviewLogin(login, "codex", config)) return null;
  if (containsBlockingSeverity(review.body, "codex")) return "fail";

  if (review.state === "APPROVED") return "pass";
  if (review.state === "CHANGES_REQUESTED") return "fail";
  if (review.state !== "COMMENTED") return null;

  const commentsForReview = reviewComments.filter((comment) =>
    comment.pull_request_review_id === review.id &&
    isTrustedReviewLogin(comment.user?.login, "codex", config)
  );
  if (commentsForReview.length === 0) return "pass";

  const priorities = commentsForReview.map((comment) => extractCodexPriority(comment.body));
  if (priorities.some((priority) => priority === null)) return "fail";
  return Math.min(...priorities) <= 2 ? "fail" : "pass";
}

export function latestCodexNativeReviewResult(reviews = [], reviewComments = [], headSha, config = {}) {
  return reviews
    .map((review) => ({
      review,
      result: classifyCodexNativeReview(review, reviewComments, headSha, config)
    }))
    .filter((entry) => entry.result !== null)
    .sort((left, right) =>
      Date.parse(right.review.submitted_at || "") - Date.parse(left.review.submitted_at || "")
    )[0]?.result || null;
}

export function isAcceptableNativeReview(review, agent, headSha, config = {}) {
  if (!review) return false;
  if (review.commit_id && headSha && review.commit_id !== headSha) return false;
  const login = normalizeLogin(review.user?.login);
  const body = review.body || "";

  if (agent === "codex") {
    return isTrustedReviewLogin(login, agent, config) &&
      review.state === "APPROVED" &&
      !containsBlockingSeverity(body, agent);
  }

  if (agent === "gemini") {
    return isTrustedReviewLogin(login, agent, config) && !containsBlockingSeverity(body, agent);
  }

  return false;
}

export function isAcceptableClaudeComment(comment, headSha, config = {}) {
  const body = comment?.body || "";
  const login = normalizeLogin(comment?.user?.login);
  if (!isTrustedReviewLogin(login, "claude", config)) return false;
  if (extractMarkerSha(body) !== headSha) return false;
  return extractClaudeOutcome(body) === "pass";
}
