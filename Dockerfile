# Use Python 3.11 Alpine - matches CrewAI requirements
FROM python:3.11-alpine3.22

# Set working directory
WORKDIR /app

# Install system dependencies for CrewAI
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    cargo \
    rust \
    git

# Copy project files
COPY pyproject.toml ./

# Install the project and its dependencies
RUN pip install --no-cache-dir -e .

# Copy the entire CrewAI project
COPY . .

# Expose port for FastAPI
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run the FastAPI wrapper
CMD ["python", "api_server.py"]
