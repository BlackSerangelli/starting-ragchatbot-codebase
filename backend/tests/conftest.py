"""Shared fixtures for the backend test suite.

backend/app.py can't be imported in tests: importing it builds a real RAGSystem
(ChromaDB + embedding model) and mounts ../frontend, which may not exist. Instead,
create_test_app() below defines the same endpoints against a mocked RAG system.
Keep these endpoints in sync with backend/app.py.
"""
from typing import List, Optional
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient
from pydantic import BaseModel

from session_manager import SessionManager


# Pydantic models mirroring backend/app.py
class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


class Source(BaseModel):
    text: str
    url: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    sources: List[Source]
    session_id: str


class CourseStats(BaseModel):
    total_courses: int
    course_titles: List[str]


def create_test_app(rag_system, static_dir: Optional[str] = None) -> FastAPI:
    """Build an app with the same API endpoints as backend/app.py, minus startup ingestion"""
    app = FastAPI(title="Course Materials RAG System (test)")

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = rag_system.session_manager.create_session()

            answer, sources = rag_system.query(request.query, session_id)

            return QueryResponse(answer=answer, sources=sources, session_id=session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/api/session/{session_id}")
    async def delete_session(session_id: str):
        rag_system.session_manager.delete_session(session_id)
        return {"status": "ok"}

    if static_dir is not None:
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return app


@pytest.fixture
def sample_sources():
    """Sources in the shape CourseSearchTool/CourseOutlineTool store in last_sources"""
    return [
        {"text": "Building Towards Computer Use - Lesson 1", "url": "https://example.com/lesson1"},
        {"text": "MCP: Build Rich-Context AI Apps - Lesson 3", "url": "https://example.com/lesson3"},
        {"text": "Advanced Retrieval for AI - Lesson 2", "url": None},
    ]


@pytest.fixture
def sample_course_titles():
    return [
        "Building Towards Computer Use with Anthropic",
        "MCP: Build Rich-Context AI Apps with Anthropic",
        "Advanced Retrieval for AI with Chroma",
    ]


@pytest.fixture
def mock_rag_system(sample_sources, sample_course_titles):
    """RAGSystem stand-in with a real SessionManager and canned query/analytics results"""
    rag = MagicMock()
    rag.session_manager = SessionManager(max_history=2)
    rag.query.return_value = ("This is the answer.", sample_sources)
    rag.get_course_analytics.return_value = {
        "total_courses": len(sample_course_titles),
        "course_titles": sample_course_titles,
    }
    return rag


@pytest.fixture
def static_dir(tmp_path):
    """A minimal frontend directory so / can be served without the real frontend/"""
    (tmp_path / "index.html").write_text(
        "<!doctype html><html><head><title>Course Materials Assistant</title></head>"
        "<body><div id=\"chat\"></div></body></html>",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def app(mock_rag_system, static_dir):
    return create_test_app(mock_rag_system, static_dir=str(static_dir))


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client
