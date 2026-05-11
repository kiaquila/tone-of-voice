from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any, Sequence

from tone_of_voice.config import repo_root
from tone_of_voice.drafting import (
    ALLOWED_RETRIEVAL_STRATEGIES,
    DraftRequest,
    build_prompt_bundle,
)
from tone_of_voice.feedback import compute_revision_metrics
from tone_of_voice.style_memory import normalize_token


SCHEMA_VERSION = 1
DEFAULT_GENERATED_OUTPUT_SUITE = "evals/generated-output/step6-followup-seed.json"
DEFAULT_VARIANTS = ("heuristic", "style_memory", "hybrid", "llama_index")


@dataclass(frozen=True)
class GeneratedOutputThresholds:
    max_char_percent_changed: float = 100.0
    max_word_percent_changed: float = 100.0
    min_prompt_references: int = 3


@dataclass(frozen=True)
class GeneratedOutputVariant:
    strategy: str
    draft_text: str
    artifact_path: str | None = None
    preference: str | None = None
    tone_corrections: tuple[str, ...] = ()
    structural_notes: tuple[str, ...] = ()
    notes: str | None = None


@dataclass(frozen=True)
class GeneratedOutputCase:
    case_id: str
    request: DraftRequest
    final_text: str
    variants: tuple[GeneratedOutputVariant, ...]
    selected_variant: str | None = None
    thresholds: GeneratedOutputThresholds = GeneratedOutputThresholds()
    tone_corrections: tuple[str, ...] = ()
    structural_notes: tuple[str, ...] = ()
    notes: str | None = None


def load_generated_output_suite(
    path: str | Path = DEFAULT_GENERATED_OUTPUT_SUITE,
) -> dict[str, Any]:
    suite_path = Path(path).expanduser()
    if not suite_path.is_absolute():
        suite_path = repo_root() / suite_path
    return json.loads(suite_path.read_text(encoding="utf-8"))


def parse_generated_output_cases(
    suite: dict[str, Any],
) -> list[GeneratedOutputCase]:
    schema_version = suite.get("schema_version")
    if schema_version != SCHEMA_VERSION:
        raise ValueError(
            f"unsupported generated-output suite schema_version: {schema_version}"
        )

    defaults = suite.get("defaults") or {}
    cases = suite.get("cases") or []
    if not cases:
        raise ValueError("generated-output suite must include at least one case")

    parsed: list[GeneratedOutputCase] = []
    for item in cases:
        thresholds = {**defaults, **(item.get("thresholds") or {})}
        variants = parse_generated_output_variants(item.get("variants"))
        selected_variant = _optional_strategy(item.get("selected_variant"))
        variant_names = {variant.strategy for variant in variants}
        if selected_variant and selected_variant not in variant_names:
            raise ValueError(
                f"generated-output case {item.get('id')!r} selects missing "
                f"variant {selected_variant!r}"
            )
        parsed.append(
            GeneratedOutputCase(
                case_id=_required_text(item, "id"),
                request=DraftRequest.from_mapping(_required_mapping(item, "request")),
                final_text=_required_text(item, "final_text"),
                variants=variants,
                selected_variant=selected_variant,
                thresholds=GeneratedOutputThresholds(
                    max_char_percent_changed=float(
                        thresholds.get("max_char_percent_changed", 100.0)
                    ),
                    max_word_percent_changed=float(
                        thresholds.get("max_word_percent_changed", 100.0)
                    ),
                    min_prompt_references=int(
                        thresholds.get("min_prompt_references", 3)
                    ),
                ),
                tone_corrections=tuple(
                    _token_list(item.get("tone_corrections"))
                ),
                structural_notes=tuple(_string_list(item.get("structural_notes"))),
                notes=_optional_text(item.get("notes")),
            )
        )
    return parsed


