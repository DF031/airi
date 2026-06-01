# Security Policy

This project is a research and thesis prototype, not a production service. Security reports and hardening suggestions are welcome.

## Supported Versions

Only the latest `main` branch is maintained.

## Reporting a Vulnerability

Please open a GitHub issue if the report does not contain sensitive exploit details. For sensitive issues, contact the repository owner through GitHub profile contact methods if available.

Do not include real API keys, private documents, personal data, or undisclosed vulnerability details in a public issue.

## Security Areas of Interest

- Accidental API key or `.env` leakage.
- Unsafe CORS or backend API behavior.
- Path traversal or unsafe file handling.
- Dependency vulnerabilities.
- Prompt injection or RAG data exfiltration.
- Privacy boundary failures in campus or user data.
- Unsafe handling of third-party Live2D assets or source snapshots.
- Frontend resource loading issues.

## Current Notes

- `.env` is ignored by Git and `.env.example` contains empty placeholders only.
- The default backend is intended for local development on `127.0.0.1`.
- RAG evaluation data should avoid private or personally sensitive content.
- Third-party assets remain under their original licenses and should be reviewed before redistribution.
