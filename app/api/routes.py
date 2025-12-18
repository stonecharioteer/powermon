from flask import jsonify, request
from app.api import bp
from app.models import SmartSwitch, PowerCheck, PowerOutage
from app.services.switch_monitor import SwitchMonitor
from datetime import datetime, timedelta
from sqlalchemy import and_


@bp.route("/switches", methods=["GET"])
def get_switches():
    """Get all switches"""
    switches = SmartSwitch.query.all()
    return jsonify([switch.to_dict() for switch in switches])


@bp.route("/switches/<int:switch_id>", methods=["GET"])
def get_switch(switch_id):
    """Get specific switch details"""
    switch = SmartSwitch.query.get_or_404(switch_id)

    # Get recent power checks for this switch
    recent_checks = (
        PowerCheck.query.filter_by(switch_id=switch_id)
        .order_by(PowerCheck.checked_at.desc())
        .limit(100)
        .all()
    )

    return jsonify(
        {
            "switch": switch.to_dict(),
            "recent_checks": [check.to_dict() for check in recent_checks],
        }
    )


@bp.route("/switches/<int:switch_id>/check", methods=["POST"])
def check_switch_now(switch_id):
    """Trigger immediate check of a switch"""
    switch = SmartSwitch.query.get_or_404(switch_id)

    # Check switch directly for testing (bypass Celery for now)
    monitor = SwitchMonitor()
    is_online, response_time, error_message = monitor.check_switch_status(switch)
    power_check = monitor.record_power_check(switch, is_online, response_time, error_message)

    return jsonify({
        "message": f"Switch {switch.name} checked",
        "result": power_check.to_dict()
    })


@bp.route("/power-checks", methods=["GET"])
def get_power_checks():
    """Get power checks with optional filtering"""
    # Query parameters
    switch_id = request.args.get("switch_id", type=int)
    hours = request.args.get("hours", 24, type=int)  # Default last 24 hours
    limit = request.args.get("limit", 1000, type=int)

    # Build query
    since_time = datetime.utcnow() - timedelta(hours=hours)
    query = PowerCheck.query.filter(PowerCheck.checked_at >= since_time)

    if switch_id:
        query = query.filter_by(switch_id=switch_id)

    checks = query.order_by(PowerCheck.checked_at.desc()).limit(limit).all()

    return jsonify([check.to_dict() for check in checks])


@bp.route("/outages", methods=["GET"])
def get_outages():
    """Get power outages with optional filtering"""
    # Query parameters
    hours = request.args.get("hours", 168, type=int)  # Default last week
    ongoing_only = request.args.get("ongoing_only", False, type=bool)
    limit = request.args.get("limit", 100, type=int)

    # Build query
    since_time = datetime.utcnow() - timedelta(hours=hours)
    query = PowerOutage.query.filter(PowerOutage.started_at >= since_time)

    if ongoing_only:
        query = query.filter_by(is_ongoing=True)

    outages = query.order_by(PowerOutage.started_at.desc()).limit(limit).all()

    return jsonify([outage.to_dict() for outage in outages])


@bp.route("/status", methods=["GET"])
def get_system_status():
    """Get comprehensive system status"""
    # Get all active switches with their latest checks
    switches = SmartSwitch.query.filter_by(is_active=True).all()

    switch_statuses = []
    for switch in switches:
        latest_check = (
            PowerCheck.query.filter_by(switch_id=switch.id)
            .order_by(PowerCheck.checked_at.desc())
            .first()
        )

        # Calculate uptime for last 24 hours
        monitor = SwitchMonitor()
        uptime_24h = monitor.get_switch_uptime_percentage(switch.id, 24)

        switch_statuses.append(
            {
                "switch": switch.to_dict(),
                "latest_check": latest_check.to_dict() if latest_check else None,
                "uptime_24h": uptime_24h,
            }
        )

    # Get ongoing outages
    ongoing_outages = PowerOutage.query.filter_by(is_ongoing=True).all()

    # Get outage count for last 24 hours
    since_24h = datetime.utcnow() - timedelta(hours=24)
    outages_24h = PowerOutage.query.filter(PowerOutage.started_at >= since_24h).count()

    # Calculate overall system health
    online_switches = sum(
        1
        for status in switch_statuses
        if status["latest_check"] and status["latest_check"]["is_online"]
    )
    total_switches = len(switch_statuses)
    system_health = (
        (online_switches / total_switches * 100) if total_switches > 0 else 0
    )

    return jsonify(
        {
            "timestamp": datetime.utcnow().isoformat(),
            "system_health": system_health,
            "switches": {
                "total": total_switches,
                "online": online_switches,
                "offline": total_switches - online_switches,
                "details": switch_statuses,
            },
            "outages": {
                "ongoing": len(ongoing_outages),
                "last_24h": outages_24h,
                "ongoing_details": [outage.to_dict() for outage in ongoing_outages],
            },
        }
    )


@bp.route("/statistics", methods=["GET"])
def get_statistics():
    """Get system statistics"""
    hours = request.args.get("hours", 168, type=int)  # Default last week
    since_time = datetime.utcnow() - timedelta(hours=hours)

    # Get statistics
    total_checks = PowerCheck.query.filter(PowerCheck.checked_at >= since_time).count()
    failed_checks = PowerCheck.query.filter(
        and_(PowerCheck.checked_at >= since_time, not PowerCheck.is_online)
    ).count()

    total_outages = PowerOutage.query.filter(
        PowerOutage.started_at >= since_time
    ).count()

    # Calculate average outage duration
    completed_outages = PowerOutage.query.filter(
        and_(
            PowerOutage.started_at >= since_time,
            not PowerOutage.is_ongoing,
            PowerOutage.duration_seconds.isnot(None),
        )
    ).all()

    avg_outage_duration = 0
    if completed_outages:
        avg_outage_duration = sum(o.duration_seconds for o in completed_outages) / len(
            completed_outages
        )

    return jsonify(
        {
            "period_hours": hours,
            "total_checks": total_checks,
            "failed_checks": failed_checks,
            "success_rate": ((total_checks - failed_checks) / total_checks * 100)
            if total_checks > 0
            else 0,
            "total_outages": total_outages,
            "average_outage_duration_seconds": avg_outage_duration,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )
