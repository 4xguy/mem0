# Token Reduction Techniques in mem0: Achieving 90% Lower Token Usage

## Overview

mem0 achieves a remarkable 90% reduction in token usage compared to traditional full-context approaches through intelligent fact extraction, selective memory retrieval, and efficient formatting. This document explains the specific techniques and implementations.

## Core Token Reduction Strategies

### 1. Fact Extraction and Compression

Instead of storing entire conversations, mem0 extracts only essential facts:

```python
# From mem0/configs/prompts.py
FACT_RETRIEVAL_PROMPT = """
Extract factual information about the person from the message. Include:
- Personal information
- Preferences
- Plans, goals, or intentions
- Important context

Rules:
- Extract only distinct facts
- Use concise phrasing
- Preserve important details
- Output as JSON list

Examples:
Input: "Hi, I am looking for a restaurant in San Francisco"
Output: ["Looking for a restaurant in San Francisco"]

Input: "Yesterday, I had a meeting with John at 3pm to discuss the project"
Output: ["Had a meeting with John", "Meeting was at 3pm", "Meeting was about the project"]
"""
```

#### Compression Examples
```python
# Before (full conversation)
conversation = """
User: Hi! My name is Sarah and I'm a software engineer working at Google. 
I've been coding for about 10 years, mostly in Python and Java. 
I'm currently working on machine learning projects and I love hiking on weekends.
"""
# Token count: ~45 tokens

# After (extracted facts)
extracted_facts = [
    "Name is Sarah",
    "Is a software engineer",
    "Works at Google", 
    "Has 10 years coding experience",
    "Codes in Python and Java",
    "Works on ML projects",
    "Enjoys hiking"
]
# Token count: ~20 tokens (55% reduction just in storage)
```

### 2. Selective Memory Retrieval

Only the most relevant memories are retrieved:

```python
# From mem0/memory/main.py
def search(self, query, user_id=None, limit=10, threshold=None):
    """
    Search memories with strict limits.
    
    Args:
        query: Search query
        limit: Maximum memories to retrieve (default: 10)
        threshold: Minimum relevance score
    """
    # Embed query once
    query_embedding = self.embedding_model.embed(query)
    
    # Vector search with limit
    results = self.vector_store.search(
        query_embedding=query_embedding,
        limit=limit,  # Prevents retrieving entire memory store
        filters={"user_id": user_id}
    )
    
    # Further filtering by threshold
    if threshold:
        results = [r for r in results if r["score"] >= threshold]
    
    return results
```

### 3. Efficient Context Window Management

```python
# From mem0/proxy/main.py
async def _fetch_relevant_memories(self, messages, user_id):
    """Fetch memories using only recent context."""
    
    # Use only last 6 messages for context
    messages_to_add = (
        messages[-6:] if len(messages) >= 6 
        else messages
    )
    
    # Format for memory search (minimal tokens)
    system_prompt_with_memories = f"Current session messages: {messages_to_add}"
    
    # Search with limited context
    result = await self.memory.search(
        messages=messages_to_add,
        user_id=user_id,
        limit=self.config.search_msg_limit  # Default: 10
    )
    
    return result
```

### 4. Minimal Memory Formatting

```python
def format_memories_for_context(memories):
    """Format memories using minimal tokens."""
    
    # Concise format: just the facts
    memories_text = "\n".join(
        memory["memory"] for memory in memories["results"]
    )
    
    # Minimal prompt template
    return f"""
Relevant context:
{memories_text}

User query: {user_query}
"""
    # Total: ~100-200 tokens vs 1000+ for full conversation
```

## Token Usage Comparison

### Traditional Full-Context Approach

```python
def traditional_chat(conversation_history):
    """Send entire conversation history."""
    
    # Example conversation (10 turns)
    full_context = """
    User: Hi, I'm John
    Assistant: Hello John! How can I help you?
    User: I'm working on a Python project
    Assistant: Great! What kind of Python project?
    User: It's a web scraper using BeautifulSoup
    Assistant: BeautifulSoup is excellent for web scraping...
    ... (6 more turns)
    """
    
    # Token calculation
    # 10 turns × 100 tokens/turn = 1,000 tokens
    # Plus new query: 50 tokens
    # Total: 1,050 tokens per request
    
    response = llm.complete(full_context + new_message)
    return response
```

### mem0 Approach

```python
def mem0_chat(query, user_id):
    """Use extracted memories instead of full history."""
    
    # Retrieve relevant memories
    memories = memory.search(query, user_id, limit=10)
    
    # Example retrieved memories
    context = """
    Relevant facts:
    - Name is John
    - Working on Python project
    - Using BeautifulSoup for web scraping
    - Interested in data extraction
    - Has intermediate Python skills
    """
    
    # Token calculation
    # 10 memories × 10 tokens/memory = 100 tokens
    # Plus new query: 50 tokens
    # Total: 150 tokens per request (85% reduction)
    
    response = llm.complete(context + query)
    return response
```

## Advanced Token Optimization Techniques

