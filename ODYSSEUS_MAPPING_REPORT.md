# Odysseus → Albert IA Migration Mapping Report

---

## 1. Model Connection Engine (highest priority)

### Call Chain (entry → provider)

| Order | File | Role |
|---|---|---|
| 1 | `routes/chat_routes.py` | HTTP entry point — receives chat POST, calls `stream_llm` / `llm_call_async` / `stream_agent_loop` |
| 2 | `src/endpoint_resolver.py` | Resolves which DB endpoint to use, builds URL + provider-specific headers; `resolve_endpoint_runtime()` → reads `ModelEndpoint.api_key` |
| 3 | `src/llm_core.py` | Core HTTP client — `stream_llm()`, `llm_call_async()`, `stream_llm_with_fallback()` actually call the provider |
| 4 | `routes/model_routes.py` | Admin CRUD for endpoints; `_probe_endpoint()` for model discovery; not in the hot path |
| 5 | `core/database.py` | `ModelEndpoint` + `ProviderAuthSession` SQLAlchemy ORM |
| 6 | `src/model_discovery.py` | Scans local network for running servers (Ollama, vLLM, LM Studio) |

### Where API Keys / Model Names / Switching Live

| Concern | Location |
|---|---|
| API keys at rest | `core/database.py` → `ModelEndpoint.api_key` (`EncryptedText` column, AES-encrypted in SQLite) |
| OAuth / session tokens | `core/database.py` → `ProviderAuthSession.access_token` (e.g. ChatGPT subscription) |
| Provider detection | `src/llm_core.py` → `_detect_provider(url)` — infers provider from URL pattern |
| Header building | `src/endpoint_resolver.py` → `build_headers(api_key, base)` — per-provider auth header format |
| Model selection | `ModelEndpoint.cached_models` (JSON list, refreshed by `_probe_endpoint`) + `ModelEndpoint.pinned_models` for admin-forced IDs |
| Fallback chains | `src/endpoint_resolver.py` → `resolve_chat_fallback_candidates()` reads settings for `default_model_fallbacks` etc. |
| Endpoint switching | Admin UI → `POST /api/model-endpoints` → `core/database.py`; per-user picker reads `GET /api/models` |

**No API keys in `.env`** — all stored in the admin-managed DB. The only env var consumed is `LLM_CONNECT_TIMEOUT` (seconds, default 10).

### Multi-Provider Abstraction

Fully abstracted. `_detect_provider()` in `src/llm_core.py` pattern-matches on base URL and dispatches to provider-specific builders:

| Provider | Detected by |
|---|---|
| anthropic | api.anthropic.com or path `/v1/messages` |
| openai | api.openai.com |
| ollama | port 11434 or "ollama" in hostname |
| groq, mistral, together, fireworks, google, xai, deepseek, openrouter, z.ai | hostname match via `_host_match()` |
| chatgpt-subscription | special `ProviderAuthSession` flow |
| copilot | `src/copilot.py` separate headers/flow |

Provider-specific payload builders in `src/llm_core.py`: `_build_anthropic_payload()`, `_build_ollama_payload()`, `_build_chatgpt_responses_payload()`.

### Dependency Drag — What Else Must Come Along

| Module | Why needed |
|---|---|
| `core/database.py` | `ModelEndpoint`, `ProviderAuthSession` schemas + SQLite engine |
| `core/middleware.py` | `require_admin()` — guards model management endpoints |
| `src/model_context.py` | Context length constants (per-model token limits) |
| `src/tls_overrides.py` | `llm_verify()` — TLS cert verification flag |
| `src/settings.py` | `load_settings()` / `save_settings()` — fallback chains and model preferences |
| `src/secret_storage.py` | AES key derivation for `EncryptedText` columns |
| `src/auth_helpers.py` | `effective_user()`, `owner_filter()` — per-user endpoint scoping |
| `src/chatgpt_subscription.py` | ChatGPT subscription provider (if you want it) |
| `src/copilot.py` | GitHub Copilot provider (if you want it) |
| `src/endpoint_resolver.py` | URL + header normalization |
| `src/model_discovery.py` | Local server scanning |

---

## 2. UI Shell (`companion/` + `static/`)

### File Counts and Sizes

| Path | Files | Size | Notes |
|---|---|---|---|
| `companion/` | 3 Python files | ~60 KB | `__init__.py`, `routes.py` (389 lines, serves companion HTML view), `pairing.py` |
| `static/` (total) | 175 files | ~12 MB | |
| `static/js/` | 152 files | 5.7 MB | All app JS — chat, sidebar, settings, all features |
| `static/lib/` | 6 files | 3.3 MB | Third-party bundled libs |
| `static/fonts/` | 7 files | 756 KB | |
| `static/icons/` | 3 files | — | |
| `static/*.html` | 2 files | — | `index.html` (main SPA), one other |

`companion/routes.py` reads `ModelEndpoint` rows directly from the DB and calls `build_chat_url()` from `src/endpoint_resolver.py` to build the companion view. It does not depend on chat routes or memory.

### Hard UI Dependencies on Routes Beyond the Model Engine

