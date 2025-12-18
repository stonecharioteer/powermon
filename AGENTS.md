# PowerMon - Agent Guide

This document provides essential information for AI agents working on the PowerMon power outage monitoring application.

## Project Overview

PowerMon is a Flask-based application that monitors smart switches to detect power outages. It uses:
- **Flask** for the web API and management interface
- **Dash/Plotly** for data visualization dashboard
- **PostgreSQL** for data storage
- **Celery** for background task processing
- **Redis** for caching and message broker
- **Docker Compose** for orchestration

## Architecture

```
PowerMon/
├── app/                    # Main Flask application
│   ├── __init__.py        # App factory, Celery setup
│   ├── models.py          # Database models (SQLAlchemy)
│   ├── tasks.py           # Celery background tasks
│   ├── main/              # Main web routes
│   ├── api/               # REST API endpoints
│   └── services/          # Business logic
│       └── switch_monitor.py  # Core monitoring logic
├── dashboard.py           # Dash visualization app
├── manage.py              # CLI management commands
├── run.py                 # Development server entry point
├── docker-compose.yml     # Container orchestration
├── Dockerfile             # Multi-stage build
└── justfile               # Development shortcuts
```

## Essential Commands

### Package Management (uv)
```bash
uv sync                    # Install/sync dependencies
uv add package-name        # Add new dependency
uv remove package-name     # Remove dependency
```

### Docker Development (just)
```bash
just build                 # Build Docker images
just up                    # Start all services
just down                  # Stop all services
just logs                  # View all logs
just shell                 # Shell into web container
just init-db               # Initialize database
```

### Local Development
```bash
just dev-run               # Run Flask app (port 56957)
just dev-dashboard         # Run Dash app (port 8050)
just dev-worker            # Run Celery worker
just dev-beat              # Run Celery scheduler
```

### Database Management
```bash
python manage.py init-db           # Create database tables
python manage.py add-switch NAME IP
python manage.py list-switches     # List all switches
python manage.py test-switches     # Test connectivity
python manage.py show-stats        # System statistics
```

### Service URLs
- **Web Interface**: http://localhost:56957 (NOTE: Changed from 5000)
- **Dash Dashboard**: http://localhost:8050
- **Celery Flower**: http://localhost:5555
- **PostgreSQL**: localhost:5432 (powermon/powermon123)
- **Redis**: localhost:6379

## Database Models

### SmartSwitch
- Represents monitored devices
- Fields: `id`, `name`, `ip_address`, `is_active`, `created_at`, `updated_at`

### PowerCheck  
- Individual connectivity checks
- Fields: `switch_id`, `is_online`, `response_time`, `error_message`, `checked_at`
- Indexed on `(switch_id, checked_at)`

### PowerOutage
- Detected power outage periods
- Fields: `started_at`, `ended_at`, `duration_seconds`, `switches_affected`, `is_ongoing`
- Automatically created/ended by monitoring logic

## Core Monitoring Logic

### Switch Monitoring (`app/services/switch_monitor.py`)
- **Primary Method**: HTTP GET requests to switch IP addresses
- **Success Criteria**: Any HTTP response (including 404) = device reachable
- **Failure Detection**: Connection timeout/refusal = device unreachable
- **Outage Logic**: >50% of switches offline = power outage

### Background Tasks (`app/tasks.py`)
- **`monitor_all_switches`**: Scheduled every 60s (configurable via `MONITOR_INTERVAL`)
- **`cleanup_old_power_checks`**: Runs daily at 2 AM, removes data >30 days old
- **`check_single_switch`**: On-demand single switch testing

## Configuration

### Environment Variables (.env)
```bash
DATABASE_URL=postgresql://powermon:powermon123@postgres:5432/powermon
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
SECRET_KEY=your-secret-key
MONITOR_INTERVAL=60                    # Seconds between checks
POWER_OUTAGE_THRESHOLD=2               # Consecutive failures before outage
SMART_SWITCHES=switch1:192.168.1.100,switch2:192.168.1.101
```

## API Endpoints

### Main Routes (`/`)
- `GET /` - Dashboard with current status
- `GET /switches` - Switch management page
- `POST /switches/add` - Add new switch
- `GET /test-switch/<id>` - Test single switch

### REST API (`/api/`)
- `GET /api/switches` - List all switches
- `GET /api/power-checks?hours=24&switch_id=1` - Power check history
- `GET /api/outages?hours=168` - Outage history
- `GET /api/status` - Comprehensive system status
- `GET /api/statistics` - System statistics

## Development Patterns

### Adding New Switch Types
1. Extend `SwitchMonitor.check_switch_status()` in `app/services/switch_monitor.py`
2. Add switch type field to `SmartSwitch` model if needed
3. Update monitoring logic to handle different protocols

### Modifying Dashboard
- Edit `dashboard.py` for Dash visualizations
- Callback functions update charts in real-time
- Data fetched from database via `get_power_data()`

### Adding Management Commands
- Add new commands to `manage.py`
- Use `@click.command()` and `@with_appcontext` decorators
- Register with `app.cli.add_command()`

## Testing & Debugging

### Testing Switches
```bash
# Test all switches
just test-switches

# Test individual switch
curl http://localhost:56957/test-switch/1
```

### Monitoring Workers
```bash
# View Celery tasks
just flower

# Check logs
just logs-celery
just logs-web
```

### Database Inspection
```bash
# Connect to PostgreSQL
just psql

# Check Redis
just redis-cli
```

## Common Issues

### Port Conflicts
- Web service runs on port **56957** (not 5000)
- If containers fail to start, check port availability

### Database Connectivity
- Ensure PostgreSQL container is healthy before starting app containers
- Use `just logs` to check for database connection errors

### Switch Detection
- Switches must respond to HTTP requests on port 80
- Any HTTP response (200, 404, etc.) indicates the switch is reachable
- Connection timeouts/refusals indicate power issues

### Celery Tasks Not Running
- Verify Redis is accessible
- Check `CELERY_BROKER_URL` matches Redis container
- Ensure Celery beat scheduler is running for periodic tasks

## Deployment Notes

- Uses multi-stage Docker builds for efficiency
- Virtual environment created in builder stage, copied to runtime
- Health checks ensure services start in correct order
- All data persisted in Docker volumes
- Commands managed through `just` (justfile) for better ergonomics
- Suitable for production with proper secret management

## Extension Points

### Custom Monitoring Protocols
- Extend `SwitchMonitor` class for SNMP, ping, or custom protocols
- Add protocol field to switch configuration

### Additional Visualizations  
- Add new Dash components in `dashboard.py`
- Create callback functions for interactive features

### Alert Systems
- Extend `PowerOutage` creation in `_evaluate_power_outages()`
- Add email, SMS, or webhook notifications

### Data Analysis
- Historical trend analysis in `/api/statistics`
- Predictive outage detection based on patterns