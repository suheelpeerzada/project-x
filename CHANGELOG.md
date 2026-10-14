# Changelog

All notable changes to Project-X are listed here.

## [0.9.2-alpha] - 2026-10-14

First public pre-release.

### Added
- Multi-model registry with switching and per-model key verification.
- Live model list for Groq and OpenAI.
- Custom OpenAI-compatible endpoints with a base URL.
- Streaming chat replies with Markdown and LaTeX rendering.
- Local chat history (SQLite) shared across all models in a conversation.
- API keys stored in the OS keychain.
- `start.bat` / `start.sh` scripts and a setup guide.

### Fixed
- Model list not appearing after entering a key (route registration in `providers.py`).
- Raw JSON and broken symbols in replies, and models not sharing context
  (`/chat/stream` was served by the legacy handler in `chat.py`).
- Model picker now shows an error instead of failing silently on a bad response.
- A 401 during verification now re-syncs the lock reason.

### Known issues
See the release notes.
