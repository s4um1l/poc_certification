FROM ghcr.io/astral-sh/uv:python3.11-slim

# Add non-root user for security
RUN useradd -m -u 1000 app
USER app

# Set environment variables
ENV HOME=/home/app \
    PATH=/home/app/.local/bin:$PATH \
    PORT=8000 \
    HOST=0.0.0.0

# Set the working directory
WORKDIR $HOME/app

# Copy the pyproject.toml file
COPY --chown=app pyproject.toml .

# Install dependencies using uv
RUN uv sync --frozen

# Copy the rest of the application
COPY --chown=app . .

# Generate synthetic data directory
RUN mkdir -p $HOME/app/data

# Run data generation on startup and then start the server
CMD uv run python data_generator.py && uv run uvicorn main:app --host ${HOST} --port ${PORT} 