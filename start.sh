#!/usr/bin/env sh
[ -n "$X_JSON" ] && cat "$X_JSON" >${CACHE}cookies.json
.venv/bin/uvicorn api.main:app --port 8080 --host 0.0.0.0
