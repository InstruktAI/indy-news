FROM python:3.11 as base
WORKDIR /app
COPY requirements-prod.txt /app/
RUN python -m venv .venv
RUN .venv/bin/pip install --no-cache-dir -r requirements-prod.txt

FROM base as ci
RUN .venv/bin/pip install --no-cache-dir -r requirements-test.txt

FROM ci as test
COPY . /app
RUN bin/format.sh && bin/lint.sh

FROM python:3.11-alpine
WORKDIR /app
COPY --from=base /app /app
COPY . /app
CMD [".venv/bin/uvicorn", "api.main:app", "--port", "8080", "--host", "0.0.0.0"]