from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from tone_of_voice.config import repo_root
from tone_of_voice.drafting import (
    DraftRequest,
    ReferenceEntry,
    ReferenceLibrary,
    load_reference_library,
    select_references,
)
from tone_of_voice.style_memory import (
    StyleMemoryIndex,
    build_style_memory_index,
    retrieve_style_memory,
    style_memory_query_from_request,
)


SCHEMA_VERSION = 1
DEFAULT_RETRIEVAL_SUITE = "evals/retrieval/style-memory-seed.json"
DEFAULT_VARIANTS = ("heuristic", "style_memory", "hybrid")


@dataclass(frozen=True)
class RetrievalThresholds:
    min_recall_at_k: float = 0.5
    min_mrr: float = 0.25


@dataclass(frozen=True)
class RetrievalExperimentCase:
    case_id: str
    request: DraftRequest
    expected_record_ids: tuple[str, ...]
    k: int = 5
    thresholds: RetrievalThresholds = RetrievalThresholds()
    notes: str | None = None


def load_retrieval_suite(path: str | Path = DEFAULT_RETRIEVAL_SUITE) -> dict[str, Any]:
    suite_path = Path(path).expanduser()
    if not suite_path.is_absolute():
        suite_path = repo_root() / suite_path
    return json.loads(suite_path.read_text(encoding="utf-8"))


def parse_retrieval_cases(suite: dict[str, Any]) -> list[RetrievalExperimentCase]:
    schema_version = suite.get("schema_version")
    if schema_version != SCHEMA_VERSION:
        raise ValueError(
            f"unsupported retrieval suite schema_version: {schema_version}"
        )
    cases = suite.get("cases") or []
    if not cases:
        raise ValueError("retrieval suite must include at least one case")

    defaults = suite.get("defaults") or {}
    parsed: list[RetrievalExperimentCase] = []
    for item in cases:
        thresholds = {**defaults, **(item.get("thresholds") or {})}
        expected = tuple(
            normalize_reference_record_id(value)
            for value in _string_list(item.get("expected_record_ids"))
        )
        if not expected:
            raise ValueError(f"retrieval case {item.get('id')!r} has no expected ids")
        parsed.append(
            RetrievalExperimentCase(
                case_id=_required_text(item, "id"),
                request=DraftRequest.from_mapping(_required_mapping(item, "request")),
                expected_record_ids=expected,
                k=int(item.get("k") or defaults.get("k") or 5),
                thresholds=RetrievalThresholds(
                    min_recall_at_k=float(thresholds.get("min_recall_at_k", 0.5)),
                    min_mrr=float(thresholds.get("min_mrr", 0.25)),
                ),
                notes=_optional_text(item.get("notes")),
            )
        )
    return parsed


def evaluate_retrieval_suite(
    suite: dict[str, Any],
    *,
    root: Path | None = None,
    variants: Sequence[str] = DEFAULT_VARIANTS,
) -> dict[str, Any]:
    base = root or repo_root()
    cases = parse_retrieval_cases(suite)
    library = load_reference_library(base)
    index = build_style_memory_index(
        root=base,
        reference_entries=library.entries,
        feedback_dirs=[],
    )

    case_results = [
        evaluate_retrieval_case(
            case,
            library_entries=library.entries,
            shortcuts=library.shortcuts,
            index=index,
            variants=variants,
        )
        for case in cases
    ]
    aggregate = aggregate_variant_metrics(case_results, variants)
    failed_variants = [
        name for name, item in aggregate.items() if not item.get("passed", False)
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "suite": suite.get("name") or "unnamed",
        "variants": list(variants),
        "total_cases": len(case_results),
        "failed_variants": failed_variants,
        "passed": not failed_variants,
        "winner": choose_winner(aggregate),
        "aggregate": aggregate,
        "cases": case_results,
    }


def evaluate_retrieval_case(
    case: RetrievalExperimentCase,
    *,
    library_entries: tuple[ReferenceEntry, ...],
    shortcuts: dict[str, tuple[str, ...]],
    index: StyleMemoryIndex,
    variants: Sequence[str] = DEFAULT_VARIANTS,
) -> dict[str, Any]:
    variant_results = {}
    for variant in variants:
        selected = select_variant_records(
            variant,
            case.request,
            library_entries=library_entries,
            shortcuts=shortcuts,
            index=index,
            k=case.k,
        )
        metrics = retrieval_metrics(selected, case.expected_record_ids, k=case.k)
        failures = []
        if metrics["recall_at_k"] < case.thresholds.min_recall_at_k:
            failures.append(
                "recall_at_k "
                f"{metrics['recall_at_k']} below {case.thresholds.min_recall_at_k}"
            )
        if metrics["mrr"] < case.thresholds.min_mrr:
            failures.append(
                f"mrr {metrics['mrr']} below {case.thresholds.min_mrr}"
            )
        variant_results[variant] = {
            "selected_record_ids": list(selected),
            "metrics": metrics,
            "passed": not failures,
            "failures": failures,
        }

    return {
        "id": case.case_id,
        "k": case.k,
        "expected_record_ids": list(case.expected_record_ids),
        "request": case.request.to_dict(),
        "notes": case.notes,
        "variants": variant_results,
    }


