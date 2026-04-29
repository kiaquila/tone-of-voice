from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tone_of_voice.config import repo_root
from tone_of_voice.drafting import DraftRequest, build_prompt_bundle
from tone_of_voice.feedback import compute_revision_metrics


SCHEMA_VERSION = 1
DEFAULT_EVAL_SUITE = "evals/regression/step4-seed.json"
DEFAULT_REQUIRED_CONTEXT_FILES = (
    "docs/00-principles.md",
    "docs/01-current-voice-snapshot.md",
    "docs/04-platform-adaptation.md",
    "docs/12-stop-list.md",
    "docs/13-drafting-recipes.md",
)


@dataclass(frozen=True)
class EvalThresholds:
    max_char_percent_changed: float
    max_word_percent_changed: float
    max_rule_failures: int = 0
    min_prompt_references: int = 3


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    platform: str
    draft_text: str
    final_text: str
    thresholds: EvalThresholds
    post_type: str | None = None
    source: str | None = None
    request: dict[str, Any] | None = None
    draft_must_not_contain: tuple[str, ...] = ()
    final_must_not_contain: tuple[str, ...] = ()
    final_must_contain: tuple[str, ...] = ()
    required_context_files: tuple[str, ...] = DEFAULT_REQUIRED_CONTEXT_FILES


def load_eval_suite(path: str | Path = DEFAULT_EVAL_SUITE) -> dict[str, Any]:
    suite_path = Path(path).expanduser()
    if not suite_path.is_absolute():
        suite_path = repo_root() / suite_path
    return json.loads(suite_path.read_text(encoding="utf-8"))


def parse_eval_cases(suite: dict[str, Any]) -> list[EvalCase]:
    schema_version = suite.get("schema_version")
    if schema_version != SCHEMA_VERSION:
        raise ValueError(f"unsupported eval suite schema_version: {schema_version}")

    defaults = suite.get("defaults") or {}
    cases = suite.get("cases") or []
    if not cases:
        raise ValueError("eval suite must include at least one case")

    parsed = []
    for item in cases:
        thresholds = {**defaults, **(item.get("thresholds") or {})}
        parsed.append(
            EvalCase(
                case_id=_required_text(item, "id"),
                platform=_required_text(item, "platform"),
                draft_text=_required_text(item, "draft_text"),
                final_text=_required_text(item, "final_text"),
                thresholds=EvalThresholds(
                    max_char_percent_changed=float(
                        thresholds.get("max_char_percent_changed", 100.0)
                    ),
                    max_word_percent_changed=float(
                        thresholds.get("max_word_percent_changed", 100.0)
                    ),
                    max_rule_failures=int(thresholds.get("max_rule_failures", 0)),
                    min_prompt_references=int(thresholds.get("min_prompt_references", 3)),
                ),
                post_type=_optional_text(item.get("post_type")),
                source=_optional_text(item.get("source")),
                request=item.get("request") if isinstance(item.get("request"), dict) else None,
                draft_must_not_contain=tuple(
                    _string_list(item.get("draft_must_not_contain"))
                ),
                final_must_not_contain=tuple(
                    _string_list(item.get("final_must_not_contain"))
                ),
                final_must_contain=tuple(_string_list(item.get("final_must_contain"))),
                required_context_files=tuple(
                    _string_list(
                        item.get("required_context_files"),
                        default=DEFAULT_REQUIRED_CONTEXT_FILES,
                    )
                ),
            )
        )
    return parsed


