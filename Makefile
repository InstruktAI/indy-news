.PHONY: help install install-dev format lint test run streamlit clean docker-build docker-run

PYTHON := .venv/bin/python
PIP := .venv/bin/pip
PYTEST := .venv/bin/pytest
ISORT := .venv/bin/isort
BLACK := .venv/bin/black
RUFF := .venv/bin/ruff
PYLINT := .venv/bin/pylint
MYPY := .venv/bin/mypy
UVICORN := .venv/bin/uvicorn
STREAMLIT := .venv/bin/streamlit

help:
	@echo "Available targets:"
	@echo "  install        - Create venv and install production dependencies"
	@echo "  install-dev    - Install development and test dependencies"
	@echo "  format         - Format code with isort and black"
	@echo "  lint           - Run pylint and mypy type checking"
	@echo "  test           - Run pytest test suite"
	@echo "  run            - Start FastAPI server on port 8088"
	@echo "  streamlit      - Start StreamLit interface"
	@echo "  clean          - Remove cache files and build artifacts"
	@echo "  docker-build   - Build Docker image"
	@echo "  docker-run     - Run Docker container"

install:
	python -m venv .venv
	$(PIP) install -r requirements.txt

install-dev: install
	$(PIP) install -r requirements-test.txt

format:
	$(RUFF) check --fix api lib pages
	$(ISORT) api lib pages
	$(BLACK) api lib pages

lint:
	$(RUFF) check api lib pages
	$(PYLINT) api lib pages
	$(MYPY) api lib pages

test:
	$(PYTEST) tests/

run:
	$(UVICORN) api.main:app --host "0.0.0.0" --port 8088

streamlit:
	$(STREAMLIT) run Home.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf data/combined.json

docker-build:
	docker build -t indy-news .

docker-run:
	docker run -p 8088:8088 --env-file .env indy-news
