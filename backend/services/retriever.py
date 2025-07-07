from typing import List, Dict
from qdrant_client import QdrantClient, models
from app.config import settings

qdrant = QdrantClient(settings.qdrant_url, check_compatibility=False)

def retrieve(query_vec: List[float], top_k: int = 5, filename: str | None = None) -> List[Dict]:
    """Return top-k payloads [{'text':…, 'section':…}, …]."""
    search_filter = None
    if filename:
        search_filter = models.Filter(
            must=[models.FieldCondition(key="filename", match=models.MatchValue(value=filename))]
        )

    hits = qdrant.search(
        collection_name=settings.qdrant_collection,
        query_vector=query_vec,
        limit=top_k,
        query_filter=search_filter,
    )
    return [h.payload | {"score": h.score} for h in hits]
