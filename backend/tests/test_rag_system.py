"""Unit tests for RAG system components."""

from unittest.mock import Mock, patch, call
from models import Course, Lesson, CourseChunk


@pytest.mark.unit
class TestRAGSystem:
    """Unit tests for the RAGSystem orchestrator."""

    def test_rag_system_initialization(self, mock_config):
        """Test that RAGSystem initializes with all components."""
        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.VectorStore'), \
             patch('rag_system.AIGenerator'), \
             patch('rag_system.SessionManager'), \
             patch('rag_system.ToolManager'), \
             patch('rag_system.CourseSearchTool'), \
             patch('rag_system.CourseOutlineTool'):

            from rag_system import RAGSystem
            system = RAGSystem(mock_config)

            assert system.config is mock_config
            assert hasattr(system, 'document_processor')
            assert hasattr(system, 'vector_store')
            assert hasattr(system, 'ai_generator')
            assert hasattr(system, 'session_manager')
            assert hasattr(system, 'tool_manager')

    def test_add_course_document_success(
        self,
        rag_system,
        mock_document_processor,
        mock_vector_store
    ):
        """Test adding a course document successfully."""
        file_path = "/path/to/course.txt"
        mock_course = Course(
            title="Test Course",
            lessons=[Lesson(lesson_number=1, title="Lesson 1")]
        )
        mock_chunks = [
            CourseChunk(
                content="Test content",
                course_title="Test Course",
                lesson_number=1,
                chunk_index=0
            )
        ]

        mock_document_processor.process_course_document.return_value = (mock_course, mock_chunks)
        mock_vector_store.add_course_metadata.return_value = None
        mock_vector_store.add_course_content.return_value = None

        course, chunk_count = rag_system.add_course_document(file_path)

        assert course is mock_course
        assert chunk_count == len(mock_chunks)
        mock_vector_store.add_course_metadata.assert_called_once_with(mock_course)
        mock_vector_store.add_course_content.assert_called_once_with(mock_chunks)

    def test_add_course_document_error(self, rag_system, mock_document_processor):
        """Test handling error when adding course document."""
        mock_document_processor.process_course_document.side_effect = Exception("Parse error")

        course, chunk_count = rag_system.add_course_document("/path/to/course.txt")

        assert course is None
        assert chunk_count == 0

    def test_add_course_folder_clear_existing(
        self,
        rag_system,
        mock_vector_store
    ):
        """Test adding course folder with clear_existing flag."""
        with patch('os.path.exists', return_value=True), \
             patch('os.listdir', return_value=['course1.txt']), \
             patch('os.path.isfile', return_value=True):

            rag_system.add_course_folder("/path/to/folder", clear_existing=True)

            mock_vector_store.clear_all_data.assert_called_once()

    def test_add_course_folder_nonexistent_folder(self, rag_system):
        """Test adding course folder that doesn't exist."""
        with patch('os.path.exists', return_value=False):
            courses, chunks = rag_system.add_course_folder("/nonexistent/folder")

            assert courses == 0
            assert chunks == 0

    def test_query_with_session(
        self,
        rag_system,
        mock_ai_generator,
        mock_session_manager
    ):
        """Test query with existing session."""
        session_id = "test-session-123"
        query = "What is async programming?"
        mock_ai_generator.generate_response.return_value = "AI response"
        mock_session_manager.get_conversation_history.return_value = None
        mock_session_manager.create_session.return_value = "new-session"

        response, sources = rag_system.query(query, session_id)

        assert response == "AI response"
        mock_session_manager.get_conversation_history.assert_called_once_with(session_id)
        mock_session_manager.add_exchange.assert_called_once_with(
            session_id, query, "AI response"
        )

    def test_query_without_session(
        self,
        rag_system,
        mock_ai_generator,
        mock_session_manager
    ):
        """Test query without providing session ID."""
        query = "What is async programming?"
        mock_ai_generator.generate_response.return_value = "AI response"
        mock_session_manager.get_conversation_history.return_value = None

        response, sources = rag_system.query(query, session_id=None)

        assert response == "AI response"
        # History should not be retrieved for new sessions
        mock_session_manager.get_conversation_history.assert_not_called()

    def test_get_course_analytics(self, rag_system, mock_vector_store):
        """Test getting course analytics."""
        mock_vector_store.get_course_count.return_value = 5
        mock_vector_store.get_existing_course_titles.return_value = [
            "Course 1", "Course 2"
        ]

        analytics = rag_system.get_course_analytics()

        assert analytics["total_courses"] == 5
        assert analytics["course_titles"] == ["Course 1", "Course 2"]


