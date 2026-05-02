FROM python:3.12.10-slim

RUN groupadd --gid 1001 exabench \
 && useradd --uid 1001 --gid exabench --no-create-home --shell /bin/false exabench

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_NO_CACHE=1 \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir "uv==0.11.8"

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev --extra openai --extra anthropic --no-install-project

COPY src/ ./src/
COPY benchmark/ ./benchmark/

RUN uv sync --frozen --no-dev --extra openai --extra anthropic

RUN chown -R exabench:exabench /app

USER exabench

ENTRYPOINT ["/app/.venv/bin/exabench"]
CMD ["--help"]
