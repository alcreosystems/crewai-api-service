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

# Install CrewAI CLI first
RUN pip install --no-cache-dir crewai

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire CrewAI project
COPY . .

# Install project dependencies
RUN crewai install

# Expose port for FastAPI
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run the FastAPI wrapper
CMD ["python", "api_server.py"]
