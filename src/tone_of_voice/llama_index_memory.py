from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from llama_index.core import Document, StorageContext, VectorStoreIndex, load_index_from_storage
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.schema import NodeWithScore
from llama_index.core.vector_stores import FilterOperator, MetadataFilter, MetadataFilters

from tone_of_voice.config import repo_root
from tone_of_voice.style_memory import (
    StyleMemoryIndex,
    StyleMemoryMatch,
    StyleMemoryQuery,
    StyleMemoryRecord,
    text_tokens,
)


LLAMA_INDEX_SCHEMA_VERSION = 1
DEFAULT_LLAMA_INDEX_DIR = "data/working/style-memory/llama-index"
LLAMA_INDEX_MANIFEST = "tone-of-voice-manifest.json"


@dataclass(frozen=True)
class LlamaIndexStyleMemory:
    index: VectorStoreIndex
    persist_dir: Path
    fingerprint: str


class HashingStyleEmbedding(BaseEmbedding):
    """Deterministic local embedding for CI-friendly LlamaIndex retrieval."""

    dimensions: int = 384

    @classmethod
    def class_name(cls) -> str:
        return "tone_of_voice_hashing_style_embedding"

    def _get_query_embedding(self, query: str) -> list[float]:
        return self._embed(query)

    async def _aget_query_embedding(self, query: str) -> list[float]:
        return self._embed(query)

    def _get_text_embedding(self, text: str) -> list[float]:
        return self._embed(text)

    def _get_text_embeddings(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = text_tokens(text)
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


def build_or_load_llama_index(
    style_index: StyleMemoryIndex,
    *,
    persist_dir: str | Path = DEFAULT_LLAMA_INDEX_DIR,
    root: Path | None = None,
    rebuild: bool = False,
) -> LlamaIndexStyleMemory:
    base = root or repo_root()
    target_dir = Path(persist_dir).expanduser()
    if not target_dir.is_absolute():
        target_dir = base / target_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    fingerprint = llama_index_fingerprint(style_index)
    manifest_path = target_dir / LLAMA_INDEX_MANIFEST
    if not rebuild and manifest_matches(manifest_path, fingerprint):
        storage_context = StorageContext.from_defaults(persist_dir=str(target_dir))
        index = load_index_from_storage(
            storage_context,
            embed_model=HashingStyleEmbedding(),
        )
        return LlamaIndexStyleMemory(
            index=index,
            persist_dir=target_dir,
            fingerprint=fingerprint,
        )

    documents = documents_from_style_memory(style_index)
    storage_context = StorageContext.from_defaults()
    index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        embed_model=HashingStyleEmbedding(),
    )
    index.storage_context.persist(persist_dir=str(target_dir))
    write_manifest(manifest_path, fingerprint, len(documents))
    return LlamaIndexStyleMemory(
        index=index,
        persist_dir=target_dir,
        fingerprint=fingerprint,
    )


def retrieve_llama_index_style_memory(
    style_index: StyleMemoryIndex,
    query: StyleMemoryQuery,
    *,
    limit: int = 8,
    persist_dir: str | Path = DEFAULT_LLAMA_INDEX_DIR,
    root: Path | None = None,
    rebuild: bool = False,
) -> tuple[StyleMemoryMatch, ...]:
    if limit <= 0:
        return ()
    memory = build_or_load_llama_index(
        style_index,
        persist_dir=persist_dir,
        root=root,
        rebuild=rebuild,
    )
    candidate_limit = max(limit * 6, 24)
    retriever_kwargs: dict[str, Any] = {"similarity_top_k": candidate_limit}
    filters = metadata_filters_for_query(query)
    if filters:
        retriever_kwargs["filters"] = filters
    retriever = memory.index.as_retriever(**retriever_kwargs)
    nodes = retriever.retrieve(query.to_search_text())

    records_by_id = {record.record_id: record for record in style_index.records}
    matches: list[StyleMemoryMatch] = []
    seen: set[str] = set()
    for node in nodes:
        record_id = str(node.node.metadata.get("record_id") or "")
        if record_id in seen:
            continue
        record = records_by_id.get(record_id)
        if record is None:
            continue
        seen.add(record_id)
        match = match_from_node(record, query, node)
        matches.append(match)

    matches.sort(key=lambda item: (-item.score, item.record.record_id))
    return tuple(matches[:limit])


