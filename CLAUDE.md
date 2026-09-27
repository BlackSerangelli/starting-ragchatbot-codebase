# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Python dependencies are managed with `uv` (Python 3.13, see `.python-version`). Requires `ANTHROPIC_API_KEY` in a root `.env` (copy `.env.example`).

```bash
uv sync                                               # install dependencies
./run.sh                                              # start the server (Git Bash on Windows)
cd backend && uv run uvicorn app:app --reload --port 8000   # same, manually
```

- The server **must be started from `backend/`**: `app.py` and `config.py` use relative paths (`../docs`, `../frontend`, `./chroma_db`).
- App: http://localhost:8000 — OpenAPI docs: http://localhost:8000/docs
- The first start is slow: the embedding model is downloaded and `docs/` is embedded before uvicorn accepts connections. The page won't load until `Application startup complete` is logged.
- The frontend is served with plain `StaticFiles`. The no-cache `DevStaticFiles` class in `app.py` is defined but never mounted, so browsers may cache old `frontend/` files after edits.
- There is no test suite, linter, or formatter configured. `main.py` at the root is an unused placeholder.

## Architecture

A course-materials RAG chatbot: FastAPI backend (`backend/`) that also serves a static vanilla-JS frontend (`frontend/`, mounted at `/`). `RAGSystem` (`rag_system.py`) is the composition root that wires every other backend component together; `app.py` holds a single module-level instance.

```
frontend/ (index.html, script.js)
    │  POST /api/query, GET /api/courses          static files at /
    ▼
app.py (FastAPI) ── startup: ingest ../docs
    │
    ▼
RAGSystem (rag_system.py) ─── composition root
    ├── DocumentProcessor   text file → Course + CourseChunks        (ingestion)
    ├── VectorStore ─────── ChromaDB: course_catalog, course_content (both paths)
    ├── SessionManager      in-memory history per session_id         (query)
    ├── AIGenerator ─────── Anthropic API, one tool round            (query)
    └── ToolManager
          └── CourseSearchTool ──► VectorStore.search                (query)
```

| Module | Responsibility |
|---|---|
| `app.py` | HTTP endpoints, Pydantic request/response models, startup ingestion, static mount |
| `rag_system.py` | Builds all components from `config`; `add_course_folder` (ingest) and `query` (answer) |
| `document_processor.py` | Parses the course file format and makes sentence-based overlapping chunks |
| `vector_store.py` | ChromaDB persistence, embeddings, course-name resolution, filtered search |
| `ai_generator.py` | System prompt, Claude calls, executing tool calls between the two requests |
| `search_tools.py` | `Tool` interface, `CourseSearchTool`, `ToolManager` (registry, dispatch, source tracking) |
| `session_manager.py` | Conversation history, truncated to `MAX_HISTORY` exchanges |
| `models.py` | `Course`, `Lesson`, `CourseChunk` data models shared by ingestion and storage |
| `config.py` | `Config` dataclass with all settings; loads `.env` |

### Ingestion (runs on server startup)
`app.py` startup hook → `RAGSystem.add_course_folder("../docs")` → `DocumentProcessor` → `VectorStore`.

- Course files must follow a fixed text format parsed in `document_processor.py`: header lines `Course Title:`, `Course Link:`, `Course Instructor:`, then sections starting with `Lesson <N>: <title>`, each optionally followed by a `Lesson Link:` line. `.pdf`/`.docx` pass the extension filter but are read as plain text, so only `.txt` really works.
- Chunking is sentence-based (`CHUNK_SIZE` 800 chars, `CHUNK_OVERLAP` 100 chars, whole sentences only). Chunk text gets a context prefix that is part of the embedded text, and it is inconsistent: most lessons prefix only their first chunk with `Lesson N content:`, while the final lesson prefixes every chunk with `Course <title> Lesson N content:`.
- `VectorStore` uses two ChromaDB collections persisted in `backend/chroma_db/`, embedded with `all-MiniLM-L6-v2`:
  - `course_catalog`: one doc per course; **the course title is the document ID**. Lessons are stored as a JSON string in metadata (`lessons_json`) because Chroma metadata must be scalar.
  - `course_content`: chunks with `course_title`, `lesson_number`, `chunk_index` metadata; IDs are `<title_with_underscores>_<chunk_index>`.
- Startup skips any course whose title already exists in the catalog. Edits to an existing transcript are **not** picked up until `backend/chroma_db/` is deleted (or `add_course_folder(..., clear_existing=True)` is used).

### Query path (`POST /api/query`)
`app.py` → `RAGSystem.query` → `AIGenerator.generate_response` → Claude, with tool use:

1. `SessionManager` supplies history (last `MAX_HISTORY`=2 exchanges), which `AIGenerator` appends to the **system prompt** rather than the messages list. Sessions are in-memory only (`session_1`, `session_2`, …).
2. First Claude call includes the `search_course_content` tool (`tool_choice: auto`); the system prompt tells Claude to search only for course-specific questions, at most once.
3. On `tool_use`, `ToolManager` dispatches to `CourseSearchTool` → `VectorStore.search`, which first resolves a fuzzy `course_name` via a vector query on `course_catalog` (`n_results=1`, so it always picks the nearest course), then queries `course_content` with a `where` filter on course/lesson.
4. A second Claude call is made **without tools**, so there is exactly one search round. Supporting multi-step tool use means changing `AIGenerator._handle_tool_execution`.
   The endpoint is `async` but the Claude and ChromaDB calls are synchronous, so each request blocks the event loop.
5. Sources shown in the UI are not returned through Claude: `CourseSearchTool` stores them in `last_sources` during formatting, and `RAGSystem.query` reads them via `ToolManager.get_last_sources()` then calls `reset_sources()`. This state lives on a single shared tool instance.

New tools: subclass `Tool` in `search_tools.py` (implement `get_tool_definition` returning an Anthropic tool schema, and `execute`), then register it in `RAGSystem.__init__`.

### Configuration
All settings (Claude model, embedding model, chunk sizes, `MAX_RESULTS`, `MAX_HISTORY`, `CHROMA_PATH`) are hardcoded in the `Config` dataclass in `backend/config.py`; only the API key comes from the environment.

### Frontend
`frontend/script.js` posts `{query, session_id}` to `/api/query`, keeps the returned `session_id` for later messages, renders answers as Markdown with `marked` (loaded from a CDN in `index.html`), and loads the sidebar from `GET /api/courses`.
