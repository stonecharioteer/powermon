from celery import Celery
from celery.schedules import crontab
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create Celery instance
celery = Celery('powermon')

# Configure Celery
celery.conf.update(
    broker_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    result_backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    beat_schedule={
        "monitor-switches": {
            "task": "app.tasks.monitor_all_switches",
            "schedule": int(os.getenv("MONITOR_INTERVAL", 60)),
        },
        "cleanup-old-records": {
            "task": "app.tasks.cleanup_old_power_checks", 
            "schedule": crontab(hour=2, minute=0),
        },
    }
)

# Import tasks after configuration to register them
from app import tasks