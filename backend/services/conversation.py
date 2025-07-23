"""Conversation memory service for RAG pipeline.

This module handles:
1. Session management and chat history storage with summary buffer memory
2. Query rewriting for follow-up questions
3. Context resolution using conversation history
4. Automatic summarization of older messages when token limits are approached
"""

from __future__ import annotations

import json
import redis
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import re
import tiktoken

from app.config import settings

# Redis client for session storage
redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)

# Token encoder for counting tokens (using GPT-3.5/4 tokenizer as approximation)
try:
    tokenizer = tiktoken.get_encoding("cl100k_base")
except Exception:
    # Fallback if tiktoken is not available
    tokenizer = None


def count_tokens(text: str) -> int:
    """Count tokens in text. Fallback to character-based approximation if tiktoken unavailable."""
    if tokenizer:
        return len(tokenizer.encode(text))
    else:
        # Rough approximation: ~4 characters per token
        return len(text) // 4


class ConversationTurn:
    """Represents a single turn in conversation (user query + AI response)."""
    
    def __init__(self, user_query: str, ai_response: str, timestamp: str = None):
        self.user_query = user_query
        self.ai_response = ai_response
        self.timestamp = timestamp or datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, str]:
        return {
            "user_query": self.user_query,
            "ai_response": self.ai_response,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'ConversationTurn':
        return cls(
            user_query=data["user_query"],
            ai_response=data["ai_response"],
            timestamp=data.get("timestamp")
        )
    
    def get_text_content(self) -> str:
        """Get the full text content of this turn for token counting."""
        return f"User: {self.user_query}\nAI: {self.ai_response}"
    
    def get_token_count(self) -> int:
        """Get approximate token count for this turn."""
        return count_tokens(self.get_text_content())


class ConversationSummary:
    """Represents a summary of older conversation turns."""
    
    def __init__(self, summary_text: str, turn_count: int, timestamp_range: str):
        self.summary_text = summary_text
        self.turn_count = turn_count  # Number of turns this summary represents
        self.timestamp_range = timestamp_range  # "2024-01-01 to 2024-01-02"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary_text": self.summary_text,
            "turn_count": self.turn_count,
            "timestamp_range": self.timestamp_range,
            "type": "summary"
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationSummary':
        return cls(
            summary_text=data["summary_text"],
            turn_count=data["turn_count"],
            timestamp_range=data["timestamp_range"]
        )
    
    def get_token_count(self) -> int:
        """Get token count for the summary."""
        return count_tokens(self.summary_text)


class SummaryBufferMemory:
    """Manages conversation history with summary buffer approach.
    
    Keeps recent k messages in raw form, summarizes older messages when
    approaching token limits.
    """
    
    def __init__(
        self, 
        max_recent_turns: int = 6,
        max_total_tokens: int = 2000,
        session_ttl: int = 86400,
        enable_summarization: bool = True
    ):
        self.max_recent_turns = max_recent_turns  # Keep last k turns in raw form
        self.max_total_tokens = max_total_tokens  # Token limit before summarization
        self.session_ttl = session_ttl
        self.enable_summarization = enable_summarization
    
    def _get_session_key(self, session_id: str) -> str:
        """Generate Redis key for session."""
        return f"chat_session_v2:{session_id}"
    
    def _get_summary_key(self, session_id: str) -> str:
        """Generate Redis key for session summary."""
        return f"chat_summary_v2:{session_id}"
    
    def get_history(self, session_id: str, limit: int = None) -> Tuple[Optional[ConversationSummary], List[ConversationTurn]]:
        """Get conversation history with summary and recent turns.
        
        Returns:
            (summary, recent_turns) where summary may be None if no summarization has occurred
        """
        if limit is None:
            limit = self.max_recent_turns * 2  # Allow retrieving more for context
        
        # Get summary if it exists
        summary_key = self._get_summary_key(session_id)
        summary_data = redis_client.get(summary_key)
        summary = None
        if summary_data:
            try:
                summary_dict = json.loads(summary_data)
                summary = ConversationSummary.from_dict(summary_dict)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"[CONVERSATION] Error parsing summary: {e}")
        
        # Get recent turns
        turns_key = self._get_session_key(session_id)
        history_data = redis_client.lrange(turns_key, -limit, -1)
        
        recent_turns = []
        for data in history_data:
            try:
                turn_dict = json.loads(data)
                recent_turns.append(ConversationTurn.from_dict(turn_dict))
            except (json.JSONDecodeError, KeyError) as e:
                print(f"[CONVERSATION] Error parsing turn: {e}")
                continue
        
        return summary, recent_turns
    
    def add_turn(self, session_id: str, user_query: str, ai_response: str) -> None:
        """Add a new conversation turn and manage summarization if needed."""
        turn = ConversationTurn(user_query, ai_response)
        turns_key = self._get_session_key(session_id)
        
        # Add new turn
        redis_client.rpush(turns_key, json.dumps(turn.to_dict()))
        redis_client.expire(turns_key, self.session_ttl)
        
        # Check if we need to summarize
        if self.enable_summarization:
            self._check_and_summarize(session_id)
    
    def _check_and_summarize(self, session_id: str) -> None:
        """Check if summarization is needed and perform it."""
        summary, recent_turns = self.get_history(session_id)
        
        # Calculate current token usage
        total_tokens = 0
        if summary:
            total_tokens += summary.get_token_count()
        
        for turn in recent_turns:
            total_tokens += turn.get_token_count()
        
        print(f"[CONVERSATION] Session {session_id}: {total_tokens} tokens, {len(recent_turns)} recent turns")
        
        # If we exceed token limit or have too many recent turns, summarize
        should_summarize = (
            total_tokens > self.max_total_tokens or
            len(recent_turns) > self.max_recent_turns
        )
        
        if should_summarize and len(recent_turns) > self.max_recent_turns:
            self._perform_summarization(session_id, summary, recent_turns)
    
    def _perform_summarization(
        self, 
        session_id: str, 
        existing_summary: Optional[ConversationSummary], 
        recent_turns: List[ConversationTurn]
    ) -> None:
        """Perform summarization of older turns."""
        # Determine how many turns to summarize (keep last max_recent_turns)
        turns_to_keep = self.max_recent_turns
        turns_to_summarize = recent_turns[:-turns_to_keep] if len(recent_turns) > turns_to_keep else []
        turns_to_keep_raw = recent_turns[-turns_to_keep:] if len(recent_turns) > turns_to_keep else recent_turns
        
        if not turns_to_summarize:
            return  # Nothing to summarize
        
        print(f"[CONVERSATION] Summarizing {len(turns_to_summarize)} turns, keeping {len(turns_to_keep_raw)} recent")
        
        # Create new summary
        new_summary_text = self._create_summary(turns_to_summarize, existing_summary)
        
        # Calculate timestamp range
        if turns_to_summarize:
            start_time = turns_to_summarize[0].timestamp
            end_time = turns_to_summarize[-1].timestamp
            timestamp_range = f"{start_time[:10]} to {end_time[:10]}"
        else:
            timestamp_range = "N/A"
        
        # Create summary object
        total_summarized_turns = len(turns_to_summarize)
        if existing_summary:
            total_summarized_turns += existing_summary.turn_count
        
        new_summary = ConversationSummary(
            summary_text=new_summary_text,
            turn_count=total_summarized_turns,
            timestamp_range=timestamp_range
        )
        
        # Store updated summary
        summary_key = self._get_summary_key(session_id)
        redis_client.set(summary_key, json.dumps(new_summary.to_dict()), ex=self.session_ttl)
        
        # Update recent turns (remove summarized turns)
        turns_key = self._get_session_key(session_id)
        redis_client.delete(turns_key)  # Clear old data
        
        # Re-add only the recent turns
        for turn in turns_to_keep_raw:
            redis_client.rpush(turns_key, json.dumps(turn.to_dict()))
        
        redis_client.expire(turns_key, self.session_ttl)
        
        print(f"[CONVERSATION] Created summary with {new_summary.get_token_count()} tokens")
    
    def _create_summary(
        self, 
        turns_to_summarize: List[ConversationTurn], 
        existing_summary: Optional[ConversationSummary]
    ) -> str:
        """Create a summary of conversation turns using LLM or rule-based approach."""
        
        # Try LLM-based summarization first
        if self._can_use_llm():
            try:
                return self._llm_summarize(turns_to_summarize, existing_summary)
            except Exception as e:
                print(f"[CONVERSATION] LLM summarization failed: {e}, falling back to rule-based")
        
        # Fallback to rule-based summarization
        return self._rule_based_summarize(turns_to_summarize, existing_summary)
    
    def _can_use_llm(self) -> bool:
        """Check if LLM is available for summarization."""
        try:
            # Check if Gemini is configured
            return bool(settings.gemini_api_key)
        except:
            return False
    
    def _llm_summarize(
        self, 
        turns_to_summarize: List[ConversationTurn], 
        existing_summary: Optional[ConversationSummary]
    ) -> str:
        """Use LLM to create conversation summary."""
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.gemini_api_key)
            model = genai.GenerativeModel(settings.gemini_model)
        except ImportError:
            raise Exception("Google Generative AI not available")
        
        # Prepare conversation text
        conversation_text = ""
        if existing_summary:
            conversation_text += f"Previous summary: {existing_summary.summary_text}\n\n"
        
        conversation_text += "Recent conversation:\n"
        for turn in turns_to_summarize:
            conversation_text += f"User: {turn.user_query}\n"
            conversation_text += f"AI: {turn.ai_response}\n\n"
        
        # Create summarization prompt
        prompt = f"""Please create a concise summary of this conversation that captures the key topics, questions asked, and important information discussed. Focus on:

1. Main topics and themes discussed
2. Key financial data or metrics mentioned
3. Important questions and their answers
4. Any follow-up patterns or user interests

Keep the summary under 200 words and maintain the essential context that would be useful for understanding future questions.

Conversation to summarize:
{conversation_text}

Summary:"""
        
        response = model.generate_content(prompt)
        summary_text = response.text.strip()
        
        print(f"[CONVERSATION] LLM generated summary: {len(summary_text)} chars")
        return summary_text
    
    def _rule_based_summarize(
        self, 
        turns_to_summarize: List[ConversationTurn], 
        existing_summary: Optional[ConversationSummary]
    ) -> str:
        """Create summary using rule-based approach."""
        summary_parts = []
        
        if existing_summary:
            summary_parts.append(f"Previous context: {existing_summary.summary_text}")
        
        # Extract key information
        topics = set()
        financial_terms = set()
        years = set()
        
        financial_keywords = [
            'revenue', 'income', 'profit', 'loss', 'earnings', 'dividend', 'share',
            'assets', 'liabilities', 'cash', 'debt', 'equity', 'margin', 'expenses'
        ]
        
        for turn in turns_to_summarize:
            # Extract topics from user queries
            query_words = turn.user_query.lower().split()
            for word in query_words:
                if len(word) > 3:  # Skip short words
                    topics.add(word)
                if word in financial_keywords:
                    financial_terms.add(word)
            
            # Extract years
            import re
            years.update(re.findall(r'\b(20\d{2})\b', turn.user_query + " " + turn.ai_response))
        
        # Build summary
        if financial_terms:
            summary_parts.append(f"Financial topics discussed: {', '.join(sorted(financial_terms))}")
        
        if years:
            summary_parts.append(f"Years referenced: {', '.join(sorted(years))}")
        
        if topics:
            # Filter out common words and keep relevant ones
            relevant_topics = [t for t in topics if len(t) > 4 and t not in ['what', 'where', 'when', 'which']][:5]
            if relevant_topics:
                summary_parts.append(f"Key topics: {', '.join(relevant_topics)}")
        
        summary_parts.append(f"Covered {len(turns_to_summarize)} conversation turns")
        
        return ". ".join(summary_parts) + "."
    
    def clear_session(self, session_id: str) -> None:
        """Clear all history and summary for a session."""
        turns_key = self._get_session_key(session_id)
        summary_key = self._get_summary_key(session_id)
        redis_client.delete(turns_key)
        redis_client.delete(summary_key)
    
    def get_context_for_query(self, session_id: str, limit: int = 3) -> str:
        """Get formatted context for query rewriting."""
        summary, recent_turns = self.get_history(session_id, limit)
        
        context_parts = []
        
        if summary:
            context_parts.append(f"Previous conversation summary: {summary.summary_text}")
        
        if recent_turns:
            context_parts.append("Recent conversation:")
            for turn in recent_turns[-limit:]:  # Last few turns
                context_parts.append(f"User: {turn.user_query}")
                context_parts.append(f"AI: {turn.ai_response[:100]}...")  # Truncate for brevity
        
        return "\n".join(context_parts)


