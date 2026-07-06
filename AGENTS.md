# AGENTS.md — Portfolio Website

Plain HTML, CSS (Tailwind via CDN), JS portfolio site showcasing AI/data science projects. Static site deployable to Netlify.

## Development

- **No framework** — vanilla HTML, Tailwind CSS (CDN), vanilla JS
- **Tailwind**: included via `<script src="https://cdn.tailwindcss.com"></script>` in each HTML page
- **Dev server**: `.\serve.ps1` (Windows) or `python -m http.server 8000` — serves on `http://localhost:8000`
- **No build step** — no bundler, transpiler, or codegen
- **No package.json, no node_modules** — keep the repo dependency-free
- **Must serve via HTTP** — opening `index.html` directly via `file://` breaks CORS requests in the chatbot

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
│   └── sentiment-analysis/     # Text sentiment classification
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

## Deployment (Netlify)

- Connect repo to Netlify; publish directory: `/`
- **No build command** — deploy the static files as-is
- `netlify.toml` sets `Access-Control-Allow-Origin: *` for chatbot API access from the deployed site

## Future Updates

Update this file when adding:
- new project directories (note the expected structure)
- any build tooling or config
- deployment changes
