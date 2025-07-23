"""Hybrid retriever that fuses dense (Qdrant) and sparse (Elasticsearch BM25)
scores using a weighted average.

final_score = α * dense_score_norm + (1 - α) * sparse_score_norm

Returned chunks include diagnostic scores for debugging.
"""

from __future__ import annotations

import re
from typing import List, Dict, Any, Tuple, Optional

from qdrant_client import QdrantClient, models  # type: ignore
from elasticsearch import Elasticsearch        # type: ignore

from app.config import settings

# ---------------------------------------------------------------------------
# 1.  Clients
# ---------------------------------------------------------------------------

qdrant = QdrantClient(settings.qdrant_url, check_compatibility=False)
es = Elasticsearch(settings.es_host, verify_certs=False)

# ---------------------------------------------------------------------------
# 2.  Section name extraction
# ---------------------------------------------------------------------------

def extract_section_name(query: str) -> Optional[str]:
    """
    Extract SEC section names from queries like:
    - "What is Item 1A?" -> "ITEM 1A."
    - "Tell me about Item 2" -> "ITEM 2."
    - "What does Item 1B contain?" -> "ITEM 1B."
    """
    # Pattern to match Item numbers with optional letters
    pattern = r'\bItem\s+(\d+[A-Za-z]?)\b'
    match = re.search(pattern, query, re.IGNORECASE)
    
    if match:
        item_num = match.group(1).upper()
        return f"ITEM {item_num}."
    
    return None

def analyze_query_for_subsections(query: str) -> Dict[str, Any]:
    """
    Analyze query to detect terms that should boost specific subsections.
    Returns boosting configuration based on query content.
    """
    query_lower = query.lower()
    
    # Define subsection boost mappings based on common 10-K terminology
    boost_mappings = {
        # Programs and Incentives
        "programs_incentives": {
            "keywords": ["programs", "incentives", "program", "incentive", "benefits", "grants", "funding"],
            "subsection_patterns": [
                r"programs?\s+and\s+incentives?",
                r"incentives?",
                r"government\s+programs?",
                r"benefits"
            ],
            "boost_score": 1.5
        },
        # Tax Credits
        "tax_credits": {
            "keywords": ["tax", "credit", "credits", "deduction", "deductions", "tax benefits"],
            "subsection_patterns": [
                r"tax\s+credits?",
                r"tax\s+benefits?",
                r"tax\s+deductions?"
            ],
            "boost_score": 1.6
        },
        # Regulations
        "regulations": {
            "keywords": ["regulations", "regulation", "regulatory", "compliance", "rules", "requirements"],
            "subsection_patterns": [
                r"regulations?",
                r"regulatory",
                r"compliance",
                r"legal\s+requirements"
            ],
            "boost_score": 1.4
        },
        # Environmental
        "environmental": {
            "keywords": ["environmental", "environment", "climate", "emissions", "sustainability", "green"],
            "subsection_patterns": [
                r"environmental",
                r"climate",
                r"emissions",
                r"sustainability"
            ],
            "boost_score": 1.3
        },
        # Risk Factors
        "risk_factors": {
            "keywords": ["risk", "risks", "factors", "challenges", "uncertainties"],
            "subsection_patterns": [
                r"risk\s+factors",
                r"risks?",
                r"uncertainties"
            ],
            "boost_score": 1.2
        },
        # Competition
        "competition": {
            "keywords": ["competition", "competitive", "competitors", "market share", "rivalry"],
            "subsection_patterns": [
                r"competition",
                r"competitive",
                r"competitors"
            ],
            "boost_score": 1.2
        }
    }
    
    detected_boosts = {}
    
    for category, config in boost_mappings.items():
        # Check for keyword matches
        keyword_matches = sum(1 for keyword in config["keywords"] if keyword in query_lower)
        
        # Check for pattern matches
        pattern_matches = 0
        for pattern in config["subsection_patterns"]:
            if re.search(pattern, query_lower):
                pattern_matches += 1
        
        # Calculate boost strength based on matches
        if keyword_matches > 0 or pattern_matches > 0:
            boost_strength = config["boost_score"]
            # Increase boost for multiple matches
            if keyword_matches > 1 or pattern_matches > 1:
                boost_strength *= 1.2
            
            detected_boosts[category] = {
                "boost_score": min(boost_strength, 2.0),  # Cap boost at 2.0
                "keyword_matches": keyword_matches,
                "pattern_matches": pattern_matches,
                "subsection_patterns": config["subsection_patterns"]
            }
    
    return {
        "boosts": detected_boosts,
        "has_boosts": len(detected_boosts) > 0,
        "max_boost": max((b["boost_score"] for b in detected_boosts.values()), default=1.0)
    }

