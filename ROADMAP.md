# Roadmap

This roadmap keeps the project honest: it is a working thesis prototype with a clear path toward a more reusable open-source reference project.

## v0.1.0 Thesis Prototype

- FastAPI backend with streaming chat API.
- PortableRAGV4 integrated into the platform.
- React + Vite frontend with Live2D model switching.
- edge-tts speech generation and mouth cue headers.
- AIRI-inspired audio queue, lip sync, motion, idle, blink, and debug panel.
- Offline RAG evaluation reports and final local acceptance record.

## v0.2.0 Reproducibility

- Add backend dependency lock or installation script.
- Add one-command smoke test for backend status, RAG retrieval, and frontend build.
- Document how to replace the campus corpus with a new document collection.
- Add smaller sample corpus for quick demos.
- Add troubleshooting notes for common API rate-limit and TTS failures.

## v0.3.0 Safety and Evaluation

- Improve negative-question refusal and real-time boundary handling.
- Add prompt-injection test cases for RAG.
- Compare offline annotation with sampled LLM judge results.
- Add security checklist for API keys, CORS, dependencies, and third-party assets.
- Publish an evaluation summary table after each major RAG change.

## v0.4.0 Open-Source Polish

- Add release artifacts and screenshots.
- Add issue templates and project labels.
- Improve Live2D asset license documentation.
- Add architecture diagrams to the README.
- Split thesis-only materials from reusable project docs where appropriate.
