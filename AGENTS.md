# Repository Guidelines

## Project Structure & Module Organization

Core application code lives in `src/gf_mobile/`. Use `core/` for configuration, auth, and shared exceptions; `persistence/` for SQLite and SQLAlchemy models; `services/` for business workflows; `sync/` for Firestore synchronization; and `ui/screens/` plus `ui/widgets/` for Kivy/KivyMD presentation. Keep automated tests in `tests/`, static assets in `assets/`, and design or sync notes in `docs/`. Utility scripts belong in `scripts/` or `tools/`.

## Build, Test, and Development Commands

Create a virtual environment with `python -m venv .venv`, then activate it with `.\.venv\Scripts\Activate.ps1` on Windows. Install runtime dependencies with `pip install -r requirements.txt` or developer tools with `pip install -e ".[dev]"`. Run the app locally with `python -m gf_mobile.main` or `.\run_app.bat`. Execute the full test suite with `pytest`, generate coverage with `pytest --cov=src/gf_mobile --cov-report=html`, and run focused sync checks with `pytest tests/test_sync_protocol.py -v`.

## Coding Style & Naming Conventions

Target Python 3.10+ and use 4-space indentation. Prefer explicit type hints on new or modified code. Format with `black` using a 100-character line length and sort imports with `isort` using the Black profile; `ruff` and `mypy` are available for additional checks. Follow existing naming patterns: modules and functions use `snake_case`, classes use `PascalCase`, and screen or service classes should be named clearly, such as `DashboardScreen` or `TransactionService`.

## Testing Guidelines

This repository uses `pytest` with `pytest-asyncio`. Place tests under `tests/` and name files `test_*.py`; group related behavior in `Test...` classes when useful. Keep unit tests close to service and sync changes, and add regression coverage for UI theme, responsive behavior, or gesture handling when those areas change. Respect the strict pytest configuration in `pytest.ini` and keep async tests marked appropriately.

## Commit & Pull Request Guidelines

Recent history uses short imperative commit messages with prefixes such as `feat:`, `fix:`, and `refactor:`; continue that pattern. Pull requests should summarize the user-visible change, list the main areas touched (for example `ui`, `sync`, or `services`), link the related issue or task, and include screenshots or short recordings for UI work. Always note the test commands you ran before requesting review.

## Security & Configuration Tips

Do not commit secrets from `.env`; use `.env.example` as the template for Firebase and local configuration. Validate sync-related changes against the Firestore docs in `docs/` before merging. Keep environment-specific database paths and credentials configurable rather than hardcoded.
