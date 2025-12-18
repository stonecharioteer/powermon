from flask import render_template, request, jsonify, redirect, url_for
from app.main import bp
from app.models import SmartSwitch, PowerCheck, PowerOutage
from app.services.switch_monitor import SwitchMonitor
from app import db
from datetime import datetime


@bp.route("/")
def index():
    """Main dashboard page"""
    from datetime import datetime as dt
    
    switches = SmartSwitch.query.filter_by(is_active=True).all()

    # Get latest power check for each switch
    switch_status = []
    for switch in switches:
        latest_check = (
            PowerCheck.query.filter_by(switch_id=switch.id)
            .order_by(PowerCheck.checked_at.desc())
            .first()
        )
        switch_status.append({"switch": switch, "latest_check": latest_check})

    # Get ongoing outages
    ongoing_outages = PowerOutage.query.filter_by(is_ongoing=True).all()

    # Get recent outages (last 10)
    recent_outages = (
        PowerOutage.query.order_by(PowerOutage.started_at.desc()).limit(10).all()
    )

    return render_template(
        "dashboard.html",
        switch_status=switch_status,
        ongoing_outages=ongoing_outages,
        recent_outages=recent_outages,
        now=dt.utcnow(),
    )


@bp.route("/dashboard/charts/timeline")
def chart_timeline():
    """Generate timeline chart"""
    from flask import send_file, request
    from app.services.chart_generator import ChartGenerator
    
    hours = request.args.get('hours', 24, type=int)
    
    generator = ChartGenerator()
    img_buffer = generator.generate_timeline_chart(hours=hours)
    
    return send_file(img_buffer, mimetype='image/png', as_attachment=False)


@bp.route("/dashboard/charts/uptime")
def chart_uptime():
    """Generate uptime chart"""
    from flask import send_file, request
    from app.services.chart_generator import ChartGenerator
    
    hours = request.args.get('hours', 24, type=int)
    
    generator = ChartGenerator()
    img_buffer = generator.generate_uptime_chart(hours=hours)
    
    return send_file(img_buffer, mimetype='image/png', as_attachment=False)


@bp.route("/dashboard/charts/outages")
def chart_outages():
    """Generate outage duration chart"""
    from flask import send_file, request
    from app.services.chart_generator import ChartGenerator
    
    hours = request.args.get('hours', 168, type=int)
    
    generator = ChartGenerator()
    img_buffer = generator.generate_outage_duration_chart(hours=hours)
    
    return send_file(img_buffer, mimetype='image/png', as_attachment=False)


@bp.route("/switches")
def switches():
    """Switches management page"""
    switches = SmartSwitch.query.all()
    return render_template("switches.html", switches=switches)


@bp.route("/switches/add", methods=["GET", "POST"])
def add_switch():
    """Add new switch"""
    if request.method == "POST":
        name = request.form.get("name")
        ip_address = request.form.get("ip_address")

        if not name or not ip_address:
            return jsonify({"error": "Name and IP address are required"}), 400

        # Check if switch with same name or IP already exists
        existing = SmartSwitch.query.filter(
            (SmartSwitch.name == name) | (SmartSwitch.ip_address == ip_address)
        ).first()

        if existing:
            return jsonify({"error": "Switch with this name or IP already exists"}), 400

        switch = SmartSwitch(name=name, ip_address=ip_address)
        db.session.add(switch)
        db.session.commit()

        return redirect(url_for("main.switches"))

    return render_template("add_switch.html")


@bp.route("/switches/<int:switch_id>/toggle", methods=["POST"])
def toggle_switch(switch_id):
    """Toggle switch active status"""
    switch = SmartSwitch.query.get_or_404(switch_id)
    switch.is_active = not switch.is_active
    switch.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify(
        {"success": True, "switch_id": switch_id, "is_active": switch.is_active}
    )


@bp.route("/switches/<int:switch_id>/delete", methods=["POST"])
def delete_switch(switch_id):
    """Delete a switch"""
    switch = SmartSwitch.query.get_or_404(switch_id)
    db.session.delete(switch)
    db.session.commit()

    return redirect(url_for("main.switches"))


@bp.route("/test-switch/<int:switch_id>")
def test_switch(switch_id):
    """Test a single switch connectivity"""
    switch = SmartSwitch.query.get_or_404(switch_id)

    monitor = SwitchMonitor()
    is_online, response_time, error_message = monitor.check_switch_status(switch)

    # Record the test result
    power_check = monitor.record_power_check(
        switch, is_online, response_time, error_message
    )

    return jsonify(
        {
            "switch_id": switch_id,
            "switch_name": switch.name,
            "is_online": is_online,
            "response_time": response_time,
            "error_message": error_message,
            "checked_at": power_check.checked_at.isoformat(),
        }
    )


@bp.route("/outages")
def outages():
    """Power outages history page"""
    page = request.args.get("page", 1, type=int)
    outages_pagination = PowerOutage.query.order_by(PowerOutage.started_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )

    # Get all switches for displaying affected switches in modals
    switches = SmartSwitch.query.all()

    return render_template(
        "outages.html",
        outages=outages_pagination,
        switches=switches,
        now=datetime.utcnow()
    )


@bp.route("/api/status")
def api_status():
    """API endpoint for current system status"""
    switches = SmartSwitch.query.filter_by(is_active=True).all()

    status_data = []
    for switch in switches:
        latest_check = (
            PowerCheck.query.filter_by(switch_id=switch.id)
            .order_by(PowerCheck.checked_at.desc())
            .first()
        )

        status_data.append(
            {
                "switch": switch.to_dict(),
                "latest_check": latest_check.to_dict() if latest_check else None,
            }
        )

    # Check for ongoing outages
    ongoing_outages = PowerOutage.query.filter_by(is_ongoing=True).all()

    return jsonify(
        {
            "switches": status_data,
            "ongoing_outages": [outage.to_dict() for outage in ongoing_outages],
            "timestamp": datetime.utcnow().isoformat(),
        }
    )
