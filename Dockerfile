# Use Python 3.14 slim image
FROM python:3.14-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies directly using pip (simpler for Docker)
RUN pip install --no-cache-dir \
    celery>=5.6.0 \
    dash>=3.3.0 \
    flask>=3.1.2 \
    flask-sqlalchemy>=3.1.1 \
    flower>=2.0.1 \
    gunicorn>=23.0.0 \
    plotly>=6.5.0 \
    psycopg[binary]>=3.3.2 \
    python-dotenv>=1.2.1 \
    redis>=7.1.0 \
    requests>=2.32.5 \
    sqlalchemy>=2.0.45 \
    numpy \
    pandas

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Expose port
EXPOSE 56957

# Default command (can be overridden in docker-compose)
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:56957", "app:create_app()"]