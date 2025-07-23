#backend/app/main.py

import json
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4
from app.config import settings
from app.dependencies import get_s3
from celery_app import celery_app
from pydantic import BaseModel
from services.retriever import retrieve
from services.generator import generate_answer, _model, stream_answer   # note: _model for embedding size
from services.conversation import get_conversation_manager
from sentence_transformers import SentenceTransformer
from utils.sse import sse_stream
from fastapi import Request
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue, ScrollRequest
from app.config import settings
import re

qdrant = QdrantClient(settings.qdrant_url, check_compatibility=False)

# Initialize embedder
_embedder = SentenceTransformer("BAAI/bge-small-en-v1.5")

def embed_text(text: str):
    """Helper function to embed text."""
    return _embedder.encode(text, normalize_embeddings=True).tolist()

app = FastAPI(title="FinSaaS API", version="0.1.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RAGQuery(BaseModel):
    query: str
    filename: str | None = None
    top_k: int = 5
    session_id: str | None = None

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
    # Get conversation manager
    conv_manager = get_conversation_manager()
    
    # Generate default session_id if not provided
    session_id = payload.session_id or str(uuid4())
    
    # Get conversation history for context
    summary, history = conv_manager.get_full_context(session_id)
    
    # Rewrite query with context if it's a follow-up
    original_query = payload.query
    rewritten_query = original_query
    if conv_manager.is_followup_query(original_query):
        rewritten_query = conv_manager.rewrite_query_with_context(original_query, history)
    
    # Log the rewriting for debugging
    if rewritten_query != original_query:
        print(f"[CONVERSATION] Rewritten query: '{original_query}' -> '{rewritten_query}'")
    
    # 1) Enhanced retrieval for comparison queries
    top_k = payload.top_k or 5
    if any(word in rewritten_query.lower() for word in ['compare', 'vs', 'versus', 'between']):
        top_k = max(top_k, 8)  # Get more chunks for comparison queries
    
    # Extract years from query for potential multi-year retrieval
    years_in_query = re.findall(r'\b(20\d{2})\b', rewritten_query)
    if len(years_in_query) > 1:
        top_k = max(top_k, 10)  # Get even more chunks for multi-year queries

    # 2) embed question and retrieve (use rewritten query)
    q_vec = embed_text(rewritten_query)
    chunks = retrieve(q_vec, rewritten_query, top_k, payload.filename)

    # 3) generate answer (use rewritten query for context)
    answer = generate_answer(rewritten_query, chunks, history)
    
    # 4) Store this turn in conversation history
    conv_manager.add_turn(session_id, original_query, answer)

    return {
        "query": original_query,
        "rewritten_query": rewritten_query if rewritten_query != original_query else None,
        "answer": answer,
        "retrieved_chunks": chunks,
        "num_chunks_retrieved": len(chunks),
        "filter_filename": payload.filename,
        "session_id": session_id,
    }

@app.post("/rag/stream/")
async def rag_stream(payload: RAGQuery, request: Request):
    session_id = payload.session_id or str(uuid4())
    original_query = payload.query
    
    # 1) Get conversation history for context
    conv_manager = get_conversation_manager()
    summary, history = conv_manager.get_full_context(session_id)
    
    # 2) Rewrite query if it's a follow-up
    rewritten_query = original_query
    if conv_manager.is_followup_query(original_query):
        rewritten_query = conv_manager.rewrite_query_with_context(original_query, history)
        print(f"[CONVERSATION] Streaming - Rewritten query: '{original_query}' -> '{rewritten_query}'")
    
    # 3) Enhanced retrieval for comparison queries
    top_k = 5
    if any(word in rewritten_query.lower() for word in ['compare', 'vs', 'versus', 'between']):
        top_k = 8  # Get more chunks for comparison queries
    
    # Extract years from query for potential multi-year retrieval
    years_in_query = re.findall(r'\b(20\d{2})\b', rewritten_query)
    if len(years_in_query) > 1:
        top_k = 10  # Get even more chunks for multi-year queries
    
    query_vec = embed_text(rewritten_query)
    chunks = retrieve(query_vec, rewritten_query, top_k=top_k, filename=payload.filename)
    
    # 4) Stream generation with full context
    full_answer = ""

    async def gen():
        nonlocal full_answer
        for token in stream_answer(rewritten_query, chunks, history):
            if await request.is_disconnected():
                break
            full_answer += token
            yield token

        # After streaming is complete, store the conversation turn
        if full_answer:
            conv_manager.add_turn(session_id, original_query, full_answer)
    
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





@app.get("/conversation/history/{session_id}")
async def get_conversation_history(session_id: str, limit: int = 10):
    """Get conversation history for a session including summary."""
    try:
        conv_manager = get_conversation_manager()
        summary, recent_turns = conv_manager.get_full_context(session_id)
        
        # Apply limit to recent turns if specified
        if limit and len(recent_turns) > limit:
            recent_turns = recent_turns[-limit:]
        
        response = {
            "session_id": session_id,
            "recent_turns": [turn.to_dict() for turn in recent_turns],
            "total_recent_turns": len(recent_turns)
        }
        
        if summary:
            response["summary"] = {
                "text": summary.summary_text,
                "turn_count": summary.turn_count,
                "timestamp_range": summary.timestamp_range,
                "token_count": summary.get_token_count()
            }
        else:
            response["summary"] = None
        
        return response
    except Exception as e:
        raise HTTPException(500, f"Error retrieving conversation history: {e}")


@app.delete("/conversation/history/{session_id}")
async def clear_conversation_history(session_id: str):
    """Clear conversation history for a session."""
    try:
        conv_manager = get_conversation_manager()
        conv_manager.clear_session(session_id)
        
        return {
            "session_id": session_id,
            "message": "Conversation history cleared successfully"
        }
    except Exception as e:
        raise HTTPException(500, f"Error clearing conversation history: {e}")


@app.get("/conversation/stats/{session_id}")
async def get_conversation_stats(session_id: str):
    """Get conversation statistics including token usage and summarization info."""
    try:
        conv_manager = get_conversation_manager()
        summary, recent_turns = conv_manager.get_full_context(session_id)
        
        # Calculate token statistics
        total_tokens = 0
        recent_tokens = 0
        summary_tokens = 0
        
        if summary:
            summary_tokens = summary.get_token_count()
            total_tokens += summary_tokens
        
        for turn in recent_turns:
            turn_tokens = turn.get_token_count()
            recent_tokens += turn_tokens
            total_tokens += turn_tokens
        
        return {
            "session_id": session_id,
            "token_usage": {
                "total_tokens": total_tokens,
                "recent_tokens": recent_tokens,
                "summary_tokens": summary_tokens,
                "max_tokens": conv_manager.memory.max_total_tokens
            },
            "conversation_stats": {
                "recent_turns_count": len(recent_turns),
                "max_recent_turns": conv_manager.memory.max_recent_turns,
                "summarized_turns_count": summary.turn_count if summary else 0,
                "has_summary": summary is not None
            },
            "summarization_status": {
                "enabled": conv_manager.memory.enable_summarization,
                "will_summarize_next": total_tokens > conv_manager.memory.max_total_tokens * 0.8,  # 80% threshold
                "summary_timestamp_range": summary.timestamp_range if summary else None
            }
        }
    except Exception as e:
        raise HTTPException(500, f"Error retrieving conversation stats: {e}")


@app.post("/conversation/test-rewrite")
async def test_query_rewrite(payload: dict):
    """Test endpoint to see how queries would be rewritten with context."""
    try:
        conv_manager = get_conversation_manager()
        
        query = payload.get("query", "")
        mock_history = payload.get("history", [])
        
        # Convert mock history to ConversationTurn objects
        from services.conversation import ConversationTurn
        history_turns = [ConversationTurn.from_dict(turn) for turn in mock_history]
        
        is_followup = conv_manager.is_followup_query(query)
        rewritten = conv_manager.rewrite_query_with_context(query, history_turns)
        
        return {
            "original_query": query,
            "is_followup": is_followup,
            "rewritten_query": rewritten,
            "history_used": len(history_turns)
        }
    except Exception as e:
        raise HTTPException(500, f"Error testing query rewrite: {e}")


@app.post("/conversation/force-summarize/{session_id}")
async def force_summarize_conversation(session_id: str):
    """Force summarization of a conversation session (for testing)."""
    try:
        conv_manager = get_conversation_manager()
        
        # Get current state
        summary, recent_turns = conv_manager.get_full_context(session_id)
        
        if len(recent_turns) < 2:
            return {
                "session_id": session_id,
                "message": "Not enough turns to summarize (minimum 2 required)",
                "turns_available": len(recent_turns)
            }
        
        # Force summarization by temporarily lowering the threshold
        original_max_turns = conv_manager.memory.max_recent_turns
        conv_manager.memory.max_recent_turns = 1  # Force summarization
        
        # Trigger summarization check
        conv_manager.memory._check_and_summarize(session_id)
        
        # Restore original setting
        conv_manager.memory.max_recent_turns = original_max_turns
        
        # Get updated state
        new_summary, new_recent_turns = conv_manager.get_full_context(session_id)
        
        return {
            "session_id": session_id,
            "message": "Summarization completed",
            "before": {
                "recent_turns": len(recent_turns),
                "had_summary": summary is not None
            },
            "after": {
                "recent_turns": len(new_recent_turns),
                "has_summary": new_summary is not None,
                "summary_turn_count": new_summary.turn_count if new_summary else 0,
                "summary_text": new_summary.summary_text if new_summary else None
            }
        }
    except Exception as e:
        raise HTTPException(500, f"Error forcing summarization: {e}")