The JS calls virtually every backend route. Migrating only the model engine leaves these broken in the UI:

| Broken feature | Route(s) |
|---|---|
| Brain (memory/skills modal) | `routes/memory_routes.py`, `routes/skills_routes.py` |
| Tasks / Assistant | `routes/task_routes.py`, `routes/assistant_routes.py` |
| Cookbook (local model download/serve) | `routes/cookbook_routes.py` |
| Deep Research | `routes/research_routes.py` |
| Session history + search | `routes/session_routes.py`, `routes/history_routes.py` |
| Personal docs panel (admin) | `routes/personal_routes.py` |
| MCP server management | `routes/mcp_routes.py` |
| Slash commands referencing other tools | All of the above + more |

The chat-only path (`static/js/chat.js`, `chatStream.js`, `chatRenderer.js`) + model picker (`static/js/settings.js`) would survive with just the model engine. Everything else in the sidebar and tool rail would 404 or break silently.

---

## 3. Personal Docs / Notes Bridge (`data/personal_docs/`)

### Path Constants (defined in `src/constants.py`)

```
DATA_DIR     = $ODYSSEUS_DATA_DIR  (or  <repo>/data/)
PERSONAL_DIR = DATA_DIR/personal_docs
RUNBOOK_DIR  = PERSONAL_DIR/runbook
```

### How It's Read/Written

| Mechanism | Detail |
|---|---|
| Indexer | `src/personal_docs.py` → `PersonalDocsManager.__init__(personal_dir)` — walks the tree, reads `.txt .md .json .pdf .docx .pptx .xlsx .xls .epub` |
| Metadata files | `data/personal_docs/indexed_directories.json` — list of extra directories to index; `data/personal_docs/excluded_files.json` — denylist |
| RAG ingestion | `PersonalDocsManager.refresh_index()` calls `rag_manager.index_personal_documents(self.personal_dir)` → feeds ChromaDB |
| Route handler | `routes/personal_routes.py` — upload, `add_directory`, `remove_directory`, `reload`; also imports `src/personal_docs.py` |
| MCP exposure | `mcp_servers/rag_server.py` — exposes `list`, `add_directory`, `remove_directory` over MCP stdio |
| Initialization | `src/app_initializer.py` line 52: `personal_docs_manager = PersonalDocsManager(PERSONAL_DIR, rag_manager)` |

The `runbook/` subfolder has no special code path — it is pre-seeded and indexed like any other subdirectory under `personal_docs/`.

---

## 4. Memory/RAG System

### Files

| Path | Purpose |
|---|---|
| `src/memory.py` (387 lines) | `MemoryManager` — stores/retrieves long-term memories in SQLite + JSON |
| `src/memory_vector.py` (251 lines) | `MemoryVectorStore` — Chroma-backed vector search on memories |
| `src/rag_manager.py` (70 lines) | Thin RAG coordinator; wraps `chroma_client.py` |
| `src/chroma_client.py` | ChromaDB client singleton |
| `src/rag_singleton.py` | Singleton pattern for `rag_manager` |
| `src/rag_vector.py` | Vector operations for RAG |
| `src/embeddings.py` | Embedding generation (calls the model engine) |
| `src/embedding_lanes.py` | Parallel embedding pipeline |
| `services/memory/memory_extractor.py` (659 lines) | LLM-based extraction of memories from conversations |
| `services/memory/skills.py` (716 lines) | `SkillsManager` — auto-extracts reusable skills from conversations |
| `services/memory/skill_extractor.py` (305 lines) | LLM-based skill pattern extraction |
| `services/memory/skill_format.py` (444 lines) | Skill validation and formatting |
| `services/memory/skill_importer.py` (283 lines) | Imports skills from external sources |
| `services/memory/service.py` (126 lines) | Memory service lifecycle |
| `routes/memory_routes.py` | CRUD for memories |
| `routes/skills_routes.py` | CRUD + audit for skills |
| `mcp_servers/memory_server.py` | MCP stdio server: list/add/edit/delete/search memories |
| `mcp_servers/rag_server.py` | MCP stdio server: list/add_directory/remove_directory for RAG docs |
| `data/chroma/` | ChromaDB persisted vector store (currently ~4 KB, likely near-empty) |
| `data/memory_vectors/` | Secondary vector store for memory-specific embeddings |
| `data/rag/` | RAG index data |

### Overlap with Albert's `app/memory/` and `data/vectorstore/`

Odysseus's memory system and Albert's are structurally parallel: both use a vector store for semantic search, both extract facts from conversations, both persist somewhere. The conflict is threefold. First, **duplicate ChromaDB instances**: Odysseus writes to `data/chroma/` and `data/memory_vectors/`; Albert writes to `data/vectorstore/` — you would be running two separate Chroma databases unless merged. Second, **extraction pipeline coupling**: `services/memory/memory_extractor.py` and `skill_extractor.py` call the LLM through Odysseus's model engine (`src/llm_core.py`), so they bring the entire engine dependency chain with them. Third, **schema mismatch**: Odysseus memories live in its SQLite `core/database.py` tables; Albert's memory format (in `app/memory/`) is unknown from the outside — reconciling them requires reading Albert's code. No resolution recommended here; flagged for the user to decide.

