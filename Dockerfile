FROM python:3.12 as base
WORKDIR /app
COPY requirements.txt /app/
RUN python -m venv .venv
ENV NEEDRESTART_MODE=l
RUN .venv/bin/pip install --no-cache-dir -r requirements.txt

FROM base as ci
RUN .venv/bin/pip install --no-cache-dir -r requirements-test.txt

FROM ci as test
COPY . /app
RUN make lint && make test

FROM python:3.12-slim
WORKDIR /app
COPY --from=base /app /app
COPY . /app

CMD ["./start.sh"]