def evaluate_suite(
    suite: dict[str, Any],
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    base = root or repo_root()
    cases = parse_eval_cases(suite)
    minimum_cases = int(suite.get("minimum_cases", 1))
    if len(cases) < minimum_cases:
        raise ValueError(
            f"eval suite has {len(cases)} cases but requires at least {minimum_cases}"
        )

    case_results = [evaluate_case(case, root=base) for case in cases]
    failed_cases = [result for result in case_results if not result["passed"]]

    return {
        "schema_version": SCHEMA_VERSION,
        "suite": suite.get("name") or "unnamed",
        "total_cases": len(case_results),
        "failed_cases": len(failed_cases),
        "passed": not failed_cases,
        "cases": case_results,
    }


def evaluate_case(case: EvalCase, *, root: Path | None = None) -> dict[str, Any]:
    metrics = compute_revision_metrics(case.draft_text, case.final_text)
    failures = metric_failures(case, metrics)
    failures.extend(rule_failures(case))

    prompt_result = None
    if case.request:
        prompt_result = evaluate_prompt_contract(case, root=root)
        failures.extend(prompt_result["failures"])

    return {
        "id": case.case_id,
        "platform": case.platform,
        "post_type": case.post_type,
        "source": case.source,
        "passed": not failures,
        "failures": failures,
        "metrics": {
            "char_percent_changed": metrics["char_percent_changed"],
            "word_percent_changed": metrics["word_percent_changed"],
            "char_edit_distance": metrics["char_edit_distance"],
            "word_edit_distance": metrics["word_edit_distance"],
        },
        "prompt": prompt_result,
    }


def metric_failures(case: EvalCase, metrics: dict[str, Any]) -> list[str]:
    failures = []
    if metrics["char_percent_changed"] > case.thresholds.max_char_percent_changed:
        failures.append(
            "char_percent_changed "
            f"{metrics['char_percent_changed']} exceeds "
            f"{case.thresholds.max_char_percent_changed}"
        )
    if metrics["word_percent_changed"] > case.thresholds.max_word_percent_changed:
        failures.append(
            "word_percent_changed "
            f"{metrics['word_percent_changed']} exceeds "
            f"{case.thresholds.max_word_percent_changed}"
        )
    return failures


def rule_failures(case: EvalCase) -> list[str]:
    failures = []
    for phrase in case.draft_must_not_contain:
        if _contains_phrase(case.draft_text, phrase):
            failures.append(f"draft contains banned phrase: {phrase}")
    for phrase in case.final_must_not_contain:
        if _contains_phrase(case.final_text, phrase):
            failures.append(f"final contains banned phrase: {phrase}")
    for phrase in case.final_must_contain:
        if not _contains_phrase(case.final_text, phrase):
            failures.append(f"final is missing required phrase: {phrase}")

    if len(failures) > case.thresholds.max_rule_failures:
        return failures
    return []


def evaluate_prompt_contract(
    case: EvalCase,
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    base = root or repo_root()
    request = DraftRequest.from_mapping(case.request or {})
    bundle = build_prompt_bundle(request, root=base, model="eval-contract")
    failures = []

    if len(bundle.references) < case.thresholds.min_prompt_references:
        failures.append(
            "prompt selected "
            f"{len(bundle.references)} references, expected at least "
            f"{case.thresholds.min_prompt_references}"
        )

    missing_context = [
        rel_path
        for rel_path in case.required_context_files
        if rel_path not in bundle.context_files or rel_path not in bundle.prompt
    ]
    for rel_path in missing_context:
        failures.append(f"prompt missing required context file: {rel_path}")

    return {
        "reference_ids": [reference.ref_id for reference in bundle.references],
        "context_files": list(bundle.context_files),
        "failures": failures,
    }


def format_eval_report(result: dict[str, Any]) -> str:
    lines = [
        f"# Regression Eval Report - {result['suite']}",
        "",
        f"- Total cases: {result['total_cases']}",
        f"- Failed cases: {result['failed_cases']}",
        f"- Status: {'pass' if result['passed'] else 'fail'}",
        "",
        "## Cases",
        "",
    ]

    for case in result["cases"]:
        status = "pass" if case["passed"] else "fail"
        metrics = case["metrics"]
        lines.append(
            "- "
            f"`{case['id']}` ({status}): "
            f"{metrics['char_percent_changed']}% chars changed, "
            f"{metrics['word_percent_changed']}% words changed"
        )
        for failure in case["failures"]:
            lines.append(f"  - {failure}")

    lines.append("")
    return "\n".join(lines)


def _required_text(data: dict[str, Any], key: str) -> str:
    value = _optional_text(data.get(key))
    if not value:
        raise ValueError(f"{key} is required")
    return value


def _optional_text(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _string_list(
    value: Any,
    *,
    default: tuple[str, ...] = (),
) -> list[str]:
    if value is None:
        return list(default)
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple)):
        values = list(value)
    else:
        values = [value]
    return [str(item).strip() for item in values if str(item).strip()]


def _contains_phrase(text: str, phrase: str) -> bool:
    return phrase.casefold() in text.casefold()