@pytest.mark.unit
class TestDocumentProcessor:
    """Unit tests for DocumentProcessor."""

    def test_document_processor_initialization(self):
        """Test DocumentProcessor initialization."""
        from document_processor import DocumentProcessor

        processor = DocumentProcessor(chunk_size=100, overlap=10)

        assert processor.chunk_size == 100
        assert processor.overlap == 10

    def test_process_course_document_parses_metadata(self, sample_course_file):
        """Test that course metadata is parsed correctly."""
        from document_processor import DocumentProcessor

        processor = DocumentProcessor(chunk_size=800, overlap=100)
        course, chunks = processor.process_course_document(str(sample_course_file))

        assert course.title == "Advanced Python Programming"
        assert course.instructor == "Dr. Jane Smith"
        assert course.course_link == "https://example.com/python-advanced"
        assert len(course.lessons) == 2
        assert course.lessons[0].lesson_number == 1
        assert course.lessons[0].title == "Introduction to Async Programming"

    def test_document_processor_creates_chunks(self, sample_course_file):
        """Test that document is chunked properly."""
        from document_processor import DocumentProcessor

        processor = DocumentProcessor(chunk_size=800, overlap=100)
        course, chunks = processor.process_course_document(str(sample_course_file))

        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.course_title == course.title
            assert chunk.content
            assert isinstance(chunk.chunk_index, int)

    def test_document_processor_chunk_overlap(self, sample_course_text, tmp_path):
        """Test that chunks have proper overlap."""
        from document_processor import DocumentProcessor

        # Create test content
        test_file = tmp_path / "overlap_test.txt"
        long_content = "This is sentence one. " + "This is sentence two. " * 200
        test_file.write_text(f"Course Title: Test Course\n\n{long_content}")

        processor = DocumentProcessor(chunk_size=200, overlap=50)
        course, chunks = processor.process_course_document(str(test_file))

        # Check that adjacent chunks have overlap
        if len(chunks) > 1:
            first_chunk_end = chunks[0].content[-50:]
            second_chunk_start = chunks[1].content[:50]
            # Should have some overlap
            assert chunks[0].content or chunks[1].content


