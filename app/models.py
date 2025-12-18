from datetime import datetime
from app import db
from sqlalchemy import Index


class SmartSwitch(db.Model):
    """Model for smart switches that act as power monitoring checkpoints"""

    __tablename__ = "smart_switches"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    ip_address = db.Column(db.String(15), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationship to power checks
    power_checks = db.relationship(
        "PowerCheck", backref="switch", lazy="dynamic", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<SmartSwitch {self.name}: {self.ip_address}>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "ip_address": self.ip_address,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class PowerCheck(db.Model):
    """Model for individual power status checks for each switch"""

    __tablename__ = "power_checks"

    id = db.Column(db.Integer, primary_key=True)
    switch_id = db.Column(
        db.Integer, db.ForeignKey("smart_switches.id"), nullable=False
    )
    is_online = db.Column(db.Boolean, nullable=False)
    response_time = db.Column(db.Float)  # in seconds
    error_message = db.Column(db.Text)
    checked_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<PowerCheck {self.switch.name}: {'Online' if self.is_online else 'Offline'} at {self.checked_at}>"

    def to_dict(self):
        return {
            "id": self.id,
            "switch_id": self.switch_id,
            "switch_name": self.switch.name,
            "is_online": self.is_online,
            "response_time": self.response_time,
            "error_message": self.error_message,
            "checked_at": self.checked_at.isoformat(),
        }


class PowerOutage(db.Model):
    """Model for detected power outages"""

    __tablename__ = "power_outages"

    id = db.Column(db.Integer, primary_key=True)
    started_at = db.Column(db.DateTime, nullable=False, index=True)
    ended_at = db.Column(db.DateTime, index=True)
    duration_seconds = db.Column(db.Integer)  # calculated when outage ends
    switches_affected = db.Column(db.JSON)  # list of switch IDs that were offline
    is_ongoing = db.Column(db.Boolean, default=True, index=True)

    def __repr__(self):
        status = "Ongoing" if self.is_ongoing else f"Lasted {self.duration_seconds}s"
        return f"<PowerOutage started {self.started_at}: {status}>"

    def to_dict(self):
        return {
            "id": self.id,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "duration_seconds": self.duration_seconds,
            "switches_affected": self.switches_affected,
            "is_ongoing": self.is_ongoing,
        }


# Create database indexes for better query performance
Index("idx_power_checks_switch_time", PowerCheck.switch_id, PowerCheck.checked_at)
Index("idx_power_outages_time_status", PowerOutage.started_at, PowerOutage.is_ongoing)
