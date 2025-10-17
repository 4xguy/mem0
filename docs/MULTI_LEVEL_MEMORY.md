# Multi-Level Memory in mem0

## Overview

mem0 implements a sophisticated multi-level memory architecture that enables AI systems to maintain context at three distinct levels: User, Session (Run), and Agent. This allows for fine-grained memory management with adaptive personalization.

## Architecture

### Core Levels

1. **User Level** (`user_id`)
   - Persistent memories specific to a user
   - Survives across all sessions and agents
   - Examples: preferences, personal information, long-term goals

2. **Agent Level** (`agent_id`)
   - Memories specific to an AI agent
   - Allows different agents to maintain their own perspective
   - Examples: agent-specific interactions, specialized knowledge

3. **Session/Run Level** (`run_id`)
   - Temporary memories for a specific session
   - Isolated from long-term storage
   - Examples: current task context, temporary decisions

### Implementation Details

The multi-level architecture is implemented through the `_build_filters_and_metadata` function:

```python
def _build_filters_and_metadata(
    *,
    user_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    run_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    input_metadata: Optional[Dict[str, Any]] = None,
    input_filters: Optional[Dict[str, Any]] = None,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Build metadata and filters for memory operations.
    
    Returns:
        - base_metadata_template: For storing memories with level identifiers
        - effective_query_filters: For retrieving memories at specific levels
    """
```

## Code Examples

### Basic Usage

```python
from mem0 import Memory

# Initialize memory
memory = Memory()

# Add user-level memory
memory.add(
    "I prefer dark mode and use VS Code",
    user_id="user_123"
)

# Add agent-specific memory about the user
memory.add(
    "User asked me to be more concise in responses",
    user_id="user_123",
    agent_id="assistant_v1"
)

# Add session-specific memory
memory.add(
    "Currently working on the authentication module",
    user_id="user_123",
    run_id="session_456"
)
```

### Retrieving Memories at Different Levels

```python
# Get all memories for a user (across all agents and sessions)
user_memories = memory.get_all(user_id="user_123")

# Get memories specific to an agent's interaction with a user
agent_memories = memory.get_all(
    user_id="user_123",
    agent_id="assistant_v1"
)

# Get memories from current session only
session_memories = memory.get_all(
    user_id="user_123",
    run_id="session_456"
)

# Search with multi-level context
relevant_memories = memory.search(
    query="coding preferences",
    user_id="user_123",
    agent_id="assistant_v1"
)
```

### Advanced Multi-Agent Example

```python
# From examples/misc/multillm_memory.py
from mem0 import Memory

memory = Memory()
project_id = "data_analysis_project"

# Research specialist stores findings
memory.add(
    "SQL query optimization: Use indexing on timestamp columns for 10x speedup",
    user_id=project_id,  # Project-level memory
    agent_id="sql_specialist",
    metadata={
        "contributor": "sql_specialist",
        "task_type": "research",
        "model_used": "gpt-4"
    }
)

# Data analyst accesses shared knowledge
project_memories = memory.search(
    query="optimization techniques",
    user_id=project_id  # Access all project memories
)

# Create team summary combining all agents' contributions
all_research = memory.get_all(user_id=project_id)
team_knowledge = {
    mem['agent_id']: mem['memory'] 
    for mem in all_research['memories']
}
```

### Actor-Level Granularity

Beyond the three main levels, mem0 supports actor-level tracking for multi-participant scenarios:

```python
# Track different actors in a conversation
memory.add(
    messages=[
        {"role": "user", "content": "I need help with Python"},
        {"role": "assistant", "content": "I'll help you with Python"}
    ],
    user_id="user_123",
    run_id="session_789",
    metadata={
        "actor_id": "participant_1",  # Track specific actor
        "conversation_type": "support"
    }
)

# Query memories from specific actor
actor_memories = memory.search(
    query="Python help",
    user_id="user_123",
    filters={"actor_id": "participant_1"}
)
```

## Memory Scoping Patterns

### 1. User-Only Scope
```python
# Global user preferences
memory.add("Prefers metric units", user_id="user_123")
```

### 2. User + Agent Scope
```python
# Agent-specific user knowledge
memory.add(
    "Has intermediate Python skills",
    user_id="user_123",
    agent_id="code_tutor"
)
```

### 3. User + Session Scope
```python
# Session-specific but agent-agnostic
memory.add(
    "Working on e-commerce checkout flow",
    user_id="user_123",
    run_id="session_999"
)
```

### 4. Full Context Scope
```python
# Fully contextualized memory
memory.add(
    "Struggling with payment gateway integration",
    user_id="user_123",
    agent_id="code_assistant",
    run_id="session_999"
)
```

## Best Practices

1. **Use Appropriate Levels**
   - User level: Persistent facts, preferences
   - Agent level: Agent-specific interactions
   - Session level: Temporary context

2. **Avoid Over-Scoping**
   - Don't use session_id for information that should persist
   - Don't use user_id only for agent-specific knowledge

3. **Leverage Metadata**
   ```python
   memory.add(
       "Completed Python tutorial",
       user_id="user_123",
       metadata={
           "skill_level": "beginner",
           "completion_date": "2024-01-15",
           "course": "python_basics"
       }
   )
   ```

4. **Multi-Agent Coordination**
   - Use consistent project/team IDs as user_id for shared memory
   - Tag memories with agent_id for attribution
   - Include metadata for richer context

## Memory Types Support

mem0 supports three memory types that work across all levels:

```python
from mem0.configs.enums import MemoryType

# Semantic memory (facts)
memory.add(
    "User is a software engineer",
    user_id="user_123",
    memory_type=MemoryType.SEMANTIC
)

# Episodic memory (events)
memory.add(
    "User attended Python conference last week",
    user_id="user_123",
    memory_type=MemoryType.EPISODIC
)

# Procedural memory (how-to)
memory.add(
    "To debug, user prefers using pdb over print statements",
    user_id="user_123",
    memory_type=MemoryType.PROCEDURAL
)
```

## Conclusion

The multi-level memory architecture in mem0 provides a flexible and powerful system for maintaining context across different scopes. By properly utilizing user, agent, and session levels, along with rich metadata, you can build AI systems that truly understand and adapt to users over time.