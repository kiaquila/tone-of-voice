from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


EMOJI_PATTERN = re.compile(
    "["
    "©®"           # © ® (copyright, registered)
    " -➿"          # misc symbols and dingbats (consolidated, replaces two overlapping ranges)
    "⤴-⤵"          # curved arrows
    "〰〽"           # wavy dash, part alternation mark
    "\U0001f000-\U0001f2ff"         # mahjong, playing cards, enclosed alphanumeric supplement
    "\U0001f1e6-\U0001f1ff"         # regional indicators (flags)
    "\U0001f300-\U0001f5ff"         # misc symbols and pictographs
    "\U0001f600-\U0001f64f"  # emoticons
    "\U0001f680-\U0001f6ff"  # transport and map
    "\U0001f700-\U0001f77f"  # alchemical symbols
    "\U0001f780-\U0001f7ff"  # geometric shapes extended
    "\U0001f800-\U0001f8ff"  # supplemental arrows
    "\U0001f900-\U0001f9ff"  # supplemental symbols and pictographs
    "\U0001fa00-\U0001fa6f"  # chess symbols
    "\U0001fa70-\U0001faff"  # symbols and pictographs extended-A
    "]"
)


STOP_WORDS = {
    "и",
    "в",
    "во",
    "не",
    "что",
    "он",
    "на",
    "я",
    "с",
    "со",
    "как",
    "а",
    "то",
    "все",
    "она",
    "так",
    "его",
    "но",
    "да",
    "ты",
    "к",
    "у",
    "же",
    "вы",
    "за",
    "бы",
    "по",
    "только",
    "ее",
    "мне",
    "было",
    "вот",
    "от",
    "меня",
    "еще",
    "нет",
    "о",
    "из",
    "ему",
    "теперь",
    "когда",
    "даже",
    "ну",
    "ли",
    "если",
    "или",
    "ни",
    "до",
    "там",
    "потом",
    "для",
    "мы",
    "их",
    "чем",
    "сам",
    "раз",
    "под",
    "будет",
    "кто",
    "этот",
    "того",
    "потому",
    "какой",
    "совсем",
    "здесь",
    "один",
    "почти",
    "мой",
    "тем",
    "чтобы",
    "сейчас",
    "куда",
    "можно",
    "при",
    "после",
    "над",
    "тот",
    "через",
    "эти",
    "нас",
    "про",
    "какая",
    "много",
    "эту",
    "моя",
    "хорошо",
    "свою",
    "этой",
    "иногда",
    "том",
    "такой",
    "им",
    "более",
    "всегда",
    "очень",
    "просто",
    "пока",
    "сразу",
    "который",
    "которые",
    "которая",
    "которое",
}


def read_jsonl(path: str) -> list[dict]:
    records: list[dict] = []
    with Path(path).expanduser().resolve().open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def _median(values: list[int]) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    mid = len(sorted_values) // 2
    if len(sorted_values) % 2:
        return float(sorted_values[mid])
    return (sorted_values[mid - 1] + sorted_values[mid]) / 2


def _mean(values: list[int]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 1)


def _tokenize(text: str) -> list[str]:
    words = re.findall(r"[A-Za-zА-Яа-яЁё0-9_\-]{3,}", text.lower())
    return [word for word in words if word not in STOP_WORDS and not word.startswith("http")]


def compute_corpus_metrics(records: list[dict], top_n: int = 15) -> dict:
    lengths = [len(record.get("raw_text", "")) for record in records]
    line_counts = [record.get("raw_text", "").count("\n") + 1 for record in records]
    texts = [record.get("raw_text", "") for record in records]

    starters = Counter()
    tokens = Counter()
    for text in texts:
        stripped = text.strip()
        if not stripped:
            continue
        first = re.split(r"\s+", stripped, maxsplit=1)[0].lower().strip(
            "\"«»“”()[]{}.,!?:;"
        )
        if first:
            starters[first] += 1
        tokens.update(_tokenize(text))

    date_values = [record.get("published_at") for record in records if record.get("published_at")]

    return {
        "total_posts": len(records),
        "date_range": {
            "first": min(date_values) if date_values else None,
            "last": max(date_values) if date_values else None,
        },
        "length": {
            "average": _mean(lengths),
            "median": _median(lengths),
            "min": min(lengths) if lengths else 0,
            "max": max(lengths) if lengths else 0,
        },
        "lines": {
            "average": _mean(line_counts),
        },
        "signals": {
            "posts_with_questions": sum("?" in text for text in texts),
            "posts_with_exclamations": sum("!" in text for text in texts),
            "posts_with_ellipsis": sum("..." in text or "…" in text for text in texts),
            "posts_with_emoji": sum(
                bool(EMOJI_PATTERN.search(text)) for text in texts
            ),
            "posts_with_links": sum(
                "http://" in text or "https://" in text for text in texts
            ),
            "posts_with_markdown_links": sum("](" in text for text in texts),
        },
        "top_starters": starters.most_common(top_n),
        "top_tokens": tokens.most_common(top_n),
    }


def format_metrics_markdown(channel: str, metrics: dict) -> str:
    date_range = metrics["date_range"]
    length = metrics["length"]
    lines = metrics["lines"]
    signals = metrics["signals"]

    return "\n".join(
        [
            f"# Telegram Metrics — @{channel}",
            "",
            "## Corpus Snapshot",
            "",
            f"- Total posts: {metrics['total_posts']}",
            f"- Date range: {date_range['first']} to {date_range['last']}",
            f"- Average length: {length['average']}",
            f"- Median length: {length['median']}",
            f"- Length min/max: {length['min']} / {length['max']}",
            f"- Average line count: {lines['average']}",
            "",
            "## Signals",
            "",
            f"- Posts with questions: {signals['posts_with_questions']}",
            f"- Posts with exclamations: {signals['posts_with_exclamations']}",
            f"- Posts with ellipsis: {signals['posts_with_ellipsis']}",
            f"- Posts with emoji: {signals['posts_with_emoji']}",
            f"- Posts with links: {signals['posts_with_links']}",
            f"- Posts with markdown links: {signals['posts_with_markdown_links']}",
            "",
            "## Top Starters",
            "",
            *[f"- `{starter}` — {count}" for starter, count in metrics["top_starters"]],
            "",
            "## Top Tokens",
            "",
            *[f"- `{token}` — {count}" for token, count in metrics["top_tokens"]],
            "",
        ]
    )
