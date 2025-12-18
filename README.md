# PowerMon 🔌⚡

A comprehensive power outage monitoring system that tracks smart switches to detect and visualize power outages in your home or office.

## Features

- 🏠 **Smart Switch Monitoring** - Monitor multiple smart switches as power checkpoints
- 📊 **Real-time Dashboard** - Interactive Dash/Plotly visualizations
- ⚡ **Automatic Outage Detection** - Intelligent power outage detection algorithms
- 🔔 **Historical Analysis** - Track uptime, outage patterns, and system statistics
- 🐳 **Docker Ready** - Complete containerized deployment with Docker Compose
- 🛠️ **Management CLI** - Easy switch management and system administration
- 📈 **REST API** - Full API for integration with other systems

## Quick Start

### Prerequisites

- Docker and Docker Compose
- [just](https://github.com/casey/just) command runner (install with `brew install just` or see [installation guide](https://just.systems/man/en/chapter_4.html))

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd powermon
   ```

2. **Copy environment configuration:**
   ```bash
   cp .env.example .env
   ```

3. **Edit `.env` file** with your settings:
   ```bash
   # Add your smart switch IPs
   SMART_SWITCHES=living-room:192.168.1.100,bedroom:192.168.1.101
   ```

4. **Start the application:**
   ```bash
   just up
   ```

5. **Initialize the database:**
   ```bash
   just init-db
   ```

6. **Add your smart switches:**
   ```bash
   just add-switch "Living Room" 192.168.1.100
   just add-switch "Bedroom" 192.168.1.101
   ```

### Access the Application

- **📊 Dashboard**: http://localhost:8050 - Interactive charts and visualizations
- **🌐 Web Interface**: http://localhost:56957 - Switch management and status
- **🌸 Celery Flower**: http://localhost:5555 - Background task monitoring

Open any interface with:
```bash
just dashboard  # Opens dashboard in browser
just web        # Opens web interface
just flower     # Opens Celery monitoring
```

## Usage

### Managing Switches

```bash
# List all switches
just list-switches

# Test connectivity
just test-switches

# Add a new switch
just add-switch "Kitchen Light" 192.168.1.102

# Remove a switch (use ID from list-switches)
just remove-switch 3

# Show system statistics
just show-stats
```

### Monitoring and Logs

```bash
# View all service logs
just logs

# View specific service logs
just logs-web
just logs-celery

# Check container status
just status

# View resource usage
just stats
```

### Development

```bash
# Install dependencies
just install

# Run individual services locally (for development)
just dev-run        # Flask web server
just dev-dashboard  # Dash dashboard
just dev-worker     # Celery worker
just dev-beat       # Celery scheduler

# Code quality
just format         # Format code with ruff
just lint          # Check code quality
just check         # Run both format and lint
```

## How It Works

PowerMon monitors your smart switches by sending periodic HTTP requests to their IP addresses. Here's the monitoring logic:

1. **Switch Monitoring**: Every 60 seconds (configurable), PowerMon checks each active switch
2. **Status Detection**: Any HTTP response (200, 404, etc.) = switch is reachable = power is on
3. **Outage Detection**: Connection timeouts/failures = switch unreachable = potential power issue
4. **Outage Logic**: When >50% of switches are unreachable, PowerMon declares a power outage
5. **Data Storage**: All checks and outages are stored in PostgreSQL for analysis

### Supported Devices

PowerMon works with any network device that responds to HTTP requests:
- Smart switches (TP-Link, Kasa, etc.)
- Smart plugs
- WiFi routers
- Smart home hubs
- Any HTTP-enabled IoT device

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed system architecture documentation.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://powermon:powermon123@postgres:5432/powermon` | PostgreSQL connection string |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection for caching and messaging |
| `MONITOR_INTERVAL` | `60` | Seconds between switch checks |
| `POWER_OUTAGE_THRESHOLD` | `2` | Consecutive failures before declaring outage |
| `SECRET_KEY` | `your-secret-key` | Flask secret key for sessions |

### Smart Switch Configuration

Add switches to your `.env` file:
```bash
SMART_SWITCHES=switch1:192.168.1.100,switch2:192.168.1.101,router:192.168.1.1
```

## API Reference

### REST Endpoints

- `GET /api/switches` - List all switches
- `GET /api/status` - Complete system status
- `GET /api/power-checks?hours=24` - Power check history
- `GET /api/outages?hours=168` - Outage history
- `GET /api/statistics` - System statistics
- `POST /api/switches/{id}/check` - Trigger immediate switch check

### Management CLI

```bash
# Database management
python manage.py init-db
python manage.py cleanup-data --days 30

# Switch management
python manage.py add-switch "Device Name" "192.168.1.100"
python manage.py list-switches
python manage.py test-switches
python manage.py remove-switch 1

# System information
python manage.py show-stats
```

## Deployment

### Production Considerations

1. **Environment Variables**: Use proper secrets in production
2. **Database**: Consider external PostgreSQL for persistence
3. **Monitoring**: Use Celery Flower for task monitoring
4. **Backups**: Backup PostgreSQL data regularly
5. **Security**: Run behind reverse proxy with HTTPS

### Docker Compose Services

- **web**: Flask application server (Gunicorn)
- **dash**: Dashboard server (Dash/Plotly)
- **postgres**: Database server
- **redis**: Cache and message broker
- **celery_worker**: Background task processor
- **celery_beat**: Task scheduler
- **celery_flower**: Task monitoring UI

### Health Checks

All services include health checks to ensure proper startup order and service availability.

## Development

### Project Structure

```
powermon/
├── app/                    # Flask application
│   ├── __init__.py        # App factory and Celery setup
│   ├── models.py          # Database models
│   ├── tasks.py           # Background tasks
│   ├── main/              # Web interface routes
│   ├── api/               # REST API endpoints
│   └── services/          # Business logic
├── dashboard.py           # Dash visualization app
├── manage.py              # CLI management commands
├── justfile               # Development commands
└── docker-compose.yml     # Container orchestration
```

### Adding New Features

1. **New Switch Types**: Extend `SwitchMonitor` class in `app/services/switch_monitor.py`
2. **Dashboard Charts**: Add components and callbacks in `dashboard.py`
3. **API Endpoints**: Add routes in `app/api/routes.py`
4. **Management Commands**: Add commands in `manage.py`

## Troubleshooting

### Common Issues

**Port Conflicts**: Web service runs on port 56957 (not 5000). Check for conflicts.

**Database Connection**: Ensure PostgreSQL container starts successfully:
```bash
just logs postgres
```

**Switch Detection**: Verify switches respond to HTTP requests:
```bash
curl -I http://192.168.1.100  # Should return HTTP response
```

**Celery Tasks**: Check if background monitoring is running:
```bash
just logs-celery
just flower  # Monitor tasks graphically
```

### Getting Help

1. Check service logs: `just logs`
2. Verify container status: `just status`
3. Test switch connectivity: `just test-switches`
4. Review system stats: `just show-stats`

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and code quality checks: `just check`
5. Submit a pull request

---

**PowerMon** - Never be caught off guard by power outages again! 🔌⚡