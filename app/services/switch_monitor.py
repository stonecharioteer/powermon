import subprocess
import platform
import time
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import logging
from app import db
from app.models import SmartSwitch, PowerCheck, PowerOutage
import os

logger = logging.getLogger(__name__)


class SwitchMonitor:
    """Service for monitoring smart switches and detecting power outages"""

    def __init__(self, timeout: int = 5):
        self.timeout = timeout
        self.outage_threshold = int(os.getenv("POWER_OUTAGE_THRESHOLD", 2))

    def check_switch_status(
        self, switch: SmartSwitch
    ) -> Tuple[bool, Optional[float], Optional[str]]:
        """
        Check if a smart switch is online using ICMP ping

        Returns:
            Tuple of (is_online, response_time, error_message)
        """
        import subprocess
        import platform

        try:
            start_time = time.time()

            # Determine ping command parameters based on OS
            system = platform.system().lower()
            
            # Build ping command
            if system == 'windows':
                # Windows: ping -n 1 -w timeout_ms IP
                command = [
                    'ping',
                    '-n', '1',  # Send 1 packet
                    '-w', str(self.timeout * 1000),  # Timeout in milliseconds
                    switch.ip_address
                ]
            else:
                # Linux/Mac: ping -c 1 -W timeout_sec IP
                command = [
                    'ping',
                    '-c', '1',  # Send 1 packet
                    '-W', str(self.timeout),  # Timeout in seconds
                    switch.ip_address
                ]

            # Execute ping command
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.timeout + 1
            )

            response_time = time.time() - start_time

            # Check if ping was successful (return code 0)
            is_online = result.returncode == 0

            if is_online:
                return True, response_time, None
            else:
                return False, None, "Ping failed - device unreachable"

        except subprocess.TimeoutExpired:
            return False, None, "Ping timeout"
        except Exception as e:
            logger.error(f"Unexpected error pinging switch {switch.name}: {e}")
            return False, None, f"Ping error: {str(e)}"

    def record_power_check(
        self,
        switch: SmartSwitch,
        is_online: bool,
        response_time: Optional[float] = None,
        error_message: Optional[str] = None,
    ) -> PowerCheck:
        """Record a power check result in the database"""
        power_check = PowerCheck(
            switch_id=switch.id,
            is_online=is_online,
            response_time=response_time,
            error_message=error_message,
        )

        db.session.add(power_check)
        db.session.commit()

        logger.info(
            f"Recorded power check for {switch.name}: {'Online' if is_online else 'Offline'}"
        )
        return power_check

    def check_all_switches(self) -> List[Dict]:
        """Check all active switches and return their status"""
        switches = SmartSwitch.query.filter_by(is_active=True).all()
        results = []

        for switch in switches:
            is_online, response_time, error_message = self.check_switch_status(switch)
            power_check = self.record_power_check(
                switch, is_online, response_time, error_message
            )

            results.append(
                {"switch": switch, "power_check": power_check, "is_online": is_online}
            )

        # Check if we need to create or end power outages
        self._evaluate_power_outages(results)

        return results

    def _evaluate_power_outages(self, check_results: List[Dict]):
        """Evaluate if there's a power outage based on recent checks"""
        # Get count of switches that are offline
        offline_count = sum(1 for result in check_results if not result["is_online"])
        total_switches = len(check_results)

        if total_switches == 0:
            return

        # Consider it an outage if more than half of switches are offline
        is_outage_detected = offline_count >= (total_switches / 2)

        # Check for ongoing outages
        ongoing_outage = PowerOutage.query.filter_by(is_ongoing=True).first()

        if is_outage_detected and not ongoing_outage:
            # Start new outage
            offline_switch_ids = [
                result["switch"].id
                for result in check_results
                if not result["is_online"]
            ]

            outage = PowerOutage(
                started_at=datetime.utcnow(),
                switches_affected=offline_switch_ids,
                is_ongoing=True,
            )

            db.session.add(outage)
            db.session.commit()

            logger.warning(
                f"Power outage detected! {offline_count}/{total_switches} switches offline"
            )

        elif not is_outage_detected and ongoing_outage:
            # End ongoing outage
            ongoing_outage.ended_at = datetime.utcnow()
            ongoing_outage.duration_seconds = int(
                (ongoing_outage.ended_at - ongoing_outage.started_at).total_seconds()
            )
            ongoing_outage.is_ongoing = False

            db.session.commit()

            logger.info(
                f"Power outage ended! Duration: {ongoing_outage.duration_seconds} seconds"
            )

    def get_recent_checks(
        self, switch_id: Optional[int] = None, limit: int = 100
    ) -> List[PowerCheck]:
        """Get recent power checks, optionally filtered by switch"""
        query = PowerCheck.query.order_by(PowerCheck.checked_at.desc())

        if switch_id:
            query = query.filter_by(switch_id=switch_id)

        return query.limit(limit).all()

    def get_switch_uptime_percentage(self, switch_id: int, hours: int = 24) -> float:
        """Calculate uptime percentage for a switch over the last N hours"""
        from datetime import timedelta

        # Get checks from the last N hours
        since_time = datetime.utcnow() - timedelta(hours=hours)

        total_checks = PowerCheck.query.filter(
            PowerCheck.switch_id == switch_id, PowerCheck.checked_at >= since_time
        ).count()

        if total_checks == 0:
            return 0.0

        online_checks = PowerCheck.query.filter(
            PowerCheck.switch_id == switch_id,
            PowerCheck.checked_at >= since_time,
            PowerCheck.is_online,
        ).count()

        return (online_checks / total_checks) * 100.0
