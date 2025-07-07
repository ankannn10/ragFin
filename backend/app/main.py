from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4
from app.config import settings
from app.dependencies import get_s3
from celery_app import celery_app
from pydantic import BaseModel
from services.retriever import retrieve
from services.generator import generate_answer, _model, stream_answer   # note: _model for embedding size
from sentence_transformers import SentenceTransformer
from utils.sse import sse_stream
from fastapi import Request
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue, ScrollRequest
from app.config import settings

qdrant = QdrantClient(settings.qdrant_url, check_compatibility=False)

app = FastAPI(title="FinSaaS API", version="0.1.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# local embedder (same model as worker)
_embedder = SentenceTransformer("BAAI/bge-small-en-v1.5")

class RAGQuery(BaseModel):
    query: str
    filename: str | None = None
    top_k: int = 5

@app.post("/upload", status_code=202)
async def upload_file(
    file: UploadFile = File(...),
    s3 = Depends(get_s3),
):
    # 1. Generate unique key
    object_key = f"{uuid4()}_{file.filename}"
    # 2. Stream to MinIO/S3
    try:
        s3.upload_fileobj(file.file, settings.s3_bucket_raw, object_key)
    except Exception as e:
        raise HTTPException(500, f"S3 upload failed: {e}")

    # 3. Kick off Celery ingestion task
    task = celery_app.send_task(
        "workers.ingestion.parse_file",
        kwargs={"object_key": object_key, "filename": file.filename},
    )
    return {"task_id": task.id, "message": "File accepted for processing"}

@app.post("/rag/query/")
async def rag_query(payload: RAGQuery):
    # 1) embed question
    q_vec = _embedder.encode(payload.query, normalize_embeddings=True).tolist()

    # 2) retrieve top-k
    chunks = retrieve(q_vec, payload.top_k, payload.filename)

    # 3) generate answer
    answer = generate_answer(payload.query, chunks)

    return {
        "query": payload.query,
        "answer": answer,
        "retrieved_chunks": chunks,
        "num_chunks_retrieved": len(chunks),
        "filter_filename": payload.filename,
    }

@app.post("/rag/stream/")
async def rag_stream(payload: RAGQuery, request: Request):
    q_vec = _embedder.encode(payload.query, normalize_embeddings=True).tolist()
    chunks = retrieve(q_vec, payload.top_k, payload.filename)

    async def gen():
        for token in stream_answer(payload.query, chunks):
            if await request.is_disconnected():
                break
            yield token

    return sse_stream(gen())

@app.get("/rag/stats", include_in_schema=False)
@app.get("/rag/stats/", tags=["RAG"])
def rag_stats():
    """
    Return quick stats for sidebar:
      • total_chunks   : number of points in collection
      • unique_documents : how many distinct filenames
      • documents        : list[str] of filenames (max 100 for perf)
    """
    try:
        info = qdrant.get_collection(settings.qdrant_collection)
        total = info.points_count
    except Exception:
        return {"total_chunks": 0, "unique_documents": 0, "documents": []}

    # scroll to get filenames (payload field "filename")
    filenames: set[str] = set()
    
    # Use the correct API for newer qdrant-client versions
    batch, next_page = qdrant.scroll(
        collection_name=settings.qdrant_collection,
        limit=256,
        with_payload=True,
    )
    
    for p in batch:
        fname = p.payload.get("filename")
        if fname:
            filenames.add(fname)
            if len(filenames) >= 100:  # cap for UI
                break
    
    # Continue scrolling if needed
    while next_page and len(filenames) < 100:
        batch, next_page = qdrant.scroll(
            collection_name=settings.qdrant_collection,
            limit=256,
            with_payload=True,
            offset=next_page,
        )
        for p in batch:
            fname = p.payload.get("filename")
            if fname:
                filenames.add(fname)
                if len(filenames) >= 100:  # cap for UI
                    break

    return {
        "total_chunks": total,
        "unique_documents": len(filenames),
        "documents": sorted(filenames),
    }
