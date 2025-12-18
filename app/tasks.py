from celery_app import celery
from app.services.switch_monitor import SwitchMonitor
import logging

logger = logging.getLogger(__name__)


@celery.task(bind=True, name='app.tasks.monitor_all_switches')
def monitor_all_switches_task(self):
    """Celery task to monitor all smart switches"""
    from app import create_app
    
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
            raise exc


@celery.task(name='app.tasks.check_single_switch')
def check_single_switch_task(switch_id: int):
    """Celery task to check a single switch"""
    from app import create_app
    
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


@celery.task(name='app.tasks.cleanup_old_power_checks')
def cleanup_old_power_checks_task():
    """Clean up power check records older than 30 days"""
    from app import create_app
    
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


# Tasks are auto-discovered and configured in celery_app.py