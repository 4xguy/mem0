# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

mem0 is an intelligent memory layer for AI agents that provides persistent, personalized memory capabilities. It's a Python-based system with TypeScript SDK support that enables AI systems to remember and learn from interactions.

## Essential Commands

### Development Setup
```bash
# Install core dependencies
make install

# Install all optional dependencies (for all providers)
make install_all
```

### Development Workflow
```bash
# Format code (required before commit)
make format

# Run linter
make lint

# Run all tests
make test

# Run tests for specific Python version
make test-py-3.9
make test-py-3.10
make test-py-3.11

# Run documentation locally
make docs

# Run a single test
pytest tests/test_memory.py::test_specific_function -v
```

## Architecture Overview

### Core Components

1. **mem0/memory/main.py** - Core Memory class implementing the main memory operations (add, search, update, delete). This is the primary interface for self-hosted usage.

2. **mem0/client/main.py** - MemoryClient for interacting with the hosted mem0 platform. Uses API key authentication and provides additional features like batch operations.

3. **Provider System** - Modular architecture supporting multiple providers:
   - LLM providers in `mem0/llms/` (19+ providers)
   - Embedding providers in `mem0/embeddings/` (10+ providers)
   - Vector store providers in `mem0/vector_stores/` (17+ providers)
   - Graph store providers in `mem0/graphs/` (3 providers)

4. **Configuration System** (`mem0/configs/`) - Pydantic-based configuration that allows flexible provider selection and custom prompt configuration.

### Key Design Patterns

- **Factory Pattern**: Used extensively for provider instantiation (see `mem0/llms/configs.py`, `mem0/embeddings/configs.py`)
- **Async Support**: Most operations have async variants (e.g., `Memory` and `AsyncMemory`)
- **Provider Abstraction**: All providers implement consistent interfaces defined in base classes
- **Configuration Validation**: Pydantic models ensure configuration correctness

### Memory Operations Flow

1. **Add Memory**: Text → LLM extraction → Embedding → Vector/Graph storage
2. **Search**: Query → Embedding → Vector similarity search → Reranking
3. **Update**: Fetch existing → Modify → Re-embed → Update storage
4. **Graph Operations**: Entity extraction → Relationship mapping → Graph storage

## Testing Strategy

- Use pytest for all tests
- Provider tests are in `tests/embeddings/`, `tests/llms/`, `tests/vector_stores/`, etc.
- Mock external API calls when testing provider integrations
- Test both sync and async versions of operations

## Important Implementation Notes

1. **Provider Dependencies**: Each provider has optional dependencies. Only import them within the provider class to avoid import errors.

2. **Error Handling**: Provider initialization errors should be caught and provide helpful messages about missing dependencies.

3. **Configuration Flexibility**: The system supports both environment variables and explicit configuration for API keys and settings.

4. **Memory Deduplication**: The system includes built-in deduplication logic to prevent storing duplicate memories.

5. **Custom Prompts**: Users can provide custom prompts for memory extraction via the configuration system.

## Multi-Component Architecture

- **mem0/** - Core Python library
- **mem0-ts/** - TypeScript SDK (separate build process)
- **server/** - FastAPI REST server
- **openmemory/** - Web UI and API
- **docs/** - Mintlify documentation

Each component has its own dependencies and build process. When making changes that affect multiple components, ensure compatibility across all affected parts.

## Personal Memory Usage
- Run `mem0ctl search --user keith --query "<topic>" -n 3 --summary` at the start of a task; fold only the summary or top two results into your prompt.
- Write new, durable facts with `mem0ctl add --user keith --text "<concise fact>"` once you’ve confirmed them; use `mem0ctl update <id> --user keith --text "<updated fact>"` when adjusting existing entries.
- Only log information that will stay useful to Keith (preferences, workflows, ongoing projects, decisions). Do **not** store ephemeral conversation, speculative notes, secrets, or tokens.
- Use `mem0ctl delete <id>` or `reset --user keith` solely when Keith explicitly requests removal/cleanup.
- If you are uncertain whether to store something, ask first or skip.