def parse_generated_output_variants(value: Any) -> tuple[GeneratedOutputVariant, ...]:
    items = _variant_items(value)
    if len(items) < 2:
        raise ValueError("generated-output cases must include at least two variants")

    variants: list[GeneratedOutputVariant] = []
    seen: set[str] = set()
    for item in items:
        strategy = _required_strategy(item, "strategy")
        if strategy in seen:
            raise ValueError(f"duplicate generated-output variant: {strategy}")
        seen.add(strategy)
        variants.append(
            GeneratedOutputVariant(
                strategy=strategy,
                draft_text=_required_text(item, "draft_text"),
                artifact_path=_optional_text(item.get("artifact_path")),
                preference=_optional_token(item.get("preference")),
                tone_corrections=tuple(_token_list(item.get("tone_corrections"))),
                structural_notes=tuple(_string_list(item.get("structural_notes"))),
                notes=_optional_text(item.get("notes")),
            )
        )
    return tuple(variants)


def evaluate_generated_output_suite(
    suite: dict[str, Any],
    *,
    root: Path | None = None,
    variants: Sequence[str] = DEFAULT_VARIANTS,
) -> dict[str, Any]:
    base = root or repo_root()
    requested_variants = tuple(_normalize_strategy(value) for value in variants)
    cases = parse_generated_output_cases(suite)
    case_results = [
        evaluate_generated_output_case(
            case,
            root=base,
            variants=requested_variants,
        )
        for case in cases
    ]
    aggregate = aggregate_generated_output_metrics(case_results, requested_variants)
    failed_cases = [case for case in case_results if not case["passed"]]

    return {
        "schema_version": SCHEMA_VERSION,
        "suite": suite.get("name") or "unnamed",
        "variants": list(requested_variants),
        "total_cases": len(case_results),
        "failed_cases": len(failed_cases),
        "passed": not failed_cases,
        "winner": choose_generated_output_winner(aggregate),
        "aggregate": aggregate,
        "common_tone_corrections": common_tone_corrections(case_results),
        "cases": case_results,
    }


def evaluate_generated_output_case(
    case: GeneratedOutputCase,
    *,
    root: Path | None = None,
    variants: Sequence[str] = DEFAULT_VARIANTS,
) -> dict[str, Any]:
    base = root or repo_root()
    variant_by_strategy = {variant.strategy: variant for variant in case.variants}
    requested = tuple(_normalize_strategy(value) for value in variants)

    variant_results: dict[str, Any] = {}
    case_failures: list[str] = []
    for strategy in requested:
        variant = variant_by_strategy.get(strategy)
        if variant is None:
            continue
        result = evaluate_generated_output_variant(
            case,
            variant,
            root=base,
        )
        variant_results[strategy] = result

    if not variant_results:
        case_failures.append("case has no generated outputs for requested variants")

    best_by_edit = best_variant_by_edit_distance(variant_results)
    selected_metrics = (
        variant_results.get(case.selected_variant, {}).get("metrics")
        if case.selected_variant
        else None
    )
    variant_failures = [
        strategy
        for strategy, result in variant_results.items()
        if not result.get("passed", False)
    ]
    if variant_failures:
        case_failures.append(
            "failing variants: " + ", ".join(sorted(variant_failures))
        )

    return {
        "id": case.case_id,
        "request": case.request.to_dict(),
        "selected_variant": case.selected_variant,
        "best_by_edit_distance": best_by_edit,
        "selected_variant_metrics": selected_metrics,
        "tone_corrections": list(case.tone_corrections),
        "structural_notes": list(case.structural_notes),
        "notes": case.notes,
        "passed": not case_failures,
        "failures": case_failures,
        "variants": variant_results,
    }


