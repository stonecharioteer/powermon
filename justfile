# PowerMon - Power Monitoring Application

# Show available commands
help:
    @just --list

# Install dependencies with uv
install:
    uv sync

# Run development servers locally
dev:
    @echo "Starting development environment..."
    @echo "Make sure PostgreSQL and Redis are running locally"
    @echo "Run in separate terminals:"
    @echo "  Terminal 1: just dev-run"
    @echo "  Terminal 2: just dev-dashboard"
    @echo "  Terminal 3: just dev-worker"
    @echo "  Terminal 4: just dev-beat"

# Build Docker images
build:
    docker-compose build

# Force rebuild Docker images without cache
rebuild:
    docker-compose build --no-cache

# Start all services with Docker Compose
up:
    docker-compose up -d

# Stop all services
down:
    docker-compose down

# View logs from all services
logs:
    docker-compose logs -f

# View web service logs
logs-web:
    docker-compose logs -f web

# View celery worker logs
logs-celery:
    docker-compose logs -f celery_worker

# Open a shell in the web container
shell:
    docker-compose exec web /bin/bash

# Connect to PostgreSQL database
psql:
    docker-compose exec postgres psql -U powermon -d powermon

# Connect to Redis
redis-cli:
    docker-compose exec redis redis-cli

# Run tests (if any)
test:
    uv run python -m pytest tests/ -v

# Clean up containers and volumes
clean:
    docker-compose down -v
    docker system prune -f

# Initialize database with tables
init-db:
    docker-compose exec web python manage.py init-db

# Add a switch (usage: just add-switch MyLabel 192.168.1.100)
add-switch label ip:
    docker-compose exec web python manage.py add-switch {{label}} {{ip}}

# List all switches
list-switches:
    docker-compose exec web python manage.py list-switches

# Test connectivity to all switches
test-switches:
    docker-compose exec web python manage.py test-switches

# Show system statistics
show-stats:
    docker-compose exec web python manage.py show-stats

# Open Celery Flower monitoring (http://localhost:5555)
flower:
    @echo "Opening Celery Flower at http://localhost:5555"
    @open http://localhost:5555 2>/dev/null || xdg-open http://localhost:5555 2>/dev/null || echo "Please open http://localhost:5555 in your browser"

# Open Flask web interface and dashboard (http://localhost:8000)
web:
    @echo "Opening PowerMon Dashboard at http://localhost:8000"
    @open http://localhost:8000 2>/dev/null || xdg-open http://localhost:8000 2>/dev/null || echo "Please open http://localhost:8000 in your browser"

# Development shortcuts
dev-install: install

# Run development server only
dev-run:
    uv run python run.py

# Run celery worker only
dev-worker:
    uv run celery -A app.celery worker --loglevel=info

# Run celery beat only
dev-beat:
    uv run celery -A app.celery beat --loglevel=info

# Format code with ruff
format:
    uv run ruff format .

# Check code with ruff
lint:
    uv run ruff check .

# Fix code issues with ruff
lint-fix:
    uv run ruff check --fix .

# Run full code quality checks
check: lint format

# Clean up old power check data (usage: just cleanup-data 7)
cleanup-data days="7":
    docker-compose exec web python manage.py cleanup-data --days {{days}}

# Remove a switch by ID (usage: just remove-switch 1)
remove-switch id:
    docker-compose exec web python manage.py remove-switch {{id}}

# Remove a switch by name (usage: just rm-switch "MySwitch")
rm-switch name:
    docker-compose exec web python manage.py rm-switch {{name}}

# Show container status
status:
    docker-compose ps

# Restart specific service (usage: just restart web)
restart service:
    docker-compose restart {{service}}

# View resource usage
stats:
    docker stats