# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Retrieval-Augmented Generation (RAG) system for querying course materials using semantic search and AI-powered responses. The architecture uses FastAPI, ChromaDB for vector storage, and Anthropic's Claude for AI generation with function calling.

## Development Commands

```bash
# Install dependencies
uv sync

# Run the application (recommended)
chmod +x run.sh && ./run.sh

# Manual start
cd backend && uv run uvicorn app:app --reload --port 8000

# Access points
# Web UI: http://localhost:8000
# API docs: http://localhost:8000/docs
```

**Note**: This codebase has no test suite configured.

## Architecture

The system follows a layered architecture orchestrated by `rag_system.py`:

- **`app.py`** - FastAPI application with `/api/query` and `/api/courses` endpoints. Auto-loads documents from `../docs` on startup.
- **`rag_system.py`** - Central coordinator integrating all components.
- **`document_processor.py`** - Parses structured course documents (Course/Lesson metadata + content) and performs sentence-based chunking with overlap.
- **`vector_store.py`** - ChromaDB wrapper with dual collections: `course_catalog` (metadata) and `course_content` (text chunks).
- **`ai_generator.py`** - Claude integration with tool-calling loop for search.
- **`search_tools.py`** - Extensible tool system with `CourseSearchTool` for filtered semantic search.
- **`session_manager.py`** - In-memory conversation state with configurable history limit.
- **`models.py`** - Pydantic models: `Course`, `Lesson`, `CourseChunk`.

## Key Patterns

1. **Tool-based AI search**: Claude doesn't access the vector store directly; it uses function calling to invoke `CourseSearchTool` with filters (course_name, lesson_number).
2. **Document format**: Structured text files with headers (`Course Title:`, `Course Link:`, `Course Instructor:`, `Lesson N:`, `Lesson Link:`).
3. **Dual collection vector store**: Semantic course name resolution via `course_catalog`, content search via `course_content`.
4. **Configuration**: Centralized in `config.py` dataclass (chunk size: 800, overlap: 100, max results: 5, history: 2 exchanges).
5. **Session management**: Client-side session IDs, server creates new if not provided.

## Configuration

Key settings in `backend/config.py`:
- `ANTHROPIC_MODEL`: claude-sonnet-4-20250514
- `EMBEDDING_MODEL`: all-MiniLM-L6-v2
- `CHUNK_SIZE`: 800 characters
- `CHUNK_OVERLAP`: 100 characters
- `CHROMA_PATH`: `./chroma_db` (persisted locally)
- `MAX_HISTORY`: 2 conversation exchanges

## Adding New Course Materials

Place text files in the `docs/` directory following the structured format. The application auto-loads all files on startup.