def evaluate_generated_output_variant(
    case: GeneratedOutputCase,
    variant: GeneratedOutputVariant,
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    base = root or repo_root()
    metrics = compute_revision_metrics(variant.draft_text, case.final_text)
    failures = metric_failures(case, metrics)

    request = DraftRequest.from_mapping(
        {**case.request.to_dict(), "retrieval_strategy": variant.strategy}
    )
    bundle = build_prompt_bundle(request, root=base, model="eval-contract")
    if len(bundle.references) < case.thresholds.min_prompt_references:
        failures.append(
            "prompt selected "
            f"{len(bundle.references)} references, expected at least "
            f"{case.thresholds.min_prompt_references}"
        )

    return {
        "strategy": variant.strategy,
        "artifact_path": variant.artifact_path,
        "preference": variant.preference,
        "tone_corrections": list(variant.tone_corrections),
        "structural_notes": list(variant.structural_notes),
        "notes": variant.notes,
        "metrics": {
            "char_percent_changed": metrics["char_percent_changed"],
            "word_percent_changed": metrics["word_percent_changed"],
            "char_edit_distance": metrics["char_edit_distance"],
            "word_edit_distance": metrics["word_edit_distance"],
            "line_delta": metrics["line_delta"],
            "emoji_delta": metrics["emoji_delta"],
        },
        "prompt": {
            "retrieval_strategy": bundle.retrieval_strategy,
            "reference_ids": [reference.ref_id for reference in bundle.references],
            "style_memory_record_ids": [
                match.record.record_id for match in bundle.style_memory_matches
            ],
            "context_files": list(bundle.context_files),
        },
        "passed": not failures,
        "failures": failures,
    }


def metric_failures(
    case: GeneratedOutputCase,
    metrics: dict[str, Any],
) -> list[str]:
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


def aggregate_generated_output_metrics(
    case_results: list[dict[str, Any]],
    variants: Sequence[str],
) -> dict[str, Any]:
    aggregate: dict[str, Any] = {}
    for strategy in variants:
        variant_cases = [
            case["variants"][strategy]
            for case in case_results
            if strategy in case["variants"]
        ]
        if not variant_cases:
            continue

        char_percentages = [
            item["metrics"]["char_percent_changed"] for item in variant_cases
        ]
        word_percentages = [
            item["metrics"]["word_percent_changed"] for item in variant_cases
        ]
        selected_count = sum(
            1
            for case in case_results
            if case.get("selected_variant") == strategy
            and strategy in case.get("variants", {})
        )
        best_by_edit_count = sum(
            1
            for case in case_results
            if case.get("best_by_edit_distance") == strategy
        )
        aggregate[strategy] = {
            "cases": len(variant_cases),
            "median_char_percent_changed": _median(char_percentages),
            "median_word_percent_changed": _median(word_percentages),
            "average_char_percent_changed": _mean(char_percentages),
            "average_word_percent_changed": _mean(word_percentages),
            "selected_count": selected_count,
            "best_by_edit_count": best_by_edit_count,
            "failed_cases": sum(1 for item in variant_cases if not item["passed"]),
            "passed": all(item["passed"] for item in variant_cases),
        }
    return aggregate


def best_variant_by_edit_distance(variant_results: dict[str, Any]) -> str | None:
    if not variant_results:
        return None
    ranked = sorted(
        variant_results.items(),
        key=lambda item: (
            item[1]["metrics"]["word_percent_changed"],
            item[1]["metrics"]["char_percent_changed"],
            item[0],
        ),
    )
    if len(ranked) > 1:
        top = (
            ranked[0][1]["metrics"]["word_percent_changed"],
            ranked[0][1]["metrics"]["char_percent_changed"],
        )
        second = (
            ranked[1][1]["metrics"]["word_percent_changed"],
            ranked[1][1]["metrics"]["char_percent_changed"],
        )
        if second == top:
            return None
    return ranked[0][0]


def choose_generated_output_winner(aggregate: dict[str, Any]) -> str | None:
    if not aggregate:
        return None
    ranked = sorted(
        aggregate.items(),
        key=lambda item: (*_winner_key(item[1]), item[0]),
    )
    if len(ranked) > 1:
        top_key = _winner_key(ranked[0][1])
        second_key = _winner_key(ranked[1][1])
        if second_key == top_key:
            return None
    return ranked[0][0]


def common_tone_corrections(
    case_results: list[dict[str, Any]],
) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    for case in case_results:
        counter.update(case.get("tone_corrections") or [])
        for variant in case.get("variants", {}).values():
            counter.update(variant.get("tone_corrections") or [])
    return counter.most_common()


def format_generated_output_report(result: dict[str, Any]) -> str:
    winner = result.get("winner") or "(no clear winner)"
    lines = [
        f"# Generated Output A/B Report - {result['suite']}",
        "",
        f"- Total cases: {result['total_cases']}",
        f"- Variants requested: {', '.join(result['variants'])}",
        f"- Winner: {winner}",
        f"- Failed cases: {result['failed_cases']}",
        f"- Status: {'pass' if result['passed'] else 'fail'}",
        "",
        "## Aggregate",
        "",
    ]

    for strategy, metrics in result["aggregate"].items():
        status = "pass" if metrics["passed"] else "fail"
        lines.append(
            "- "
            f"`{strategy}` ({status}): "
            f"median_word_change={metrics['median_word_percent_changed']}%, "
            f"median_char_change={metrics['median_char_percent_changed']}%, "
            f"selected={metrics['selected_count']}, "
            f"best_by_edit={metrics['best_by_edit_count']}, "
            f"failed_cases={metrics['failed_cases']}"
        )

    lines.extend(["", "## Common Corrections", ""])
    if result["common_tone_corrections"]:
        lines.extend(
            f"- `{tag}` - {count}"
            for tag, count in result["common_tone_corrections"]
        )
    else:
        lines.append("- None recorded.")

    lines.extend(["", "## Cases", ""])
    for case in result["cases"]:
        status = "pass" if case["passed"] else "fail"
        lines.append(f"### {case['id']} ({status})")
        lines.append("")
        lines.append(f"- Selected variant: {case['selected_variant'] or 'none'}")
        lines.append(
            f"- Best by edit distance: {case['best_by_edit_distance'] or 'tie'}"
        )
        for strategy, variant in case["variants"].items():
            metrics = variant["metrics"]
            variant_status = "pass" if variant["passed"] else "fail"
            refs = ", ".join(variant["prompt"]["reference_ids"])
            lines.append(
                "- "
                f"`{strategy}` ({variant_status}): "
                f"{metrics['word_percent_changed']}% words changed, "
                f"{metrics['char_percent_changed']}% chars changed; "
                f"refs: {refs}"
            )
            for failure in variant["failures"]:
                lines.append(f"  - {failure}")
        for failure in case["failures"]:
            lines.append(f"- {failure}")
        lines.append("")
    return "\n".join(lines)


def _winner_key(metrics: dict[str, Any]) -> tuple[Any, ...]:
    # Objective edit-metrics drive ranking; the human `selected_count` acts only
    # as a tie-breaker so the winner cannot just re-broadcast manual labels.
    return (
        not metrics["passed"],
        -metrics["best_by_edit_count"],
        metrics["median_word_percent_changed"],
        metrics["median_char_percent_changed"],
        -metrics["selected_count"],
    )


def _variant_items(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        items: list[dict[str, Any]] = []
        for strategy, data in value.items():
            if not isinstance(data, dict):
                raise ValueError(f"variant {strategy!r} must be an object")
            items.append({"strategy": strategy, **data})
        return items
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _required_mapping(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} is required")
    return value


def _required_text(data: dict[str, Any], key: str) -> str:
    value = _optional_text(data.get(key))
    if not value:
        raise ValueError(f"{key} is required")
    return value


def _optional_text(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _optional_token(value: Any) -> str | None:
    text = _optional_text(value)
    return normalize_token(text) if text else None


def _required_strategy(data: dict[str, Any], key: str) -> str:
    value = _required_text(data, key)
    return _normalize_strategy(value)


def _optional_strategy(value: Any) -> str | None:
    text = _optional_text(value)
    return _normalize_strategy(text) if text else None


def _normalize_strategy(value: str) -> str:
    strategy = normalize_token(value)
    if strategy not in ALLOWED_RETRIEVAL_STRATEGIES:
        allowed = ", ".join(sorted(ALLOWED_RETRIEVAL_STRATEGIES))
        raise ValueError(f"retrieval strategy must be one of: {allowed}")
    return strategy


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple)):
        values = list(value)
    else:
        values = [value]
    return [str(item).strip() for item in values if str(item).strip()]


def _token_list(value: Any) -> list[str]:
    return [normalize_token(item) for item in _string_list(value)]


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 1)


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(float(median(values)), 1)
