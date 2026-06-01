# Contributing

Thanks for taking a look at this project. AIRI Digital Human Assistant is currently a thesis prototype, so contributions that improve reproducibility, safety, documentation, and evaluation are especially valuable.

## Good First Areas

- Improve setup instructions for Windows, Linux, or macOS.
- Add smoke tests for backend API endpoints or RAG evaluation commands.
- Improve negative-question refusal and out-of-scope handling.
- Add documentation for adding new corpora or Live2D models.
- Report unclear third-party asset or license boundaries.
- Improve frontend accessibility, loading states, and error messages.

## Development Setup

Copy the environment template:

```powershell
Copy-Item .env.example .env
```

Start backend:

```powershell
.\scripts\run_backend.ps1
```

Start frontend:

```powershell
.\scripts\run_frontend.ps1
```

Run frontend checks:

```powershell
Set-Location frontend
npm run lint
npm run build
```

Run Python syntax checks:

```powershell
.\venv\Scripts\python.exe -m compileall backend experiments\rag_reproduction\raglab
```

## Pull Request Guidelines

- Keep changes focused and explain the motivation.
- Do not commit `.env`, API keys, local caches, generated indexes, or private data.
- If you modify RAG behavior, include a small reproduction command or evaluation note.
- If you add assets or third-party code, document the source and license.
- Prefer clear documentation over broad rewrites.

## Issue Guidelines

When reporting a bug, include:

- OS and shell.
- Python and Node.js versions.
- Backend or frontend command used.
- Relevant logs, with API keys removed.
- A minimal question or corpus example if the issue is RAG-related.