def select_variant_records(
    variant: str,
    request: DraftRequest,
    *,
    library_entries: tuple[ReferenceEntry, ...],
    shortcuts: dict[str, tuple[str, ...]],
    index: StyleMemoryIndex,
    k: int,
) -> tuple[str, ...]:
    normalized = variant.strip().lower().replace("-", "_")
    if normalized == "heuristic":
        references = select_references(
            request,
            ReferenceLibrary(entries=library_entries, shortcuts=shortcuts),
        )
        return tuple(reference_record_id(reference.ref_id) for reference in references[:k])
    if normalized == "style_memory":
        query = style_memory_query_from_request(request)
        query = type(query)(
            text=query.text,
            platform=query.platform,
            post_type=query.post_type,
            topics=query.topics,
            mood=query.mood,
            source_types=("reference_example",),
        )
        matches = retrieve_style_memory(index, query, limit=k)
        return tuple(match.record.record_id for match in matches)
    if normalized == "hybrid":
        style_ids = select_variant_records(
            "style_memory",
            request,
            library_entries=library_entries,
            shortcuts=shortcuts,
            index=index,
            k=k,
        )
        heuristic_ids = select_variant_records(
            "heuristic",
            request,
            library_entries=library_entries,
            shortcuts=shortcuts,
            index=index,
            k=k,
        )
        return interleave_unique(style_ids, heuristic_ids, limit=k)
    raise ValueError(f"unknown retrieval variant: {variant}")


def retrieval_metrics(
    selected_record_ids: Sequence[str],
    expected_record_ids: Sequence[str],
    *,
    k: int,
) -> dict[str, Any]:
    selected = tuple(selected_record_ids[:k])
    expected = tuple(expected_record_ids)
    expected_set = set(expected)
    hits = [record_id for record_id in selected if record_id in expected_set]
    first_rank = next(
        (index + 1 for index, record_id in enumerate(selected) if record_id in expected_set),
        None,
    )
    precision = len(hits) / len(selected) if selected else 0.0
    recall = len(set(hits)) / len(expected_set) if expected_set else 0.0
    mrr = 1 / first_rank if first_rank else 0.0
    return {
        "hits": hits,
        "hit_count": len(set(hits)),
        "precision_at_k": round(precision, 4),
        "recall_at_k": round(recall, 4),
        "mrr": round(mrr, 4),
        "first_hit_rank": first_rank,
    }


def aggregate_variant_metrics(
    case_results: list[dict[str, Any]],
    variants: Sequence[str],
) -> dict[str, Any]:
    aggregate = {}
    for variant in variants:
        variant_cases = [case["variants"][variant] for case in case_results]
        count = len(variant_cases)
        aggregate[variant] = {
            "mean_precision_at_k": round(
                sum(item["metrics"]["precision_at_k"] for item in variant_cases) / count,
                4,
            ),
            "mean_recall_at_k": round(
                sum(item["metrics"]["recall_at_k"] for item in variant_cases) / count,
                4,
            ),
            "mean_mrr": round(
                sum(item["metrics"]["mrr"] for item in variant_cases) / count,
                4,
            ),
            "failed_cases": sum(1 for item in variant_cases if not item["passed"]),
            "passed": all(item["passed"] for item in variant_cases),
        }
    return aggregate


def choose_winner(aggregate: dict[str, Any]) -> str | None:
    if not aggregate:
        return None
    ranked = sorted(
        aggregate.items(),
        key=lambda item: (
            item[1]["passed"],
            item[1]["mean_recall_at_k"],
            item[1]["mean_mrr"],
            item[1]["mean_precision_at_k"],
        ),
        reverse=True,
    )
    return ranked[0][0]


def format_retrieval_report(result: dict[str, Any]) -> str:
    lines = [
        f"# Retrieval Experiment Report - {result['suite']}",
        "",
        f"- Total cases: {result['total_cases']}",
        f"- Variants: {', '.join(result['variants'])}",
        f"- Winner: {result['winner'] or 'n/a'}",
        f"- Status: {'pass' if result['passed'] else 'fail'}",
        "",
        "## Aggregate",
        "",
    ]
    for variant, metrics in result["aggregate"].items():
        status = "pass" if metrics["passed"] else "fail"
        lines.append(
            "- "
            f"`{variant}` ({status}): "
            f"precision@k={metrics['mean_precision_at_k']}, "
            f"recall@k={metrics['mean_recall_at_k']}, "
            f"mrr={metrics['mean_mrr']}, "
            f"failed_cases={metrics['failed_cases']}"
        )

    lines.extend(["", "## Cases", ""])
    for case in result["cases"]:
        lines.append(f"### {case['id']}")
        lines.append("")
        lines.append("Expected: " + ", ".join(case["expected_record_ids"]))
        for variant, item in case["variants"].items():
            metrics = item["metrics"]
            status = "pass" if item["passed"] else "fail"
            lines.append(
                "- "
                f"`{variant}` ({status}): "
                f"selected {', '.join(item['selected_record_ids'])}; "
                f"recall@k={metrics['recall_at_k']}, mrr={metrics['mrr']}"
            )
            for failure in item["failures"]:
                lines.append(f"  - {failure}")
        lines.append("")
    return "\n".join(lines)


def normalize_reference_record_id(value: str) -> str:
    clean = value.strip()
    if clean.startswith("reference:"):
        return clean
    if clean.startswith("REF-"):
        return reference_record_id(clean)
    return clean


def reference_record_id(ref_id: str) -> str:
    return f"reference:{ref_id}"


def interleave_unique(
    primary: Sequence[str],
    secondary: Sequence[str],
    *,
    limit: int,
) -> tuple[str, ...]:
    merged: list[str] = []
    seen: set[str] = set()
    max_len = max(len(primary), len(secondary))
    for index in range(max_len):
        for group in (primary, secondary):
            if index >= len(group):
                continue
            item = group[index]
            if item in seen:
                continue
            seen.add(item)
            merged.append(item)
            if len(merged) >= limit:
                return tuple(merged)
    return tuple(merged)


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
