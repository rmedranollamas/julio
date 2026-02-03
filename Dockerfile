FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install python dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# Copy source code
COPY . .

# Create skills directory
RUN mkdir -p /skills

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

# Command to run the agent
CMD ["uv", "run", "python", "main.py"]
