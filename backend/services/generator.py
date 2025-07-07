from typing import List, Dict
import google.generativeai as genai
from app.config import settings

genai.configure(api_key=settings.gemini_api_key)
_model = genai.GenerativeModel(settings.gemini_model)

PROMPT_TEMPLATE = """\
You are an SEC-filing assistant. Use the context to answer the user question.
If the answer is not contained in the context, say “I don’t know”.

###
Context:
{context}

###
Question: {question}
Answer (concise, with numbered citations):
"""

def build_context(chunks: List[Dict]) -> str:
    """Concatenate retrieved chunks with inline citation numbers."""
    return "\n\n".join(
        f"[{i+1}] ({c['section']}) {c['text']}" for i, c in enumerate(chunks)
    )

def generate_answer(question: str, chunks: List[Dict]) -> str:
    prompt = PROMPT_TEMPLATE.format(context=build_context(chunks), question=question)
    response = _model.generate_content(prompt)
    return response.text  # plain string

def stream_answer(question: str, chunks: List[Dict]):
    """Stream answer for the given question and chunks."""
    prompt = PROMPT_TEMPLATE.format(context=build_context(chunks), question=question)
    # Use the non-streaming method since streaming is not supported
    result = _model.generate_content(prompt)
    yield result.text  # yield the text content as one chunk
