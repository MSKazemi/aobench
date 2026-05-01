FROM python:3.11-slim

WORKDIR /app

# System deps for pandas/pyarrow
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency resolution
RUN pip install --no-cache-dir uv

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install with OpenAI + Anthropic extras (MCP and Langfuse are optional)
RUN uv sync --frozen --extra openai --extra anthropic

# Copy source and benchmark data
COPY src/ ./src/
COPY benchmark/ ./benchmark/

# Install the package in editable mode
RUN uv pip install -e . --no-deps

# Runtime environment (override with --env or .env mount)
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["uv", "run", "exabench"]
CMD ["--help"]
