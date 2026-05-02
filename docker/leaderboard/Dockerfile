FROM python:3.12-slim

# Non-root user for security
RUN groupadd --gid 1001 exabench \
 && useradd --uid 1001 --gid exabench --no-create-home --shell /bin/false exabench

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_NO_CACHE=1

# Install uv (latest stable; reproducibility comes from uv.lock for Python deps)
RUN pip install --no-cache-dir uv

# Copy manifests first — layer is cached unless deps change
COPY pyproject.toml uv.lock ./

# Install only the leaderboard extra (fastapi + uvicorn + base deps); skip dev tools
# --no-install-project defers the editable install until src/ is present
RUN uv sync --frozen --no-dev --extra leaderboard --no-install-project

# Copy source
COPY src/ ./src/

# Install package into the already-resolved venv without re-solving deps
RUN uv sync --frozen --no-dev --extra leaderboard

# Ensure data directory exists and is owned by the non-root user
RUN mkdir -p data/leaderboard && chown -R exabench:exabench data/

USER exabench

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
  CMD ["/usr/local/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]

CMD ["/app/.venv/bin/uvicorn", "exabench.leaderboard.api:app", \
     "--host", "0.0.0.0", "--port", "8000"]
