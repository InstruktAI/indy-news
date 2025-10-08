#!/usr/bin/env sh
if [ -n "$SVC_COOKIES" ]; then
  cookies_dir="${CACHE}cookies"
  files=$(find "$cookies_dir" -type f | wc -l)
  # check if cookies exist:
  if [ ! "$files" -eq 0 ]; then
    echo "$SVC_COOKIES" >"${cookies_dir}/$(date +%Y-%m-%d_%H-%M-%S).txt"
  fi
fi
.venv/bin/uvicorn api.main:app --port 8080 --host 0.0.0.0