---

## 5. Skills/Tools System

### Files

| Path | Purpose |
|---|---|
| `src/agent_tools/__init__.py` | Facade re-exporting all tool submodules |
| `src/agent_tools/document_tools.py` | File read/edit/active-document ops |
| `src/agent_tools/filesystem_tools.py` | Filesystem navigation |
| `src/agent_tools/model_interaction_tools.py` | `ChatWithModelTool`, `AskTeacherTool`, `ListModelsTool` |
| `src/agent_tools/session_tools.py` | Session management tools |
| `src/agent_tools/subprocess_tools.py` | Shell subprocess execution |
| `src/agent_tools/web_tools.py` | Web search and fetch |
| `src/agent_tools/bg_job_tools.py` | Background job triggers |
| `src/tool_schemas.py` | OpenAI-format function schemas for all tools |
| `src/tool_implementations.py` | `do_*` handler functions |
| `src/tool_execution.py` | Execution dispatch + MCP tool integration |
| `src/tool_parsing.py` | Parses model tool-call outputs |
| `src/tool_policy.py` | Per-session tool enable/disable policy |
| `src/tool_security.py` | Sandboxing and path-escape checks |
| `src/tool_utils.py` | Shared helpers |
| `src/tool_index.py` | Tool registry index |
| `services/memory/skills.py` | `SkillsManager` — auto-learned conversation skills |
| `data/skills/` | **Empty directory** — skills stored in SQLite, not as files |
| `routes/skills_routes.py` | Skills CRUD + AI audit endpoint |

### Overlap with Albert's `app/tools/`

Albert's `app/tools/` is expected to contain physics-specific reasoning tools (symbolic math, equation solvers, etc.). Odysseus's `src/agent_tools/` is general-purpose scaffolding: filesystem ops, web fetch, subprocess, document editing. The two sets do not overlap in *purpose*, but they share the *concept* of a tool registry. The architectural conflict is format: Odysseus uses OpenAI function-call JSON schema (`tool_schemas.py`) and expects the agent loop in `src/agent_loop.py` to parse and dispatch tool calls. If Albert's tools use a different format or dispatch mechanism, one registry would need to be adapted to the other's calling convention before the two tool sets can coexist in the same inference loop.

---

## 6. Uncertain Items (flagged, not analyzed)

| Item | Backing files | Note |
|---|---|---|
| **Brain** (sidebar) | `routes/memory_routes.py`, `src/memory.py`, `services/memory/memory_extractor.py`, `services/memory/skills.py`; frontend `static/js/skills.js` | Modal with "Memories" and "Skills" tabs; see Section 4 |
| **Cookbook** (sidebar) | `routes/cookbook_routes.py`, `/cookbook` page served in `app.py`; frontend `static/js/cookbook.js` and ~6 supporting JS files | Model download, local model serve lifecycle |
| **Tasks** (rail icon + sidebar) | `routes/task_routes.py`, `routes/assistant_routes.py`, `src/task_scheduler.py`, `src/bg_jobs.py`; frontend `static/js/tasks.js` | Scheduled tasks + per-user personal assistant |
| **Tools** (sidebar section) | Not a single backing file — it is a navigation list linking to Brain, Calendar, Compare, Cookbook, Deep Research, Gallery, Notes; no dedicated route | |
| **services/search/** | 18 files across `services/search/` and `src/search/` (core.py, providers.py, query.py, ranking.py, cache.py, content.py, analytics.py) | Possible future physics-literature research use, not decided yet |
| **services/research/** | 6 files (research_handler.py, service.py); backed by `routes/research_routes.py` | Deep-research pipeline (multi-step web search + synthesis); possible future physics-literature research use, not decided yet |

---

## 7. Excluded Items (confirmation)

All were found and skipped.

| Category | Confirmed present |
|---|---|
| Email | `routes/email_routes.py`, `routes/email_helpers.py`, `routes/email_pollers.py`, `scripts/demo_email/`, `data/mail-attachments/`, `mcp_servers/email_server.py` |
| Calendar | `routes/calendar_routes.py`, `src/caldav_sync.py`, `src/caldav_writeback.py` |
| Compare | `routes/compare_routes.py`, `static/js/compare/` |
| Gallery | `routes/gallery_routes.py`, `routes/gallery_helpers.py`, `data/generated_images/` |
| TTS / STT | `services/tts/`, `services/stt/`, `routes/tts_routes.py`, `routes/stt_routes.py`, `data/tts_cache/` |
| Faces / hwfit / youtube | `services/faces/`, `services/hwfit/`, `services/youtube/`, `routes/hwfit_routes.py` |
| Misc routes | `routes/signature_routes.py`, `routes/vault_routes.py`, `routes/copilot_routes.py`, `routes/device_flow.py`, `routes/diagnostics_routes.py`, `routes/emoji_routes.py`, `routes/font_routes.py` |
| GPU AMD compose | `docker-compose.gpu-amd.yml` (filename differs from `gpu.amd.yml` in the brief — same file) |
| Licenses / docker / tests | `licenses/`, `docker/`, `tests/` |