### 1. Memory Deduplication

Prevents storing redundant information:

```python
def deduplicate_memories(self, new_facts, existing_memories):
    """Remove duplicate facts to minimize storage."""
    
    # Create embedding map for comparison
    existing_embeddings = {
        mem["memory"]: mem["embedding"] 
        for mem in existing_memories
    }
    
    unique_facts = []
    for fact in new_facts:
        # Check semantic similarity
        is_duplicate = False
        fact_embedding = self.embed(fact)
        
        for existing_text, existing_emb in existing_embeddings.items():
            similarity = cosine_similarity(fact_embedding, existing_emb)
            if similarity > 0.95:  # High similarity threshold
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique_facts.append(fact)
    
    return unique_facts
```

### 2. Smart Update Strategy

Updates existing memories instead of creating new ones:

```python
# From DEFAULT_UPDATE_MEMORY_PROMPT
update_rules = """
- If a memory conveys the same information, USE EVENT: UPDATE
- Only ADD when information is completely new
- DELETE when information is contradictory
- NONE when no action needed

This prevents memory bloat and keeps token usage minimal.
"""
```

### 3. Prompt Optimization

```python
# Optimized prompts use minimal tokens
OPTIMIZED_FACT_PROMPT = """
Extract facts as brief phrases.
Output JSON list only.
"""
# 10 tokens vs 50+ for verbose prompt

# Memory retrieval prompt
SEARCH_PROMPT = "Find: {query}"  # 3-5 tokens
```

### 4. Batch Processing

```python
def batch_embed_texts(self, texts):
    """Embed multiple texts in one API call."""
    
    # Single API call for all texts
    embeddings = self.embedding_model.embed_batch(texts)
    
    # Saves tokens on API overhead
    return embeddings
```

## Real-World Token Savings Example

### Customer Support Scenario

```python
# Traditional approach - Full conversation
traditional_context = {
    "conversation_length": 50,  # 50 exchanges
    "avg_tokens_per_exchange": 100,
    "total_context_tokens": 5000,
    "new_query_tokens": 50,
    "total_request": 5050  # Tokens sent to LLM
}

# mem0 approach - Extracted memories
mem0_context = {
    "stored_facts": 30,  # 30 key facts extracted
    "avg_tokens_per_fact": 8,
    "retrieved_memories": 10,  # Only 10 relevant
    "memory_tokens": 80,  # 10 × 8
    "new_query_tokens": 50,
    "total_request": 130  # Tokens sent to LLM
}

# Savings: (5050 - 130) / 5050 = 97.4% reduction!
```

## Configuration for Token Optimization

```python
config = {
    "memory": {
        "fact_extraction": {
            "min_fact_length": 3,  # Skip very short facts
            "max_fact_length": 20,  # Limit fact size
            "dedup_threshold": 0.95  # Aggressive deduplication
        },
        "search": {
            "default_limit": 10,  # Limit retrieved memories
            "relevance_threshold": 0.7,  # Only high-relevance
            "max_context_messages": 6  # Recent context only
        }
    },
    "llm": {
        "prompts": {
            "use_compressed": True,  # Use token-optimized prompts
            "fact_extraction_style": "minimal"
        }
    }
}
```

## Token Tracking and Monitoring

```python
class TokenTracker:
    """Track token usage for optimization."""
    
    def __init__(self):
        self.usage = {
            "fact_extraction": 0,
            "memory_search": 0,
            "memory_update": 0,
            "total_saved": 0
        }
    
    def track_extraction(self, original_text, extracted_facts):
        original_tokens = self.count_tokens(original_text)
        fact_tokens = sum(self.count_tokens(f) for f in extracted_facts)
        
        self.usage["fact_extraction"] += fact_tokens
        self.usage["total_saved"] += (original_tokens - fact_tokens)
        
        return {
            "compression_ratio": fact_tokens / original_tokens,
            "tokens_saved": original_tokens - fact_tokens
        }
```

## Best Practices for Token Reduction

1. **Aggressive Fact Extraction**
   - Extract only actionable information
   - Use shortest possible phrasing
   - Avoid redundant context

2. **Smart Retrieval Limits**
   - Start with lower limits (5-10 memories)
   - Increase only if needed
   - Use relevance thresholds

3. **Efficient Formatting**
   - Minimal prompt templates
   - No unnecessary formatting
   - Direct fact presentation

4. **Regular Cleanup**
   - Remove outdated memories
   - Merge similar facts
   - Maintain lean memory store

## Conclusion

mem0's 90% token reduction is achieved through:

1. **Intelligent Compression**: Full conversations → Essential facts
2. **Selective Retrieval**: All context → Only relevant memories  
3. **Efficient Formatting**: Verbose prompts → Minimal templates
4. **Smart Updates**: Deduplication and merging
5. **Optimized Operations**: Batch processing and caching

This dramatic reduction in token usage translates directly to:
- Lower API costs
- Faster response times
- Ability to handle longer conversations
- Better scalability for production systems