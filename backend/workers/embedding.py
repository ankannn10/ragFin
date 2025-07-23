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

# Sparse indexer
from services.sparse_indexer import index_chunks

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

def chunk_subsection_aware(section_data: Dict, chunk_size: int = 500, overlap: int = 50) -> List[Dict]:
    """
    Create chunks based on subsections detected in sectioning.py.
    Returns chunks with item_number and subsection_title metadata.
    """
    chunks = []
    section_name = section_data["section"]
    subsections = section_data.get("subsections", [])
    
    # Extract item number from section name (e.g., "ITEM 1." -> "ITEM 1")
    item_number = section_name.replace(".", "").strip()
    
    if not subsections:
        # No subsections detected, use traditional chunking
        section_text = section_data["text"]
        text_chunks = chunk_text(section_text, chunk_size, overlap)
        
        for idx, chunk in enumerate(text_chunks):
            chunks.append({
                "text": chunk,
                "item_number": item_number,
                "subsection_title": f"{item_number} - Full Content",
                "chunk_idx": idx,
                "subsection_start_pos": 0,
                "subsection_end_pos": len(section_text)
            })
    else:
        # Create chunks based on detected subsections
        chunk_idx = 0
        
        for subsection in subsections:
            subsection_title = subsection["title"]
            subsection_content = subsection["content"]
            
            # Skip very short subsections
            if len(subsection_content) < 100:
                continue
                
            # Create chunks within this subsection
            text_chunks = chunk_text(subsection_content, chunk_size, overlap)
            
            for sub_idx, chunk in enumerate(text_chunks):
                # Skip very short chunks
                if len(chunk.strip()) < 50:
                    continue
                    
                chunks.append({
                    "text": chunk,
                    "item_number": item_number,
                    "subsection_title": subsection_title,
                    "chunk_idx": chunk_idx,
                    "subsection_chunk_idx": sub_idx,
                    "subsection_start_pos": subsection["start_pos"],
                    "subsection_end_pos": subsection["end_pos"]
                })
                chunk_idx += 1
    
    return chunks


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

        # 2) re-chunk each section using subsection-aware chunking
        chunks: List[Dict] = []
        for sec in sections:
            section_name = sec["section"]
            
            # Get enhanced metadata if available
            page_range = sec.get("page_range", [1, 1])
            cross_references = sec.get("cross_references", [])
            
            # Use subsection-aware chunking
            section_chunks = chunk_subsection_aware(sec)
            
            for chunk in section_chunks:
                chunk_data = {
                    "section": section_name,
                    "chunk_idx": chunk["chunk_idx"],
                    "text": chunk["text"],
                    "page_range": page_range,
                    "cross_references": cross_references,
                    # New subsection metadata
                    "item_number": chunk["item_number"],
                    "subsection_title": chunk["subsection_title"],
                    "subsection_chunk_idx": chunk.get("subsection_chunk_idx", 0),
                    "subsection_start_pos": chunk.get("subsection_start_pos", 0),
                    "subsection_end_pos": chunk.get("subsection_end_pos", 0)
                }
                chunks.append(chunk_data)

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
                    "page_range": ch.get("page_range", [1, 1]),
                    "cross_references": ch.get("cross_references", []),
                    # New subsection metadata for retrieval boosting
                    "item_number": ch.get("item_number", ""),
                    "subsection_title": ch.get("subsection_title", ""),
                    "subsection_chunk_idx": ch.get("subsection_chunk_idx", 0),
                    "subsection_start_pos": ch.get("subsection_start_pos", 0),
                    "subsection_end_pos": ch.get("subsection_end_pos", 0)
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

        # 7) index the same chunks into Elasticsearch (sparse)
        try:
            index_chunks(chunks, filename)
        except Exception as exc:
            # Do not fail the task if ES is temporarily unavailable
            print(f"[EMBED] Warning: failed sparse index for {filename}: {exc}")

        print(
            f"[EMBED] {filename}: {len(points)} chunks (dim={vector_dim}) → "
            f"dense={settings.qdrant_collection} | sparse={settings.es_index}"
        )
        
    except Exception as e:
        print(f"[EMBED] Task failed for {filename}: {e}")
        raise