def documents_from_style_memory(style_index: StyleMemoryIndex) -> list[Document]:
    return [
        Document(
            id_=record.record_id,
            text=record_document_text(record),
            metadata=record_metadata(record),
            excluded_embed_metadata_keys=[],
            excluded_llm_metadata_keys=[],
        )
        for record in style_index.records
    ]


def record_document_text(record: StyleMemoryRecord) -> str:
    fields = [
        record.title,
        record.text,
        record.source_type,
        record.platform or "",
        " ".join(record.post_types),
        " ".join(record.topics),
        " ".join(record.mood),
        record.polarity,
        record.scope,
    ]
    return "\n".join(field for field in fields if field).strip()


def record_metadata(record: StyleMemoryRecord) -> dict[str, Any]:
    return {
        "record_id": record.record_id,
        "source_type": record.source_type,
        "title": record.title,
        "source": record.source,
        "platform": record.platform or "general",
        "post_types": " ".join(record.post_types),
        "topics": " ".join(record.topics),
        "mood": " ".join(record.mood),
        "polarity": record.polarity,
        "scope": record.scope,
    }


def metadata_filters_for_query(query: StyleMemoryQuery) -> MetadataFilters | None:
    filters = []
    if query.source_types:
        if len(query.source_types) == 1:
            filters.append(
                MetadataFilter(
                    key="source_type",
                    value=query.source_types[0],
                    operator=FilterOperator.EQ,
                )
            )
        else:
            filters.append(
                MetadataFilter(
                    key="source_type",
                    value=list(query.source_types),
                    operator=FilterOperator.IN,
                )
            )
    return MetadataFilters(filters=filters) if filters else None


def match_from_node(
    record: StyleMemoryRecord,
    query: StyleMemoryQuery,
    node: NodeWithScore,
) -> StyleMemoryMatch:
    score = float(node.score or 0.0) * 100
    reasons = ["llama_index_vector"]
    if query.source_types:
        reasons.append("metadata_filter:source_type")
    if query.platform and record.platform == query.platform:
        score += 8
        reasons.append("platform")
    elif query.platform and record.platform is None:
        score += 2
        reasons.append("general")
    if query.post_type and query.post_type in record.post_types:
        score += 6
        reasons.append("post_type")
    topic_hits = sorted(set(query.topics).intersection(record.topics))
    if topic_hits:
        score += 4 * len(topic_hits)
        reasons.append("topics:" + ",".join(topic_hits))
    mood_hits = sorted(set(query.mood).intersection(record.mood))
    if mood_hits:
        score += 3 * len(mood_hits)
        reasons.append("mood:" + ",".join(mood_hits))
    if record.source_type == "feedback_final":
        score += 2
        reasons.append("feedback_final")
    elif record.source_type == "reference_example":
        score += 1
        reasons.append("reference_example")
    if record.polarity == "corrective":
        reasons.append("corrective_signal")
    return StyleMemoryMatch(
        record=record,
        score=score,
        reasons=tuple(reasons),
    )


def llama_index_fingerprint(style_index: StyleMemoryIndex) -> str:
    payload = {
        "schema_version": LLAMA_INDEX_SCHEMA_VERSION,
        "embedding": HashingStyleEmbedding.class_name(),
        "records": [record.to_dict() for record in style_index.records],
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def manifest_matches(path: Path, fingerprint: str) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return (
        data.get("schema_version") == LLAMA_INDEX_SCHEMA_VERSION
        and data.get("fingerprint") == fingerprint
    )


def write_manifest(path: Path, fingerprint: str, record_count: int) -> None:
    data = {
        "schema_version": LLAMA_INDEX_SCHEMA_VERSION,
        "fingerprint": fingerprint,
        "record_count": record_count,
        "embedding": HashingStyleEmbedding.class_name(),
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
