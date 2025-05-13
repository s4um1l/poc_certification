FROM ghcr.io/astral-sh/uv:python3.12-bookworm

# Switch to root to install system dependencies
USER root 

# Install system dependencies required for pygraphviz and potentially other packages
# - build-essential provides gcc and other compilation tools
# - graphviz-dev provides the development headers for graphviz
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    graphviz-dev \
    && rm -rf /var/lib/apt/lists/*

# Add non-root user for security
RUN useradd -m -u 1000 app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    HOME=/home/app \
    PATH=/home/app/.local/bin:$PATH \
    PORT=8000 \
    HOST=0.0.0.0

USER app
WORKDIR $HOME/app

# Copy project definition and lock file first to leverage Docker cache
# Ensure uv.lock is committed to your repository in the 'backend' directory.
COPY --chown=app:app pyproject.toml uv.lock* ./
# If uv.lock is named differently or in a subdirectory, adjust the path.

# Install dependencies using uv
RUN uv sync --frozen

# Copy the rest of the application
COPY --chown=app:app . .

# Generate synthetic data directory
RUN mkdir -p $HOME/app/data

# Expose the port the app runs on. Railway will use this or its own $PORT.
EXPOSE ${PORT}

# Run data generation on startup and then start the server
CMD uv run python data_generator.py && uv run uvicorn main:app --host ${HOST} --port ${PORT} 