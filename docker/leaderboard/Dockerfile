FROM python:3.12.10-slim

RUN groupadd --gid 1001 aobench \
 && useradd --uid 1001 --gid aobench --no-create-home --shell /bin/false aobench

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_NO_CACHE=1

RUN pip install --no-cache-dir "uv==0.11.8"

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev --extra leaderboard --no-install-project

COPY src/ ./src/

RUN uv sync --frozen --no-dev --extra leaderboard

RUN mkdir -p data/leaderboard && chown -R aobench:aobench data/

USER aobench

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
  CMD ["/usr/local/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]

CMD ["/app/.venv/bin/uvicorn", "aobench.leaderboard.api:app", \
     "--host", "0.0.0.0", "--port", "8000"]