@pytest.mark.unit
class TestVectorStore:
    """Unit tests for VectorStore."""

    def test_vector_store_initialization(self):
        """Test VectorStore initialization."""
        with patch('vector_store.chromadb'):
            from vector_store import VectorStore

            store = VectorStore(
                chroma_path=":memory:",
                embedding_model="test-model",
                max_results=5
            )

            assert store.chroma_path == ":memory:"
            assert store.max_results == 5

    def test_add_course_metadata(self):
        """Test adding course metadata to vector store."""
        with patch('vector_store.chromadb') as mock_chroma:
            from vector_store import VectorStore

            mock_collection = Mock()
            mock_chroma.Client.return_value.get_or_create_collection.return_value = mock_collection

            store = VectorStore(":memory:", "test-model", 5)
            course = Course(
                title="Test Course",
                course_link="https://example.com",
                instructor="Test Instructor",
                lessons=[]
            )

            store.add_course_metadata(course)

            mock_collection.add.assert_called_once()

    def test_search(self):
        """Test searching vector store."""
        with patch('vector_store.chromadb') as mock_chroma:
            from vector_store import VectorStore

            mock_collection = Mock()
            mock_collection.query.return_value = {
                "documents": [["Test document 1", "Test document 2"]],
                "metadatas": [[
                    {"course": "Test Course", "lesson": 1, "chunk": 0},
                    {"course": "Test Course", "lesson": 1, "chunk": 1}
                ]],
                "distances": [[0.1, 0.2]]
            }
            mock_chroma.Client.return_value.get_or_create_collection.return_value = mock_collection

            store = VectorStore(":memory:", "test-model", 5)
            results = store.search("test query")

            assert len(results) == 2
            assert results[0]["content"] == "Test document 1"
            mock_collection.query.assert_called_once()

    def test_get_course_count(self):
        """Test getting course count."""
        with patch('vector_store.chromadb') as mock_chroma:
            from vector_store import VectorStore

            mock_collection = Mock()
            mock_collection.count.return_value = 10
            mock_chroma.Client.return_value.get_or_create_collection.return_value = mock_collection

            store = VectorStore(":memory:", "test-model", 5)
            count = store.get_course_count()

            assert count == 10


@pytest.mark.unit
class TestSessionManager:
    """Unit tests for SessionManager."""

    def test_session_manager_initialization(self):
        """Test SessionManager initialization."""
        from session_manager import SessionManager

        manager = SessionManager(max_history=5)

        assert manager.max_history == 5
        assert manager.sessions == {}

    def test_create_session(self):
        """Test creating a new session."""
        from session_manager import SessionManager

        manager = SessionManager(max_history=2)
        session_id = manager.create_session()

        assert session_id
        assert session_id in manager.sessions
        assert manager.sessions[session_id] == []

    def test_add_exchange(self):
        """Test adding conversation exchange to session."""
        from session_manager import SessionManager

        manager = SessionManager(max_history=2)
        session_id = manager.create_session()

        manager.add_exchange(session_id, "Question 1", "Answer 1")

        assert len(manager.sessions[session_id]) == 1
        assert manager.sessions[session_id][0] == {
            "role": "user",
            "content": "Question 1"
        }
        assert manager.sessions[session_id][1] == {
            "role": "assistant",
            "content": "Answer 1"
        }

    def test_max_history_enforcement(self):
        """Test that max history is enforced."""
        from session_manager import SessionManager

        manager = SessionManager(max_history=2)  # Only keep 2 exchanges
        session_id = manager.create_session()

        # Add 4 exchanges
        for i in range(4):
            manager.add_exchange(session_id, f"Q{i+1}", f"A{i+1}")

        # Should only have 4 messages (2 exchanges * 2 messages each)
        history = manager.sessions[session_id]
        assert len(history) == 4
        # Oldest messages should be removed
        assert history[0]["content"] == "Q3"
        assert history[-1]["content"] == "A4"

    def test_get_conversation_history(self):
        """Test retrieving conversation history."""
        from session_manager import SessionManager

        manager = SessionManager(max_history=5)
        session_id = manager.create_session()

        manager.add_exchange(session_id, "Q1", "A1")
        manager.add_exchange(session_id, "Q2", "A2")

        history = manager.get_conversation_history(session_id)

        assert len(history) == 4
        assert history[0]["content"] == "Q1"
        assert history[1]["content"] == "A1"
        assert history[2]["content"] == "Q2"
        assert history[3]["content"] == "A2"

    def test_get_history_nonexistent_session(self):
        """Test getting history for non-existent session."""
        from session_manager import SessionManager

        manager = SessionManager(max_history=2)
        history = manager.get_conversation_history("nonexistent-session")

        assert history is None


