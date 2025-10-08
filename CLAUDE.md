# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Indy News is a FastAPI-based service that aggregates content from independent media outlets across multiple platforms (YouTube, X/Twitter, Substack). It provides curated news sources with bias ratings from AllSides and MediaBiasFactCheck databases.

## Development Setup

### Environment Setup

1. Create and activate virtual environment:

```bash
python -m venv .venv
. .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. For development (includes test dependencies):

```bash
pip install -r requirements-test.txt
```

### Running the Application

**FastAPI server:**

```bash
.venv/bin/uvicorn api.main:app --host "0.0.0.0" --port 8088
```

**StreamLit interface:**

```bash
.venv/bin/streamlit run Home.py
```

**Production (using start.sh):**

```bash
./start.sh
```

### Development Commands

**Format code:**

```bash
bin/format.sh
```

Runs `isort` and `black` on `api`, `lib`, and `pages` directories.

**Lint code:**

```bash
bin/lint.sh
```

Runs `pylint` and `mypy` type checking.

**Run tests:**

```bash
bin/test.sh
```

Runs pytest test suite.

### Docker

Build and test workflow defined in `Dockerfile` with multi-stage builds:

- `base`: Python 3.12 with production dependencies
- `ci`: Adds test dependencies
- `test`: Runs format, lint, and test checks
- Final slim image for production

## Architecture

### API Endpoints (`api/main.py`)

All endpoints require API key authentication via query param `apikey`, header `X-API-KEY`, or Bearer token.

**Core content search endpoints:**

- `/youtube` - Search YouTube videos by channels and/or query with transcript support
- `/x` - Search X/Twitter tweets by users and/or query
- `/substack` - Search Substack posts by publications and/or query
- `/news` - Combined YouTube and X search

**Data source endpoints:**

- `/sources` - List all curated sources (names, about, topics)
- `/source-media` - Get YouTube/X/Substack handles for sources
- `/media` - Search curated independent media database
- `/allsides` - Query AllSides bias ratings database
- `/mediabiasfactcheck` - Query MediaBiasFactCheck database

### Data Layer (`api/store.py`)

Manages three data sources in `data/` directory:

- `all.csv` - Curated independent media sources
- `allsides.com.json` - AllSides bias ratings snapshot
- `mediabiasfactcheck.com.json` - MediaBiasFactCheck ratings snapshot
- `combined.json` - Runtime-generated merged dataset (cached)

The `get_data()` function merges CSV with bias/factual ratings and caches to `data/combined.json`.

### Platform Integrations

**X/Twitter (`api/x.py`):**

- Uses `twikit` client with cookie-based authentication
- Cookies managed via `CookieManager` in `lib/cookie_manager.py`
- Cookies stored in timestamped files in `cookies/` directory
- Auto-refresh when cookies are >29 days old
- Fallback to `SVC_COOKIES` env var for static cookie string

**YouTube (`api/youtube.py`):**

- Uses `youtube-transcript-api` for transcript extraction
- Supports channel-based search with date filtering

**Substack (`api/substack.py`):**

- Uses `substack-api` library for post search

### Authentication (`lib/auth.py`)

API key verification supports three methods:

- Query parameter: `?apikey=xxx`
- Header: `X-API-KEY: xxx`
- Bearer token: `Authorization: Bearer xxx`

Validates against `API_KEY` environment variable.

### Cookie Management (`lib/cookie_manager.py`)

Manages X/Twitter authentication cookies:

- Stores cookies in timestamped files: `cookies/YYYY-MM-DD_HH-MM-SS.txt`
- Auto-detects cookie age and triggers refresh when >29 days old
- Integrates with external playwright service for cookie refresh
- Provides `get_valid_cookies()` to automatically handle refresh logic

## Environment Variables

Required:

- `API_KEY` - API authentication key

Optional:

- `LOG_LEVEL` - Logging level (default: INFO)
- `CACHE` - Cache directory path
- `SVC_JSON` - Path to X cookies JSON file (used by start.sh)
- `SVC_COOKIES` - Static cookie string fallback

## Code Quality

- Python 3.11+ required
- Type hints enforced with mypy
- Code formatting: black (line length 88) + isort
- Linting: pylint with custom rules in `pyproject.toml`
- Pydantic models for all API request/response schemas
