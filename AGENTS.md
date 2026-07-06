# AGENTS.md — Portfolio Website

Plain HTML, CSS (Tailwind via CDN), JS portfolio site showcasing AI/data science projects. Static site deployable to Netlify.

## Development

- **No framework** — vanilla HTML, Tailwind CSS (CDN), vanilla JS
- **Tailwind**: included via `<script src="https://cdn.tailwindcss.com"></script>` in each HTML page
- **Dev server**: `.\serve.ps1` (Windows) or `python -m http.server 8000` — serves on `http://localhost:8000`
- **No build step** — no bundler, transpiler, or codegen
- **No package.json, no node_modules** — keep the repo dependency-free
- **Must serve via HTTP** — opening `index.html` directly via `file://` breaks CORS requests in the chatbot

## SQL AI Assistant (Backend-Heavy Project)

The SQL AI Assistant at `projects/sql-ai-assistant/` is the only project with a real backend (FastAPI + SQLite + Ollama).

### Backend (`backend/`)
- **api.py**: FastAPI routes — upload-db, schema, tables, query, history, export, health. Also serves frontend static files as fallback mount.
- **database.py**: SQLite operations — schema reader, query executor, upload management, `uploads/` directory for .db files.
- **llm.py**: Ollama HTTP client with async httpx, configurable base URL / model / headers via env vars.
- **sql_agent.py**: SQL generation via LLM, safety validation (SELECT-only), chart type detection, sample question generation.
- **models.py**: Pydantic models for request/response.
- **prompt.py**: LLM prompt templates (system prompt with schema, explanation, sample questions).
- **utils.py**: Logging setup, timing decorator, safe SQL identifier quoting.

### Frontend (`frontend/`)
- **index.html**: Dashboard layout — top bar, sidebar (DB info, sample questions, history), message area, input bar, upload modal.
- **app.js**: API client, message rendering, results table, Chart.js integration, export handlers, upload flow, history management.

### Dev
```bash
cd projects/sql-ai-assistant/backend
pip install -r ../requirements.txt
uvicorn api:app --reload --port 8000
# Open http://localhost:8000
```

### Docker
```bash
cd projects/sql-ai-assistant
docker compose up -d
# Open http://localhost:8000
```

### Notes
- Only SELECT queries are allowed — safety validator in `sql_agent.py:validate_sql()` rejects DELETE, DROP, UPDATE, INSERT, ALTER, CREATE.
- Chart.js is loaded via CDN. Charts auto-detect type (pie ≤6 unique labels, bar ≤20, line otherwise).
- History is in-memory only (resets on server restart). Max 50 items.

## Project Structure

```
/
├── index.html                  # Portfolio landing page
├── serve.ps1                   # Dev server launcher (Windows)
├── netlify.toml                # Netlify deploy config with CORS headers
├── projects/
│   ├── ai-chatbot/
│   │   ├── index.html          # Working chatbot (Ollama frontend)
│   │   └── screenshots/        # Project images
│   ├── pdf-chat-rag/           # RAG over PDF documents
│   ├── resume-analyzer/        # AI resume analysis
│   ├── ocr-reader/             # Image text extraction
│   ├── sentiment-analysis/     # Text sentiment classification
│   └── sql-ai-assistant/       # SQL AI Assistant (FastAPI + SQLite + Ollama)
│       ├── index.html          # Project description page
│       ├── backend/            # FastAPI backend
│       ├── frontend/           # Dashboard HTML + JS
│       ├── Dockerfile
│       ├── docker-compose.yml
│       ├── requirements.txt
│       ├── .env.example
│       └── README.md
├── css/                        # Custom styles beyond Tailwind
├── js/                         # Shared scripts
```

## Conventions

- Every project page is a standalone HTML file — no SPA routing
- Clicking a project on the landing page navigates to `projects/project-name/`
- Use Tailwind utility classes directly in HTML; avoid custom CSS unless necessary
- Screenshots go in a `screenshots/` folder inside each project directory
- No build tooling, no package manager — keep it zero-config

## Chatbot / Ollama

- The chatbot at `projects/ai-chatbot/` connects to an Ollama API endpoint (configurable via ⚙️ Settings in the UI)
- Endpoint, custom headers (e.g. `ngrok-skip-browser-warning`), and model list are persisted in `localStorage`
- If the API is behind ngrok, the instance needs `OLLAMA_ORIGINS=*` to allow browser CORS requests
- Click "Test Connection" in Settings to verify endpoint before chatting

## Architectural Diagrams

- **All architecture sections use Mermaid.js** (via CDN) for diagram rendering — no ASCII art, no draw.io
- Mermaid is loaded from `https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js` in each project page
- Dark theme initialized with `mermaid.initialize({theme:'dark',themeVariables:{...}})`
- Styles use the slate/purple palette matching the portfolio's Tailwind dark theme
- README.md diagrams use native GitHub Mermaid rendering (fenced code blocks with ````mermaid`)
- When adding a new project, include both the Mermaid CDN `<script>` tag and a `mermaid.initialize()` call in `<head>`

## Deployment (Netlify)

- Connect repo to Netlify; publish directory: `/`
- **No build command** — deploy the static files as-is
- `netlify.toml` sets `Access-Control-Allow-Origin: *` for chatbot API access from the deployed site

## Future Updates

Update this file when adding:
- new project directories (note the expected structure)
- any build tooling or config
- deployment changes