def apply_subsection_boosting(results: List[Dict[str, Any]], query_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Apply subsection-based score boosting to retrieval results.
    """
    if not query_analysis["has_boosts"]:
        return results
    
    boosted_results = []
    
    for result in results:
        payload = result.get("payload", result)
        subsection_title = payload.get("subsection_title", "").lower()
        original_score = result.get("score", 0.0)
        
        # Calculate boost multiplier based on subsection title
        boost_multiplier = 1.0
        boost_reasons = []
        
        for category, boost_config in query_analysis["boosts"].items():
            # Check if subsection title matches any boost patterns
            for pattern in boost_config["subsection_patterns"]:
                if re.search(pattern, subsection_title, re.IGNORECASE):
                    boost_multiplier = max(boost_multiplier, boost_config["boost_score"])
                    boost_reasons.append(f"{category}: {pattern}")
                    break
        
        # Apply boost
        boosted_score = original_score * boost_multiplier
        
        # Create result with boosting information
        boosted_result = result.copy()
        if "payload" in boosted_result:
            boosted_result["payload"] = payload.copy()
            boosted_result["payload"].update({
                "original_score": original_score,
                "boost_multiplier": boost_multiplier,
                "boost_reasons": boost_reasons,
                "boosted_score": boosted_score
            })
        else:
            boosted_result.update({
                "original_score": original_score,
                "boost_multiplier": boost_multiplier,
                "boost_reasons": boost_reasons,
                "boosted_score": boosted_score
            })
        
        boosted_result["score"] = boosted_score
        boosted_results.append(boosted_result)
    
    # Re-sort by boosted scores
    boosted_results.sort(key=lambda x: x["score"], reverse=True)
    
    return boosted_results


def _search_by_section(section_name: str, top_k: int, filename: str | None) -> List[Dict[str, Any]]:
    """
    Direct search by section name using Qdrant scroll with filter.
    This bypasses semantic search for exact section matches.
    """
    # Build filter for exact section match
    must_conditions = [models.FieldCondition(key="section", match=models.MatchValue(value=section_name))]
    
    if filename:
        must_conditions.append(models.FieldCondition(key="filename", match=models.MatchValue(value=filename)))
    
    search_filter = models.Filter(must=must_conditions)
    
    # Use scroll method instead of query_points
    try:
        hits, _ = qdrant.scroll(
            collection_name=settings.qdrant_collection,
            limit=top_k,
            scroll_filter=search_filter,
            with_payload=True,
        )
        
        return [
            {
                "payload": h.payload,
                "score": 1.0,  # Perfect match for section name
                "search_type": "section_match"
            }
            for h in hits
        ]
    except Exception as e:
        print(f"[ENHANCED_RETRIEVAL] Error in section search: {e}")
        return []

# ---------------------------------------------------------------------------
# 3.  Enhanced retrieval function
# ---------------------------------------------------------------------------

def _dense_search(query_vec: List[float], top_k: int, filename: str | None) -> List[Dict[str, Any]]:
    """Return dense search hits as list[{payload, score}]."""
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
    return [
        {
            "payload": h.payload,
            "score": h.score,
            "search_type": "dense"
        }
        for h in hits
    ]


def _sparse_search(query_text: str, top_k: int, filename: str | None) -> List[Dict[str, Any]]:
    """Return BM25 hits list[{payload, score}]."""
    must_clause: List[Dict[str, Any]] = [{"match": {"text": query_text}}]
    if filename:
        must_clause.append({"term": {"filename": filename}})

    body = {
        "query": {"bool": {"must": must_clause}},
        "size": top_k,
    }

    resp = es.search(index=settings.es_index, body=body)
    hits = resp.get("hits", {}).get("hits", [])
    return [
        {
            "payload": h["_source"],
            "score": h["_score"],
            "search_type": "sparse"
        }
        for h in hits
    ]


def _normalise(scores: List[float]) -> List[float]:
    """Min-max normalise to [0,1]. If all scores equal, return zeros."""
    if not scores:
        return []
    mx = max(scores)
    if mx == 0:
        return [0.0 for _ in scores]
    return [s / mx for s in scores]


def retrieve(
    query_vec: List[float],
    query_text: str,
    top_k: int = 5,
    filename: str | None = None,
    alpha: float = settings.hybrid_alpha,
) -> List[Dict[str, Any]]:
    """Enhanced retrieval with section name extraction and subsection boosting.
    
    First tries to match section names directly, then falls back to hybrid search
    with optional subsection-based score boosting.
    """

    # 0) Analyze query for subsection boosting opportunities
    query_analysis = analyze_query_for_subsections(query_text)
    if query_analysis["has_boosts"]:
        print(f"[ENHANCED_RETRIEVAL] Detected subsection boost triggers: {list(query_analysis['boosts'].keys())}")

    # 1) Try section name extraction first
    section_name = extract_section_name(query_text)
    if section_name:
        print(f"[ENHANCED_RETRIEVAL] Detected section query: '{query_text}' -> '{section_name}'")
        section_hits = _search_by_section(section_name, top_k, filename)
        
        if section_hits:
            print(f"[ENHANCED_RETRIEVAL] Found {len(section_hits)} chunks for section '{section_name}'")
            # Apply subsection boosting even to section matches
            results = []
            for hit in section_hits:
                payload_with_scores = hit["payload"].copy()
                payload_with_scores.update({
                    "score": hit["score"],
                    "dense_score": 1.0,  # Perfect match
                    "sparse_score": 1.0,  # Perfect match
                    "search_type": "section_match"
                })
                results.append(payload_with_scores)
            
            # Apply subsection boosting to section results
            if query_analysis["has_boosts"]:
                results = apply_subsection_boosting(results, query_analysis)
                print(f"[ENHANCED_RETRIEVAL] Applied subsection boosting to {len(results)} section results")
            
            return results
        else:
            print(f"[ENHANCED_RETRIEVAL] No chunks found for section '{section_name}', falling back to hybrid search")

    # 2) Fall back to hybrid search if no section match
    print(f"[ENHANCED_RETRIEVAL] Using hybrid search for query: '{query_text}'")
    
    # Run searches independently
    dense_hits = _dense_search(query_vec, top_k * 2, filename)
    sparse_hits = _sparse_search(query_text, top_k * 2, filename)

    # Normalise scores to [0,1]
    dense_norm = _normalise([h["score"] for h in dense_hits])
    sparse_norm = _normalise([h["score"] for h in sparse_hits])

    for idx, h in enumerate(dense_hits):
        h["dense_score_norm"] = dense_norm[idx]
    for idx, h in enumerate(sparse_hits):
        h["sparse_score_norm"] = sparse_norm[idx]

    # Merge on unique key (filename, section, chunk_idx)
    def _key(p: Dict[str, Any]) -> Tuple[str | None, str | None, int | None]:
        return (
            p.get("filename"),
            p.get("section"),
            p.get("chunk_idx"),
        )

    merged: Dict[Tuple[str | None, str | None, int | None], Dict[str, Any]] = {}

    # add dense first
    for h in dense_hits:
        k = _key(h["payload"])
        merged[k] = {
            "payload": h["payload"],
            "dense_score": h["score"],
            "dense_score_norm": h["dense_score_norm"],
            "sparse_score": 0.0,
            "sparse_score_norm": 0.0,
        }

    # add / update with sparse
    for h in sparse_hits:
        k = _key(h["payload"])
        entry = merged.get(
            k,
            {
                "payload": h["payload"],
                "dense_score": 0.0,
                "dense_score_norm": 0.0,
                "sparse_score": 0.0,
                "sparse_score_norm": 0.0,
            },
        )
        entry["sparse_score"] = h["score"]
        entry["sparse_score_norm"] = h["sparse_score_norm"]
        merged[k] = entry

    # Compute final fusion score
    for m in merged.values():
        m["score"] = alpha * m["dense_score_norm"] + (1 - alpha) * m["sparse_score_norm"]

    # Sort and trim
    ranked = sorted(merged.values(), key=lambda x: x["score"], reverse=True)[:top_k]

    # Attach debug info in payload for transparency
    results = []
    for r in ranked:
        payload_with_scores = r["payload"].copy()
        payload_with_scores.update(
            {
                "score": r["score"],
                "dense_score": r["dense_score"],
                "sparse_score": r["sparse_score"],
                "search_type": "hybrid"
            }
        )
        results.append(payload_with_scores)

    # Apply subsection boosting to hybrid results
    if query_analysis["has_boosts"]:
        results = apply_subsection_boosting(results, query_analysis)
        print(f"[ENHANCED_RETRIEVAL] Applied subsection boosting to {len(results)} hybrid results")

    # Optional log
    print(
        f"[HYBRID] dense={len(dense_hits)} sparse={len(sparse_hits)} → returned={len(results)}"
    )

    return results