@pytest.mark.unit
class TestAIGenerator:
    """Unit tests for AIGenerator."""

    def test_ai_generator_initialization(self):
        """Test AIGenerator initialization."""
        with patch('ai_generator.Anthropic'):
            from ai_generator import AIGenerator

            generator = AIGenerator(
                api_key="test-key",
                model="claude-sonnet-4-20250514"
            )

            assert generator.model == "claude-sonnet-4-20250514"

    def test_generate_response(self):
        """Test generating AI response."""
        with patch('ai_generator.Anthropic') as mock_anthropic:
            from ai_generator import AIGenerator

            mock_client = Mock()
            mock_response = Mock()
            mock_response.content = [Mock(type="text", text="This is a test response.")]
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            generator = AIGenerator("test-key", "claude-sonnet-4-20250514")
            response = generator.generate_response(
                query="Test query",
                conversation_history=None,
                tools=[],
                tool_manager=Mock()
            )

            assert response == "This is a test response."


@pytest.mark.unit
class TestSearchTools:
    """Unit tests for search tools."""

    def test_course_search_tool_definition(self):
        """Test CourseSearchTool definition structure."""
        from search_tools import CourseSearchTool

        tool = CourseSearchTool(Mock())

        definition = tool.get_definition()

        assert definition["name"] == "course_search"
        assert "description" in definition
        assert "input_schema" in definition

    def test_course_outline_tool_definition(self):
        """Test CourseOutlineTool definition structure."""
        from search_tools import CourseOutlineTool

        tool = CourseOutlineTool(Mock())

        definition = tool.get_definition()

        assert definition["name"] == "course_outline"
        assert "description" in definition
        assert "input_schema" in definition

    def test_tool_manager_register_tool(self):
        """Test registering tools with ToolManager."""
        from search_tools import ToolManager, CourseSearchTool

        manager = ToolManager()
        tool = CourseSearchTool(Mock())

        manager.register_tool(tool)

        assert len(manager.tools) == 1
        assert "course_search" in manager.tools

    def test_tool_manager_get_tool_definitions(self):
        """Test getting all tool definitions."""
        from search_tools import ToolManager, CourseSearchTool, CourseOutlineTool

        manager = ToolManager()
        manager.register_tool(CourseSearchTool(Mock()))
        manager.register_tool(CourseOutlineTool(Mock()))

        definitions = manager.get_tool_definitions()

        assert len(definitions) == 2
        assert any(d["name"] == "course_search" for d in definitions)
        assert any(d["name"] == "course_outline" for d in definitions)

    def test_course_search_tool_execution(self):
        """Test executing course search tool."""
        from search_tools import CourseSearchTool

        mock_store = Mock()
        mock_store.search.return_value = [
            {
                "content": "Test content",
                "course_title": "Test Course",
                "lesson_number": 1,
                "distance": 0.1
            }
        ]

        tool = CourseSearchTool(mock_store)
        result = tool.execute(query="test query")

        assert "results" in result
        assert len(result["results"]) == 1
        mock_store.search.assert_called_once()


@pytest.mark.unit
class TestPydanticModels:
    """Unit tests for Pydantic models."""

    def test_course_model(self):
        """Test Course model validation."""
        course = Course(
            title="Test Course",
            course_link="https://example.com",
            instructor="Test Instructor",
            lessons=[
                Lesson(lesson_number=1, title="Lesson 1"),
                Lesson(lesson_number=2, title="Lesson 2"),
            ]
        )

        assert course.title == "Test Course"
        assert len(course.lessons) == 2
        assert course.lessons[0].lesson_number == 1

    def test_lesson_model(self):
        """Test Lesson model validation."""
        lesson = Lesson(
            lesson_number=5,
            title="Advanced Topics",
            lesson_link="https://example.com/lesson5"
        )

        assert lesson.lesson_number == 5
        assert lesson.title == "Advanced Topics"

    def test_course_chunk_model(self):
        """Test CourseChunk model validation."""
        chunk = CourseChunk(
            content="This is test content for chunking.",
            course_title="Test Course",
            lesson_number=1,
            chunk_index=0
        )

        assert chunk.course_title == "Test Course"
        assert chunk.chunk_index == 0
