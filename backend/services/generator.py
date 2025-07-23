#backend/services/generator.py

from typing import List, Dict, Optional
import google.generativeai as genai
from app.config import settings

genai.configure(api_key=settings.gemini_api_key)
_model = genai.GenerativeModel(settings.gemini_model)

PROMPT_TEMPLATE = """\
You are an SEC-filing assistant for financial analysts and hedge fund managers. Use the context to answer the user question.
If the answer is not contained in the context, say "I don't know".

Provide detailed, actionable citations that include section names and chunk information for traceability.
When citing financial information, include specific metrics and trends where available.

{conversation_context}

###
Context:
{context}

###
Question: {question}
Answer (concise, with detailed citations including section names and financial context where relevant):
"""

def _get_materiality_indicator(section: str, text: str) -> str:
    """Determine materiality indicator based on section and content."""
    section_upper = section.upper()
    text_upper = text.upper()
    
    # High materiality indicators
    if any(keyword in text_upper for keyword in ['REVENUE', 'PROFIT', 'LOSS', 'RISK', 'LIABILITY', 'DEBT']):
        if 'ITEM 1A' in section_upper:  # Risk Factors
            return "HIGH RISK"
        elif 'ITEM 7' in section_upper:  # MD&A
            return "FINANCIAL"
        elif 'ITEM 8' in section_upper:  # Financial Statements
            return "FINANCIAL"
    
    # Medium materiality
    if any(keyword in text_upper for keyword in ['COMPETITION', 'REGULATION', 'COMPLIANCE', 'OPERATIONS']):
        return "OPERATIONAL"
    
    return "INFORMATIONAL"

def build_context(chunks: List[Dict]) -> str:
    """Concatenate retrieved chunks with detailed citation numbers for financial analysis."""
    context_parts = []
    for i, chunk in enumerate(chunks):
        section = chunk.get('section', 'UNKNOWN')
        chunk_idx = chunk.get('chunk_idx', 0)
        text = chunk.get('text', '')
        page_range = chunk.get('page_range', [1, 1])
        cross_references = chunk.get('cross_references', [])
        
        # Determine materiality indicator
        materiality = _get_materiality_indicator(section, text)
        
        # Create clean citation format for hedge fund managers (no chunk info)
        if page_range[0] == page_range[1]:
            page_info = f"p.{page_range[0]}"
        else:
            page_info = f"pp.{page_range[0]}-{page_range[1]}"
        
        citation = f"[{i+1}] {section} ({materiality}, {page_info})"
        
        # Add cross-reference information if available
        if cross_references:
            ref_info = []
            for ref in cross_references[:3]:  # Limit to first 3 references
                ref_info.append(f"→ {ref['target_section']}")
            if ref_info:
                citation += f" [Refs: {', '.join(ref_info)}]"
        
        context_parts.append(f"{citation}\n{text}")
    
    return "\n\n".join(context_parts)

def build_conversation_context(conversation_history: Optional[List] = None) -> str:
    """Build conversation context from recent turns."""
    if not conversation_history:
        return ""
    
    context_lines = ["###", "Recent Conversation:"]
    for turn in conversation_history[-3:]:  # Last 3 turns for context
        context_lines.append(f"User: {turn.user_query}")
        context_lines.append(f"AI: {turn.ai_response}")
    context_lines.append("")  # Empty line before main context
    
    return "\n".join(context_lines)

def generate_answer(question: str, chunks: List[Dict], conversation_history: Optional[List] = None) -> str:
    conversation_context = build_conversation_context(conversation_history)
    prompt = PROMPT_TEMPLATE.format(
        conversation_context=conversation_context,
        context=build_context(chunks), 
        question=question
    )
    response = _model.generate_content(prompt)
    return response.text  # plain string

def stream_answer(question: str, chunks: List[Dict], conversation_history: Optional[List] = None):
    """Stream answer for the given question and chunks."""
    conversation_context = build_conversation_context(conversation_history)
    prompt = PROMPT_TEMPLATE.format(
        conversation_context=conversation_context,
        context=build_context(chunks), 
        question=question
    )
    # Use the non-streaming method since streaming is not supported
    result = _model.generate_content(prompt)
    yield result.text  # yield the text content as one chunk
