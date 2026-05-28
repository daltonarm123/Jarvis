# Jarvis runtime image
FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source and install package
COPY src/ ./src/
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir -e .

# Non-root user
RUN useradd --create-home --shell /bin/bash jarvis \
    && mkdir -p /app/logs /app/data \
    && chown -R jarvis:jarvis /app
USER jarvis

# Secrets are provided at runtime via env_file or env vars — NOT baked in.
# Override JARVIS_MODE etc. via docker-compose / docker run -e ...

CMD ["python", "-m", "jarvis.main"]
