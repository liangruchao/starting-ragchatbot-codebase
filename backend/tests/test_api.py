"""API endpoint tests for the RAG system FastAPI application."""

import pytest
from fastapi import status


@pytest.mark.api
class TestQueryEndpoint:
    """Tests for /api/query endpoint."""

    def test_query_success(self, client):
        """Test successful query request."""
        response = client.post(
            "/api/query",
            json={"query": "What is async programming?"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        assert isinstance(data["sources"], list)

    def test_query_with_session_id(self, client):
        """Test query request with existing session ID."""
        session_id = "existing-session-456"
        response = client.post(
            "/api/query",
            json={
                "query": "What are decorators?",
                "session_id": session_id
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["session_id"] == session_id

    def test_query_generates_session_id(self, client):
        """Test that query generates session ID when not provided."""
        response = client.post(
            "/api/query",
            json={"query": "Test query"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["session_id"]
        assert isinstance(data["session_id"], str)

    def test_query_empty_query(self, client):
        """Test query request with empty query string."""
        response = client.post(
            "/api/query",
            json={"query": ""}
        )

        # Should still process, even if empty
        assert response.status_code == status.HTTP_200_OK

    def test_query_long_query(self, client):
        """Test query request with a long query string."""
        long_query = "What is async programming? " * 100
        response = client.post(
            "/api/query",
            json={"query": long_query}
        )

        assert response.status_code == status.HTTP_200_OK

    def test_query_special_characters(self, client):
        """Test query with special characters."""
        response = client.post(
            "/api/query",
            json={"query": "What's the difference between @decorator & context manager?"}
        )

        assert response.status_code == status.HTTP_200_OK

    def test_query_unicode_characters(self, client):
        """Test query with Unicode characters."""
        response = client.post(
            "/api/query",
            json={"query": "Explain Python中的异步编程"}
        )

        assert response.status_code == status.HTTP_200_OK

    def test_query_server_error(self, client, test_app):
        """Test query endpoint handles server errors gracefully."""
        test_app.state.query_should_fail = True
        response = client.post(
            "/api/query",
            json={"query": "Test query"}
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "detail" in response.json()
        test_app.state.query_should_fail = False

    def test_query_missing_query_field(self, client):
        """Test query request without required query field."""
        response = client.post(
            "/api/query",
            json={"session_id": "test-session"}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_query_invalid_body_type(self, client):
        """Test query with invalid content type."""
        response = client.post(
            "/api/query",
            data="not a json"
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.api
class TestCoursesEndpoint:
    """Tests for /api/courses endpoint."""

    def test_get_courses_success(self, client):
        """Test successful request to get course statistics."""
        response = client.get("/api/courses")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_courses" in data
        assert "course_titles" in data
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)

    def test_get_courses_empty_catalog(self, client, test_app):
        """Test getting courses when catalog is empty."""
        from tests.conftest import CourseStats
        test_app.state.mock_course_stats = CourseStats(
            total_courses=0,
            course_titles=[]
        )

        response = client.get("/api/courses")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_courses"] == 0
        assert data["course_titles"] == []

    def test_get_courses_multiple_titles(self, client, test_app):
        """Test getting courses with multiple course titles."""
        from tests.conftest import CourseStats
        test_app.state.mock_course_stats = CourseStats(
            total_courses=3,
            course_titles=["Python Basics", "Advanced Python", "Data Science"]
        )

        response = client.get("/api/courses")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_courses"] == 3
        assert len(data["course_titles"]) == 3

    def test_get_courses_server_error(self, client, test_app):
        """Test courses endpoint handles server errors gracefully."""
        test_app.state.courses_should_fail = True
        response = client.get("/api/courses")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "detail" in response.json()
        test_app.state.courses_should_fail = False


@pytest.mark.api
class TestAPIIntegration:
    """Integration tests for API behavior."""

    def test_concurrent_queries_same_session(self, client):
        """Test multiple queries using the same session."""
        session_id = "concurrent-test-session"

        # First query
        response1 = client.post(
            "/api/query",
            json={
                "query": "First question",
                "session_id": session_id
            }
        )
        assert response1.status_code == status.HTTP_200_OK

        # Second query with same session
        response2 = client.post(
            "/api/query",
            json={
                "query": "Follow-up question",
                "session_id": session_id
            }
        )
        assert response2.status_code == status.HTTP_200_OK

        # Verify session ID is preserved
        assert response1.json()["session_id"] == response2.json()["session_id"]

    def test_query_and_get_courses_sequence(self, client):
        """Test calling query and then getting course stats."""
        # Make a query
        query_response = client.post(
            "/api/query",
            json={"query": "Test query"}
        )
        assert query_response.status_code == status.HTTP_200_OK

        # Get course stats
        courses_response = client.get("/api/courses")
        assert courses_response.status_code == status.HTTP_200_OK

    def test_response_structure_consistency(self, client):
        """Test that response structure is consistent across multiple calls."""
        responses = []
        for i in range(3):
            response = client.post(
                "/api/query",
                json={"query": f"Test query {i}"}
            )
            responses.append(response.json())

        # All responses should have the same structure
        for resp in responses:
            assert set(resp.keys()) == {"answer", "sources", "session_id"}


@pytest.mark.api
@pytest.mark.asyncio
class TestAsyncAPI:
    """Async API tests using AsyncClient."""

    async def test_async_query_request(self, async_client):
        """Test query endpoint using async client."""
        response = await async_client.post(
            "/api/query",
            json={"query": "Async test query"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "answer" in data

    async def test_async_get_courses_request(self, async_client):
        """Test courses endpoint using async client."""
        response = await async_client.get("/api/courses")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_courses" in data

    async def test_async_multiple_concurrent_requests(self, async_client):
        """Test multiple concurrent async requests."""
        import asyncio

        async def make_query(query_text):
            response = await async_client.post(
                "/api/query",
                json={"query": query_text}
            )
            return response

        # Make 5 concurrent requests
        responses = await asyncio.gather(*[
            make_query(f"Concurrent query {i}")
            for i in range(5)
        ])

        # All should succeed
        for response in responses:
            assert response.status_code == status.HTTP_200_OK


@pytest.mark.api
class TestAPIHeadersAndMiddleware:
    """Tests for API headers and middleware configuration."""

    def test_cors_headers(self, client):
        """Test that CORS headers are properly set."""
        response = client.options(
            "/api/query",
            headers={"Origin": "http://example.com"}
        )

        # Check for CORS headers
        assert "access-control-allow-origin" in response.headers

    def test_content_type_header(self, client):
        """Test that API returns JSON content type."""
        response = client.post(
            "/api/query",
            json={"query": "Test query"}
        )

        assert "application/json" in response.headers.get("content-type", "")

    def test_api_accepts_json(self, client):
        """Test that API properly accepts JSON content."""
        response = client.post(
            "/api/query",
            json={"query": "Test"},
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == status.HTTP_200_OK
