"""Shared fixtures and test configuration for RAG system tests."""

import os
import tempfile
from pathlib import Path
from typing import Generator, AsyncGenerator
from unittest.mock import Mock, MagicMock, AsyncMock
import pytest

from fastapi.testclient import TestClient


# ============================================================================
# Mock Fixtures for Core Components
# ============================================================================

@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    from config import Config
    return Config(
        ANTHROPIC_API_KEY="test-api-key",
        ANTHROPIC_MODEL="claude-sonnet-4-20250514",
        EMBEDDING_MODEL="all-MiniLM-L6-v2",
        CHUNK_SIZE=800,
        CHUNK_OVERLAP=100,
        MAX_RESULTS=5,
        MAX_HISTORY=2,
        CHROMA_PATH=":memory:",  # Use in-memory database for tests
    )


@pytest.fixture
def mock_vector_store():
    """Create a mock vector store."""
    store = Mock()
    store.add_course_metadata = Mock()
    store.add_course_content = Mock()
    store.search = Mock(return_value=[])
    store.get_course_count = Mock(return_value=0)
    store.get_existing_course_titles = Mock(return_value=[])
    store.clear_all_data = Mock()
    return store


@pytest.fixture
def mock_ai_generator():
    """Create a mock AI generator."""
    generator = Mock()
    generator.generate_response = Mock(return_value="Test AI response")
    return generator


@pytest.fixture
def mock_session_manager():
    """Create a mock session manager."""
    manager = Mock()
    manager.create_session = Mock(return_value="test-session-123")
    manager.get_conversation_history = Mock(return_value=None)
    manager.add_exchange = Mock()
    return manager


@pytest.fixture
def mock_document_processor():
    """Create a mock document processor."""
    processor = Mock()
    from models import Course, Lesson, CourseChunk

    # Create mock course and chunks
    mock_course = Course(
        title="Test Course",
        course_link="https://example.com/course",
        instructor="Test Instructor",
        lessons=[
            Lesson(lesson_number=1, title="Introduction", lesson_link="https://example.com/lesson1"),
            Lesson(lesson_number=2, title="Advanced Topics", lesson_link="https://example.com/lesson2"),
        ]
    )

    mock_chunks = [
        CourseChunk(
            content="This is the first chunk of test content.",
            course_title="Test Course",
            lesson_number=1,
            chunk_index=0
        ),
        CourseChunk(
            content="This is the second chunk with more detailed information.",
            course_title="Test Course",
            lesson_number=1,
            chunk_index=1
        ),
    ]

    processor.process_course_document = Mock(return_value=(mock_course, mock_chunks))
    return processor


# ============================================================================
# Test Fixtures for RAG System
# ============================================================================

@pytest.fixture
def rag_system(
    mock_config,
    mock_vector_store,
    mock_ai_generator,
    mock_session_manager,
    mock_document_processor
):
    """Create a RAG system with mocked components."""
    from rag_system import RAGSystem

    system = RAGSystem.__new__(RAGSystem)
    system.config = mock_config
    system.document_processor = mock_document_processor
    system.vector_store = mock_vector_store
    system.ai_generator = mock_ai_generator
    system.session_manager = mock_session_manager

    # Mock tool manager
    from search_tools import ToolManager
    system.tool_manager = ToolManager()
    system.tool_manager.get_tool_definitions = Mock(return_value=[])
    system.tool_manager.get_last_sources = Mock(return_value=[])
    system.tool_manager.reset_sources = Mock()

    return system


# ============================================================================
# Test Fixtures for API Testing
# ============================================================================

@pytest.fixture
def test_app():
    """
    Create a test FastAPI app without static file mounting.
    This avoids import issues with missing static files in test environment.
    """
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.middleware.trustedhost import TrustedHostMiddleware
    from pydantic import BaseModel
    from typing import List, Optional, Dict, Any

    app = FastAPI(title="Test Course Materials RAG System")

    # Add middleware
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    # Pydantic models
    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[Dict[str, Any]]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    # Store for mock responses
    app.state.mock_query_response = QueryResponse(
        answer="Test answer",
        sources=[{"course": "Test Course", "lesson": 1, "content": "Test content"}],
        session_id="test-session-123"
    )
    app.state.mock_course_stats = CourseStats(
        total_courses=2,
        course_titles=["Course 1", "Course 2"]
    )
    app.state.query_should_fail = False
    app.state.courses_should_fail = False

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        if app.state.query_should_fail:
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail="Test error")
        return app.state.mock_query_response

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        if app.state.courses_should_fail:
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail="Test error")
        return app.state.mock_course_stats

    return app


