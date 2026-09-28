"""API endpoint tests, run against the test app from conftest.create_test_app"""


class TestQueryEndpoint:
    def test_query_without_session_creates_one(self, client, mock_rag_system):
        response = client.post("/api/query", json={"query": "What is MCP?"})

        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "This is the answer."
        assert data["session_id"] == "session_1"
        assert "session_1" in mock_rag_system.session_manager.sessions
        mock_rag_system.query.assert_called_once_with("What is MCP?", "session_1")

    def test_query_with_existing_session_echoes_it(self, client, mock_rag_system):
        session_id = mock_rag_system.session_manager.create_session()

        response = client.post(
            "/api/query", json={"query": "And lesson 2?", "session_id": session_id}
        )

        assert response.status_code == 200
        assert response.json()["session_id"] == session_id
        mock_rag_system.query.assert_called_once_with("And lesson 2?", session_id)

    def test_sources_are_serialized(self, client, sample_sources):
        response = client.post("/api/query", json={"query": "What is MCP?"})

        assert response.json()["sources"] == sample_sources

    def test_source_without_url_serializes_as_null(self, client):
        response = client.post("/api/query", json={"query": "What is MCP?"})

        assert response.json()["sources"][2]["url"] is None

    def test_empty_sources(self, client, mock_rag_system):
        mock_rag_system.query.return_value = ("Hello!", [])

        response = client.post("/api/query", json={"query": "Hi"})

        assert response.status_code == 200
        assert response.json()["sources"] == []

    def test_missing_query_returns_422(self, client, mock_rag_system):
        response = client.post("/api/query", json={"session_id": "session_1"})

        assert response.status_code == 422
        mock_rag_system.query.assert_not_called()

    def test_malformed_body_returns_422(self, client, mock_rag_system):
        response = client.post(
            "/api/query", content="not json", headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422
        mock_rag_system.query.assert_not_called()

    def test_rag_error_returns_500(self, client, mock_rag_system):
        mock_rag_system.query.side_effect = Exception("boom")

        response = client.post("/api/query", json={"query": "What is MCP?"})

        assert response.status_code == 500
        assert response.json()["detail"] == "boom"


class TestCoursesEndpoint:
    def test_returns_course_stats(self, client, sample_course_titles):
        response = client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == len(sample_course_titles)
        assert data["course_titles"] == sample_course_titles

    def test_empty_catalog(self, client, mock_rag_system):
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": [],
        }

        response = client.get("/api/courses")

        assert response.status_code == 200
        assert response.json() == {"total_courses": 0, "course_titles": []}

    def test_analytics_error_returns_500(self, client, mock_rag_system):
        mock_rag_system.get_course_analytics.side_effect = Exception("chroma unavailable")

        response = client.get("/api/courses")

        assert response.status_code == 500
        assert response.json()["detail"] == "chroma unavailable"


class TestDeleteSessionEndpoint:
    def test_deletes_existing_session(self, client, mock_rag_system):
        session_id = mock_rag_system.session_manager.create_session()

        response = client.delete(f"/api/session/{session_id}")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert session_id not in mock_rag_system.session_manager.sessions

    def test_unknown_session_is_ok(self, client):
        response = client.delete("/api/session/does_not_exist")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestStaticRoot:
    def test_root_serves_index_html(self, client):
        response = client.get("/")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        assert "Course Materials Assistant" in response.text

    def test_unknown_api_route_returns_404(self, client):
        response = client.get("/api/unknown")

        assert response.status_code == 404
