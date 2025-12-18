#!/usr/bin/env python3
"""
Management commands for PowerMon
"""

import click
from flask.cli import with_appcontext
from app import create_app, db
from app.models import SmartSwitch, PowerCheck, PowerOutage

app = create_app()


@click.command()
@with_appcontext
def init_db():
    """Initialize the database with tables"""
    db.create_all()
    click.echo("Database initialized!")


@click.command()
@click.argument("label")
@click.argument("ip_address")
@with_appcontext
def add_switch(label, ip_address):
    """Add a new smart switch"""
    # Check if switch already exists
    existing = SmartSwitch.query.filter(
        (SmartSwitch.name == label) | (SmartSwitch.ip_address == ip_address)
    ).first()

    if existing:
        click.echo(f'Switch with name "{label}" or IP "{ip_address}" already exists!')
        return

    switch = SmartSwitch(name=label, ip_address=ip_address)
    db.session.add(switch)
    db.session.commit()

    click.echo(f"Added switch: {label} ({ip_address})")


@click.command()
@with_appcontext
def list_switches():
    """List all switches"""
    switches = SmartSwitch.query.all()

    if not switches:
        click.echo("No switches found.")
        return

    click.echo("Switches:")
    for switch in switches:
        status = "Active" if switch.is_active else "Inactive"
        click.echo(f"  {switch.id}: {switch.name} ({switch.ip_address}) - {status}")


@click.command()
@click.argument("switch_id", type=int)
@with_appcontext
def remove_switch(switch_id):
    """Remove a switch by ID"""
    switch = SmartSwitch.query.get(switch_id)

    if not switch:
        click.echo(f"Switch with ID {switch_id} not found!")
        return

    db.session.delete(switch)
    db.session.commit()

    click.echo(f"Removed switch: {switch.name}")


@click.command()
@click.argument("switch_name")
@with_appcontext
def rm_switch(switch_name):
    """Remove a switch by name"""
    switch = SmartSwitch.query.filter_by(name=switch_name).first()

    if not switch:
        click.echo(f'Switch with name "{switch_name}" not found!')
        # Show available switches
        all_switches = SmartSwitch.query.all()
        if all_switches:
            click.echo("\nAvailable switches:")
            for s in all_switches:
                click.echo(f"  - {s.name} (ID: {s.id})")
        return

    # Ask for confirmation
    click.confirm(
        f'Remove switch "{switch.name}" ({switch.ip_address})?',
        abort=True
    )

    db.session.delete(switch)
    db.session.commit()

    click.echo(f"✓ Removed switch: {switch.name}")


@click.command()
@with_appcontext
def test_switches():
    """Test connectivity to all active switches"""
    from app.services.switch_monitor import SwitchMonitor

    switches = SmartSwitch.query.filter_by(is_active=True).all()

    if not switches:
        click.echo("No active switches found.")
        return

    monitor = SwitchMonitor()

    for switch in switches:
        click.echo(f"Testing {switch.name} ({switch.ip_address})... ", nl=False)
        is_online, response_time, error_message = monitor.check_switch_status(switch)

        if is_online:
            click.echo(f"✓ Online ({response_time:.2f}s)")
        else:
            click.echo(f"✗ Offline ({error_message})")


@click.command()
@click.option("--days", default=7, help="Keep data from last N days")
@with_appcontext
def cleanup_data(days):
    """Clean up old power check data"""
    from datetime import datetime, timedelta

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    deleted_checks = PowerCheck.query.filter(
        PowerCheck.checked_at < cutoff_date
    ).delete()
    db.session.commit()

    click.echo(
        f"Deleted {deleted_checks} old power check records (older than {days} days)"
    )


@click.command()
@with_appcontext
def show_stats():
    """Show system statistics"""
    from datetime import datetime, timedelta

    # Overall stats
    total_switches = SmartSwitch.query.count()
    active_switches = SmartSwitch.query.filter_by(is_active=True).count()

    # Last 24h stats
    since_24h = datetime.utcnow() - timedelta(hours=24)
    checks_24h = PowerCheck.query.filter(PowerCheck.checked_at >= since_24h).count()
    failed_checks_24h = PowerCheck.query.filter(
        PowerCheck.checked_at >= since_24h, not PowerCheck.is_online
    ).count()

    outages_24h = PowerOutage.query.filter(PowerOutage.started_at >= since_24h).count()
    ongoing_outages = PowerOutage.query.filter_by(is_ongoing=True).count()

    click.echo("PowerMon Statistics")
    click.echo("==================")
    click.echo(f"Switches: {active_switches}/{total_switches} active")
    click.echo(f"Last 24h checks: {checks_24h}")
    click.echo(f"Last 24h failed checks: {failed_checks_24h}")
    click.echo(f"Last 24h outages: {outages_24h}")
    click.echo(f"Ongoing outages: {ongoing_outages}")

    if checks_24h > 0:
        success_rate = ((checks_24h - failed_checks_24h) / checks_24h) * 100
        click.echo(f"Success rate: {success_rate:.1f}%")


# Register commands with the app
app.cli.add_command(init_db)
app.cli.add_command(add_switch)
app.cli.add_command(list_switches)
app.cli.add_command(remove_switch)
app.cli.add_command(rm_switch)
app.cli.add_command(test_switches)
app.cli.add_command(cleanup_data)
app.cli.add_command(show_stats)

if __name__ == "__main__":
    app.cli()
