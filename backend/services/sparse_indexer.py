from __future__ import annotations

"""Sparse (BM25) indexing helpers for Elasticsearch.

This module is responsible for:
1. Ensuring the index exists with the correct mappings.
2. Bulk-indexing section-level chunks.
3. Performing BM25 search and returning top-k hits.

The low-level Elasticsearch logic is isolated here so both the worker
pipeline (for indexing) and the hybrid retriever (for querying) can share
one implementation.
"""

from typing import List, Dict, Any

from elasticsearch import Elasticsearch, helpers
from app.config import settings

# ---------------------------------------------------------------------------
# 1.  Client & index initialisation
# ---------------------------------------------------------------------------

es = Elasticsearch(settings.es_host, verify_certs=False)


def _init_index() -> None:
    """Create the sparse index with simple mappings if it does not exist."""
    if es.indices.exists(index=settings.es_index):
        return

    es.indices.create(
        index=settings.es_index,
        body={
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
            },
            "mappings": {
                "properties": {
                    "filename": {"type": "keyword"},
                    "section": {"type": "keyword"},
                    "chunk_idx": {"type": "integer"},
                    "text": {"type": "text"},  # BM25 default
                }
            },
        },
        ignore=400,  # ignore "index already exists" errors
    )


# Ensure index exists on module import (safe in local dev)
try:
    _init_index()
except Exception as e:
    # In worker boot order Elasticsearch may not be up yet.
    # The caller should retry on failure.
    print(f"[SPARSE] Failed to create index: {e}")


# ---------------------------------------------------------------------------
# 2.  Bulk indexing helper
# ---------------------------------------------------------------------------

def index_chunks(chunks: List[Dict], filename: str) -> None:
    """Index a list of chunk dictionaries into Elasticsearch.

    Each *chunk* is expected to contain at least keys:
        {"text": str, "section": str, "chunk_idx": int}
    Additional keys are ignored.
    """
    actions = (
        {
            "_index": settings.es_index,
            "_source": {
                "filename": filename,
                "section": c["section"],
                "chunk_idx": c["chunk_idx"],
                "text": c["text"],
            },
        }
        for c in chunks
    )

    try:
        helpers.bulk(es, actions)
        print(f"[SPARSE] Indexed {len(chunks)} chunks from {filename} → {settings.es_index}")
    except Exception as exc:
        print(f"[SPARSE] Failed bulk index ({filename}): {exc}")


# ---------------------------------------------------------------------------
# 3.  BM25 search helper (optional, not used directly by hybrid retriever)
# ---------------------------------------------------------------------------

def bm25_search(query: str, top_k: int = 10, filename: str | None = None) -> List[Dict[str, Any]]:
    """Return Elasticsearch BM25 hits as list[{payload, score}]."""
    must_clause: List[Dict[str, Any]] = [{"match": {"text": query}}]
    if filename:
        must_clause.append({"term": {"filename": filename}})

    body = {
        "query": {"bool": {"must": must_clause}},
        "size": top_k,
    }

    resp = es.search(index=settings.es_index, body=body)
    return [
        {
            "payload": hit["_source"],
            "score": hit["_score"],
        }
        for hit in resp.get("hits", {}).get("hits", [])
    ] 