@pytest.fixture
def client(test_app) -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(test_app)


@pytest.fixture
def async_client(test_app) -> AsyncGenerator:
    """Create an async test client for the FastAPI app."""
    from httpx import AsyncClient, ASGITransport

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test"
    ) as ac:
        yield ac


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_course_text():
    """Sample course document text for testing."""
    return """Course Title: Advanced Python Programming
Course Link: https://example.com/python-advanced
Course Instructor: Dr. Jane Smith

Lesson 1: Introduction to Async Programming
Lesson Link: https://example.com/python-async

Async programming in Python allows for concurrent code execution using
the asyncio library. This lesson covers the basics of async/await syntax,
event loops, and how to write non-blocking code.

Lesson 2: Decorators and Context Managers
Lesson Link: https://example.com/python-decorators

Python decorators provide a way to modify functions and methods. Context
managers allow for proper resource management using the 'with' statement.
This lesson explores both concepts in depth.
"""


@pytest.fixture
def sample_course_file(sample_course_text, tmp_path) -> Path:
    """Create a temporary sample course file."""
    course_file = tmp_path / "sample_course.txt"
    course_file.write_text(sample_course_text)
    return course_file


@pytest.fixture
def sample_courses_dir(sample_course_text, tmp_path) -> Path:
    """Create a temporary directory with multiple course files."""
    courses_dir = tmp_path / "courses"
    courses_dir.mkdir()

    # Create multiple course files
    courses = [
        ("python_basics.txt", "Course Title: Python Basics\nCourse Instructor: John Doe\n\nLesson 1: Hello World\nThis is basic Python content."),
        ("advanced_python.txt", "Course Title: Advanced Python\nCourse Instructor: Jane Smith\n\nLesson 1: Metaclasses\nThis is advanced Python content."),
        ("data_science.txt", "Course Title: Data Science 101\nCourse Instructor: Bob Johnson\n\nLesson 1: NumPy Basics\nThis is data science content."),
    ]

    for filename, content in courses:
        (courses_dir / filename).write_text(content)

    return courses_dir


# ============================================================================
# Mock API Response Fixtures
# ============================================================================

@pytest.fixture
def mock_anthropic_response():
    """Mock response from Anthropic API."""
    return {
        "id": "msg-123",
        "type": "message",
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "Here's information about async programming in Python..."
            }
        ],
        "model": "claude-sonnet-4-20250514",
        "stop_reason": "end_turn",
    }


@pytest.fixture
def mock_search_results():
    """Mock search results from vector store."""
    return [
        {
            "content": "Async programming in Python allows for concurrent code execution",
            "course_title": "Advanced Python Programming",
            "lesson_number": 1,
            "chunk_index": 0,
            "distance": 0.123
        },
        {
            "content": "The asyncio library provides tools for async programming",
            "course_title": "Advanced Python Programming",
            "lesson_number": 1,
            "chunk_index": 1,
            "distance": 0.234
        },
    ]


# ============================================================================
# Directory and Path Fixtures
# ============================================================================

@pytest.fixture
def temp_chroma_path(tmp_path) -> Path:
    """Create a temporary path for ChromaDB testing."""
    chroma_path = tmp_path / "chroma_test"
    chroma_path.mkdir(exist_ok=True)
    return str(chroma_path)


# ============================================================================
# Session Fixtures
# ============================================================================

@pytest.fixture
def sample_session_id():
    """Sample session ID for testing."""
    return "test-session-abc-123"


@pytest.fixture
def sample_conversation_history():
    """Sample conversation history for testing."""
    return [
        {"role": "user", "content": "What is async programming?"},
        {"role": "assistant", "content": "Async programming allows for concurrent execution..."},
        {"role": "user", "content": "Can you give me an example?"},
        {"role": "assistant", "content": "Here's an example using async/await..."},
    ]
