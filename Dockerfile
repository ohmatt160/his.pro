# Use Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV APP_ENV=production
ENV PORT=7860
ENV WEB_CONCURRENCY=1
ENV DATABASE_URL=sqlite:////data/hispro.db

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy project (includes built static files in app/static)
COPY . .

# Create runtime data directories. On Hugging Face Spaces, enable persistent
# storage so /data survives rebuilds and restarts.
RUN mkdir -p /data uploads

# Expose port
EXPOSE 7860

# Run the application with gunicorn
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-7860} --workers ${WEB_CONCURRENCY:-1} --worker-class uvicorn.workers.UvicornWorker --timeout 120 app.main:app"]