class ConversationManager:
    """Enhanced conversation manager with summary buffer memory."""
    
    def __init__(
        self, 
        max_recent_turns: int = 6,
        max_total_tokens: int = 2000,
        session_ttl: int = 86400,
        enable_summarization: bool = True
    ):
        self.memory = SummaryBufferMemory(
            max_recent_turns=max_recent_turns,
            max_total_tokens=max_total_tokens,
            session_ttl=session_ttl,
            enable_summarization=enable_summarization
        )
    
    def get_history(self, session_id: str, limit: int = None) -> List[ConversationTurn]:
        """Get conversation history (for backwards compatibility)."""
        summary, recent_turns = self.memory.get_history(session_id, limit)
        return recent_turns
    
    def get_full_context(self, session_id: str) -> Tuple[Optional[ConversationSummary], List[ConversationTurn]]:
        """Get full context including summary and recent turns."""
        return self.memory.get_history(session_id)
    
    def add_turn(self, session_id: str, user_query: str, ai_response: str) -> None:
        """Add a new conversation turn."""
        self.memory.add_turn(session_id, user_query, ai_response)
    
    def clear_session(self, session_id: str) -> None:
        """Clear all history for a session."""
        self.memory.clear_session(session_id)
    
    def is_followup_query(self, query: str) -> bool:
        """Detect if a query is likely a follow-up that needs context."""
        query_lower = query.lower().strip()
        
        # Simple heuristics for follow-up detection
        followup_patterns = [
            r'^(and|also|what about|how about)\s',
            r'^(for|in|about)\s+\d{4}',  # "for 2022", "in 2023"
            r'^\d{4}\s*\?*$',  # Just a year like "2022?"
            r'^(the\s+)?(previous|next|last|this)\s+(year|quarter|period)',
            r'^(what|how)\s+(about|was)\s+(that|it|this)',
            r'^\w+\s*\?*$',  # Single word queries like "revenue?"
        ]
        
        for pattern in followup_patterns:
            if re.match(pattern, query_lower):
                return True
        
        # Check if query is very short (likely incomplete)
        if len(query.split()) <= 3 and '?' in query:
            return True
        
        return False
    
    def rewrite_query_with_context(self, current_query: str, history: List[ConversationTurn]) -> str:
        """Rewrite a follow-up query using conversation context with improved edge case handling."""
        if not history or not self.is_followup_query(current_query):
            return current_query
        
        # Get the last few turns for better context
        last_turn = history[-1]
        last_query = last_turn.user_query
        last_response = last_turn.ai_response
        
        current_lower = current_query.lower().strip()
        
        # Enhanced pattern-based rewriting rules
        
        # Case 1: Year-based queries with improved accuracy
        year_match = re.search(r'(?:and\s+|for\s+|in\s+|about\s+)?(\d{4})', current_lower)
        if year_match:
            new_year = year_match.group(1)
            
            # Extract the main topic from the last query and response
            main_topic = self._extract_main_topic(last_query, last_response)
            
            if main_topic:
                # Create a more specific query combining topic and year
                return f"What was the {main_topic} in {new_year}?"
            else:
                # Fallback: replace year in previous query
                prev_year_match = re.search(r'\d{4}', last_query)
                if prev_year_match:
                    rewritten = last_query.replace(prev_year_match.group(), new_year)
                    return rewritten
                else:
                    # No year in previous query, append year context
                    return f"{last_query} for {new_year}"
        
        # Case 2: "compare it with X" or "vs X" patterns
        comparison_patterns = [
            r'compare\s+(?:it|that|this)\s+(?:with|to|against)\s+(.+?)[\?]*$',
            r'(?:vs|versus)\s+(.+?)[\?]*$',
            r'and\s+(.+?)[\?]*$'
        ]
        
        for pattern in comparison_patterns:
            match = re.search(pattern, current_lower)
            if match:
                comparison_target = match.group(1).strip()
                main_topic = self._extract_main_topic(last_query, last_response)
                
                if main_topic and comparison_target:
                    # Check if comparison target is a year
                    if re.match(r'\d{4}', comparison_target):
                        return f"Compare the {main_topic} between the previous year mentioned and {comparison_target}"
                    else:
                        return f"Compare the {main_topic} with {comparison_target}"
                else:
                    return f"{last_query} compared to {comparison_target}"
        
        # Case 3: Direct year queries "2022?" with context preservation
        if re.match(r'^\d{4}\s*\?*$', current_lower):
            year = re.match(r'^(\d{4})', current_lower).group(1)
            main_topic = self._extract_main_topic(last_query, last_response)
            
            if main_topic:
                return f"What was the {main_topic} in {year}?"
            else:
                # Replace year in last query
                prev_year_match = re.search(r'\d{4}', last_query)
                if prev_year_match:
                    return last_query.replace(prev_year_match.group(), year)
                else:
                    return f"{last_query} in {year}"
        
        # Case 4: Topic-based follow-ups with better context
        topic_patterns = [
            r'(?:what about|how about)\s+(.+?)[\?]*$',
            r'^(.+?)\s*\?*$'  # fallback for single terms
        ]
        
        for pattern in topic_patterns:
            match = re.search(pattern, current_lower)
            if match:
                new_topic = match.group(1).strip()
                # Avoid very short or common terms
                if len(new_topic) > 2 and new_topic not in ['it', 'that', 'this', 'then', 'what']:
                    # Extract year from last query if present
                    last_year_match = re.search(r'\d{4}', last_query)
                    if last_year_match:
                        year = last_year_match.group()
                        return f"What was the {new_topic} in {year}?"
                    else:
                        return f"What was the {new_topic}?"
        
        # Fallback: enhanced combination
        return f"{last_query.rstrip('?')} and {current_query}"
    
    def _extract_main_topic(self, query: str, response: str) -> str:
        """Extract the main financial topic from query and response."""
        # Financial metrics keywords in order of priority
        financial_keywords = [
            'net income', 'total revenue', 'revenue', 'income', 'profit', 'loss', 
            'earnings', 'margin', 'assets', 'liabilities', 'cash flow', 'dividend',
            'share price', 'eps', 'ebitda', 'operating income', 'gross profit'
        ]
        
        text_to_search = (query + " " + response).lower()
        
        # Look for financial keywords in order of priority
        for keyword in financial_keywords:
            if keyword in text_to_search:
                return keyword
        
        # Fallback: extract noun phrases (simplified)
        # Look for patterns like "the X" or "X was"
        noun_patterns = [
            r'(?:the|what)\s+([a-zA-Z\s]+?)(?:\s+(?:was|is|in|for))',
            r'([a-zA-Z\s]+?)\s+(?:was|is)\s+\$'
        ]
        
        for pattern in noun_patterns:
            match = re.search(pattern, query.lower())
            if match:
                topic = match.group(1).strip()
                if len(topic) > 2 and topic not in ['what', 'the', 'it']:
                    return topic
        
        return ""


# Global conversation manager instance with summary buffer memory
conversation_manager = ConversationManager(
    max_recent_turns=6,      # Keep last 6 turns in raw form
    max_total_tokens=2000,   # Summarize when approaching 2000 tokens
    enable_summarization=True
)


def get_conversation_manager() -> ConversationManager:
    """Get the global conversation manager instance."""
    return conversation_manager 