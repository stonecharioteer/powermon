from celery.schedules import crontab
from app import celery, create_app
from app.services.switch_monitor import SwitchMonitor
import os
import logging

logger = logging.getLogger(__name__)

# Configure Celery beat schedule
celery.conf.beat_schedule = {
    "monitor-switches": {
        "task": "app.tasks.monitor_all_switches",
        "schedule": int(os.getenv("MONITOR_INTERVAL", 60)),  # Run every N seconds
    },
}
celery.conf.timezone = "UTC"


@celery.task(bind=True)
def monitor_all_switches(self):
    """Celery task to monitor all smart switches"""
    app = create_app()

    with app.app_context():
        try:
            monitor = SwitchMonitor()
            results = monitor.check_all_switches()

            # Log summary
            total_switches = len(results)
            online_switches = sum(1 for result in results if result["is_online"])
            offline_switches = total_switches - online_switches

            logger.info(
                f"Switch monitoring completed: {online_switches}/{total_switches} online, {offline_switches} offline"
            )

            return {
                "total_switches": total_switches,
                "online": online_switches,
                "offline": offline_switches,
                "timestamp": results[0]["power_check"].checked_at.isoformat()
                if results
                else None,
            }

        except Exception as exc:
            logger.error(f"Error in monitor_all_switches task: {exc}")
            self.retry(exc=exc, countdown=60, max_retries=3)


@celery.task
def check_single_switch(switch_id: int):
    """Celery task to check a single switch"""
    app = create_app()

    with app.app_context():
        from app.models import SmartSwitch

        switch = SmartSwitch.query.get(switch_id)
        if not switch:
            return {"error": f"Switch with id {switch_id} not found"}

        monitor = SwitchMonitor()
        is_online, response_time, error_message = monitor.check_switch_status(switch)
        power_check = monitor.record_power_check(
            switch, is_online, response_time, error_message
        )

        return power_check.to_dict()


@celery.task
def cleanup_old_power_checks():
    """Clean up power check records older than 30 days"""
    app = create_app()

    with app.app_context():
        from datetime import datetime, timedelta
        from app.models import PowerCheck
        from app import db

        # Delete records older than 30 days
        cutoff_date = datetime.utcnow() - timedelta(days=30)

        deleted_count = PowerCheck.query.filter(
            PowerCheck.checked_at < cutoff_date
        ).delete()

        db.session.commit()

        logger.info(f"Cleaned up {deleted_count} old power check records")
        return {"deleted_records": deleted_count}


# Add cleanup task to beat schedule
celery.conf.beat_schedule["cleanup-old-records"] = {
    "task": "app.tasks.cleanup_old_power_checks",
    "schedule": crontab(hour=2, minute=0),  # Run daily at 2 AM
}
