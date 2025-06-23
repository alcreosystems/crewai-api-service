# Use Python 3.11 Debian - better package compatibility than Alpine
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for CrewAI
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    libffi-dev \
    libssl-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install CrewAI and dependencies directly (without tools to avoid conflicts)
RUN pip install --no-cache-dir \
    "crewai==0.85.0" \
    "fastapi>=0.104.1" \
    "uvicorn[standard]>=0.24.0" \
    "python-multipart>=0.0.6" \
    "python-dotenv>=1.0.0"

# Copy the entire project
COPY . .

# Set Python path to include our source directory
ENV PYTHONPATH=/app:/app/marketing_strategy:/app/marketing_strategy/src

# Expose port for FastAPI
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run the FastAPI wrapper
CMD ["python", "api_server.py"]
