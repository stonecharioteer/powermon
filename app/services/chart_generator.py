"""
Chart generation service using Matplotlib for dashboard visualizations
"""
import io
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from app.models import SmartSwitch, PowerCheck, PowerOutage
from app import db

# Configure matplotlib style
plt.style.use('seaborn-v0_8-darkgrid')

class ChartGenerator:
    """Service for generating dashboard charts using Matplotlib"""
    
    def __init__(self):
        self.fig_size = (12, 6)  # Default figure size
        self.dpi = 100
        # Bootstrap-inspired color palette
        self.colors = {
            'primary': '#0d6efd',
            'success': '#198754',
            'danger': '#dc3545',
            'warning': '#ffc107',
            'info': '#0dcaf0',
            'secondary': '#6c757d'
        }
    
    def generate_timeline_chart(self, hours: int = 24) -> io.BytesIO:
        """
        Generate power status timeline chart showing switch status over time
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            BytesIO object containing PNG image
        """
        since_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Get all active switches
        switches = SmartSwitch.query.filter_by(is_active=True).all()
        
        fig, ax = plt.subplots(figsize=self.fig_size, dpi=self.dpi)
        
        # Plot each switch as a separate line
        for idx, switch in enumerate(switches):
            checks = PowerCheck.query.filter(
                PowerCheck.switch_id == switch.id,
                PowerCheck.checked_at >= since_time
            ).order_by(PowerCheck.checked_at.asc()).all()
            
            if checks:
                times = [check.checked_at for check in checks]
                statuses = [1 if check.is_online else 0 for check in checks]
                
                ax.plot(times, statuses, marker='o', markersize=3, 
                       label=switch.name, linewidth=2, alpha=0.7)
        
        # Formatting
        ax.set_xlabel('Time', fontsize=12, fontweight='bold')
        ax.set_ylabel('Status', fontsize=12, fontweight='bold')
        ax.set_title(f'Switch Status Timeline (Last {hours} hours)', 
                    fontsize=14, fontweight='bold', pad=20)
        ax.set_yticks([0, 1])
        ax.set_yticklabels(['Offline', 'Online'])
        ax.legend(loc='upper left', framealpha=0.9)
        ax.grid(True, alpha=0.3)
        
        # Format x-axis dates
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=max(1, hours // 12)))
        plt.xticks(rotation=45, ha='right')
        
        plt.tight_layout()
        
        # Save to BytesIO
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', bbox_inches='tight')
        img_buffer.seek(0)
        plt.close(fig)
        
        return img_buffer
    
    def generate_uptime_chart(self, hours: int = 24) -> io.BytesIO:
        """
        Generate uptime percentage bar chart for each switch
        
        Args:
            hours: Number of hours to calculate uptime for
            
        Returns:
            BytesIO object containing PNG image
        """
        since_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Get all active switches
        switches = SmartSwitch.query.filter_by(is_active=True).all()
        
        switch_names = []
        uptime_percentages = []
        
        for switch in switches:
            total_checks = PowerCheck.query.filter(
                PowerCheck.switch_id == switch.id,
                PowerCheck.checked_at >= since_time
            ).count()
            
            if total_checks > 0:
                online_checks = PowerCheck.query.filter(
                    PowerCheck.switch_id == switch.id,
                    PowerCheck.checked_at >= since_time,
                    PowerCheck.is_online == True
                ).count()
                
                uptime = (online_checks / total_checks) * 100
                switch_names.append(switch.name)
                uptime_percentages.append(uptime)
        
        # Create horizontal bar chart
        fig, ax = plt.subplots(figsize=(10, max(6, len(switch_names) * 0.5)), dpi=self.dpi)
        
        # Color bars based on uptime percentage
        colors = [
            self.colors['success'] if up >= 95 else 
            self.colors['warning'] if up >= 80 else 
            self.colors['danger']
            for up in uptime_percentages
        ]
        
        bars = ax.barh(switch_names, uptime_percentages, color=colors, alpha=0.8)
        
        # Add percentage labels on bars
        for idx, (bar, pct) in enumerate(zip(bars, uptime_percentages)):
            width = bar.get_width()
            ax.text(width + 1, bar.get_y() + bar.get_height()/2, 
                   f'{pct:.1f}%', ha='left', va='center', fontweight='bold')
        
        ax.set_xlabel('Uptime (%)', fontsize=12, fontweight='bold')
        ax.set_title(f'Switch Uptime (Last {hours} hours)', 
                    fontsize=14, fontweight='bold', pad=20)
        ax.set_xlim(0, 105)  # Extra space for labels
        ax.grid(True, alpha=0.3, axis='x')
        
        plt.tight_layout()
        
        # Save to BytesIO
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', bbox_inches='tight')
        img_buffer.seek(0)
        plt.close(fig)
        
        return img_buffer
    
    def generate_outage_duration_chart(self, hours: int = 168) -> io.BytesIO:
        """
        Generate histogram of outage durations
        
        Args:
            hours: Number of hours to look back (default 7 days)
            
        Returns:
            BytesIO object containing PNG image
        """
        since_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Get completed outages
        outages = PowerOutage.query.filter(
            PowerOutage.started_at >= since_time,
            PowerOutage.is_ongoing == False,
            PowerOutage.duration_seconds.isnot(None)
        ).all()
        
        fig, ax = plt.subplots(figsize=self.fig_size, dpi=self.dpi)
        
        if outages:
            # Convert durations to minutes
            durations_minutes = [o.duration_seconds / 60 for o in outages]
            
            # Create histogram
            n, bins, patches = ax.hist(durations_minutes, bins=20, 
                                       color=self.colors['danger'], 
                                       alpha=0.7, edgecolor='black')
            
            # Color bars by duration
            for i, patch in enumerate(patches):
                if bins[i] < 5:  # Less than 5 minutes
                    patch.set_facecolor(self.colors['warning'])
                elif bins[i] < 30:  # Less than 30 minutes
                    patch.set_facecolor(self.colors['danger'])
                else:  # 30+ minutes
                    patch.set_facecolor('#a71d2a')  # Darker red
            
            ax.set_xlabel('Duration (minutes)', fontsize=12, fontweight='bold')
            ax.set_ylabel('Number of Outages', fontsize=12, fontweight='bold')
            ax.set_title(f'Power Outage Duration Distribution (Last {hours // 24} days)', 
                        fontsize=14, fontweight='bold', pad=20)
            
            # Add statistics text
            avg_duration = sum(durations_minutes) / len(durations_minutes)
            max_duration = max(durations_minutes)
            stats_text = f'Total Outages: {len(outages)}\nAvg Duration: {avg_duration:.1f} min\nMax Duration: {max_duration:.1f} min'
            ax.text(0.98, 0.97, stats_text, transform=ax.transAxes,
                   fontsize=10, verticalalignment='top', horizontalalignment='right',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        else:
            # No outages - show message
            ax.text(0.5, 0.5, 'No outages recorded in this period',
                   transform=ax.transAxes, fontsize=14,
                   ha='center', va='center', color=self.colors['success'],
                   fontweight='bold')
            ax.set_xlabel('Duration (minutes)', fontsize=12, fontweight='bold')
            ax.set_ylabel('Number of Outages', fontsize=12, fontweight='bold')
            ax.set_title(f'Power Outage Duration Distribution (Last {hours // 24} days)', 
                        fontsize=14, fontweight='bold', pad=20)
        
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        
        # Save to BytesIO
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', bbox_inches='tight')
        img_buffer.seek(0)
        plt.close(fig)
        
        return img_buffer
