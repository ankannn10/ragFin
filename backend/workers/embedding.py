# backend/workers/embedding.py
"""
Embed SEC-filing sections and store vectors in Qdrant.

* Uses the free BAAI/bge-small-en-v1.5 model (384-dim, CPU-only)
* Automatically (re)creates the target Qdrant collection with the
  correct vector dimension every run, so mismatches cannot occur.
* Task name: workers.embedding.embed_sections
"""

from __future__ import annotations

import json
import tempfile
import uuid
from typing import List, Dict

import boto3
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, VectorParams, Distance
from qdrant_client.http.exceptions import ApiException

from app.config import settings
from celery_app import celery_app

# ───────────────────────────────────────────────
# 1.  Local embedding model (CPU, 384-dim)
# ───────────────────────────────────────────────
_MODEL = SentenceTransformer("BAAI/bge-small-en-v1.5")


def embed(texts: List[str]) -> List[List[float]]:
    """
    Compute L2-normalised embeddings for a list of texts.
    """
    vecs = _MODEL.encode(
        texts,
        batch_size=64,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return [v.tolist() for v in vecs]


def test_embedding_model():
    """
    Test function to verify the embedding model works correctly.
    """
    test_texts = ["This is a test sentence.", "Another test sentence."]
    embeddings = embed(test_texts)
    print(f"[TEST] Model: {_MODEL.get_sentence_embedding_dimension()} dimensions")
    print(f"[TEST] Generated {len(embeddings)} embeddings")
    print(f"[TEST] First embedding length: {len(embeddings[0])}")
    print(f"[TEST] First embedding sample: {embeddings[0][:5]}...")
    return embeddings


# ───────────────────────────────────────────────
# 2.  Simple word-window chunker
# ───────────────────────────────────────────────
def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Split `text` into `chunk_size`-word windows with `overlap` words overlap.
    """
    words = text.split()
    step = max(chunk_size - overlap, 1)
    return [" ".join(words[i : i + chunk_size]) for i in range(0, len(words), step)]


# ───────────────────────────────────────────────
# 3.  Clients
# ───────────────────────────────────────────────
s3 = boto3.client(
    "s3",
    endpoint_url=settings.s3_endpoint,
    aws_access_key_id=settings.s3_access_key,
    aws_secret_access_key=settings.s3_secret_key,
)
qdrant = QdrantClient(settings.qdrant_url)


# ───────────────────────────────────────────────
# 4.  Celery task
# ───────────────────────────────────────────────
@celery_app.task(name="workers.embedding.embed_sections", bind=True, max_retries=3)
def embed_sections(self, sections_key: str, filename: str):
    """
    sections_key : S3 key of *.sections.jsonl produced by sectioning
    filename     : original filing name (for payload metadata)
    """
    try:
        # Test the embedding model first
        print("[EMBED] Testing embedding model...")
        test_embeddings = test_embedding_model()
        
        # 1) load logical sections
        print(f"[EMBED] Loading sections from {sections_key}")
        body = s3.get_object(
            Bucket="processed-filings", Key=sections_key
        )["Body"].iter_lines()
        sections = [json.loads(line) for line in body]
        print(f"[EMBED] Loaded {len(sections)} sections")

        # 2) re-chunk each section (~500-word windows)
        chunks: List[Dict] = []
        for sec in sections:
            for idx, chunk in enumerate(chunk_text(sec["text"])):
                chunks.append(
                    {"section": sec["section"], "chunk_idx": idx, "text": chunk}
                )

        if not chunks:
            print(f"[EMBED] No chunks found for {filename}")
            return

        print(f"[EMBED] Created {len(chunks)} chunks")

        # 3) embed
        print("[EMBED] Generating embeddings...")
        embeddings = embed([c["text"] for c in chunks])
        vector_dim = len(embeddings[0])          # 384 for bge-small

        print(f"[EMBED] Generated {len(embeddings)} embeddings with dimension {vector_dim}")

        # 4) force collection to match vector_dim every run
        try:
            print(f"[EMBED] Recreating collection {settings.qdrant_collection}...")
            qdrant.recreate_collection(
                collection_name=settings.qdrant_collection,
                vectors_config=VectorParams(size=vector_dim, distance=Distance.COSINE),
            )
            print(f"[EMBED] Successfully recreated collection {settings.qdrant_collection} with dim {vector_dim}")
        except Exception as e:
            print(f"[EMBED] Error recreating collection: {e}")
            raise

        # 5) build points with proper UUIDs
        print("[EMBED] Building points...")
        points = []
        for i, (ch, vec) in enumerate(zip(chunks, embeddings)):
            point = PointStruct(
                id=str(uuid.uuid4()),  # Use UUID instead of string-based ID
                vector=vec,
                payload={
                    "filename": filename,
                    "section": ch["section"],
                    "chunk_idx": ch["chunk_idx"],
                    "text": ch["text"],
                },
            )
            points.append(point)

        print(f"[EMBED] Built {len(points)} points for upsert")

        # 6) upsert with better error handling
        try:
            print(f"[EMBED] Upserting {len(points)} points to {settings.qdrant_collection}...")
            qdrant.upsert(
                collection_name=settings.qdrant_collection,
                wait=True,
                points=points,
            )
            print(f"[EMBED] Successfully upserted {len(points)} points")
        except ApiException as e:
            print(f"[EMBED] Qdrant API error: {e}")
            print(f"[EMBED] Collection: {settings.qdrant_collection}")
            print(f"[EMBED] Points count: {len(points)}")
            if points:
                print(f"[EMBED] First point structure: {points[0]}")
                print(f"[EMBED] First point vector length: {len(points[0].vector)}")
                print(f"[EMBED] First point payload: {points[0].payload}")
            raise
        except Exception as e:
            print(f"[EMBED] Unexpected error during upsert: {e}")
            raise

        print(
            f"[EMBED] {filename}: {len(points)} chunks "
            f"(dim={vector_dim}) → {settings.qdrant_collection}"
        )
        
    except Exception as e:
        print(f"[EMBED] Task failed for {filename}: {e}")
        raise
