// PowerMon Dashboard JavaScript

// Auto-refresh interval (30 seconds)
const REFRESH_INTERVAL = 30000;
// Relative time update interval (10 seconds)
const TIME_UPDATE_INTERVAL = 10000;
let refreshTimer;
let timeUpdateTimer;

// Update last update time
function updateLastUpdateTime() {
    const now = new Date();
    const timeString = now.toLocaleTimeString();
    const element = document.getElementById('lastUpdate');
    if (element) {
        element.textContent = `Last updated: ${timeString}`;
    }
}

// Update charts with cache-busting timestamp
function updateCharts() {
    const hours = document.getElementById('timeRange')?.value || 24;
    const timestamp = new Date().getTime();

    const timelineChart = document.getElementById('timelineChart');
    const uptimeChart = document.getElementById('uptimeChart');
    const outageChart = document.getElementById('outageChart');

    if (timelineChart) {
        timelineChart.src = `/dashboard/charts/timeline?hours=${hours}&t=${timestamp}`;
    }

    if (uptimeChart) {
        uptimeChart.src = `/dashboard/charts/uptime?hours=${hours}&t=${timestamp}`;
    }

    if (outageChart) {
        // Outage chart uses longer time period (7 days default)
        const outageHours = hours > 168 ? hours : 168;
        outageChart.src = `/dashboard/charts/outages?hours=${outageHours}&t=${timestamp}`;
    }
}

// Update switch status cards via API
async function updateSwitchStatus() {
    try {
        const response = await fetch('/api/status');
        if (!response.ok) {
            throw new Error('API request failed');
        }

        const data = await response.json();

        // Update switch cards
        const switchStatusContainer = document.getElementById('switchStatusCards');
        if (switchStatusContainer && data.switches) {
            // Reload the page to update switch cards
            // (Simpler than complex DOM manipulation)
            location.reload();
        }
    } catch (error) {
        console.error('Error updating switch status:', error);
    }
}

// Refresh dashboard data
function refreshDashboard() {
    const btn = event?.target;
    if (btn) {
        btn.classList.add('loading');
        btn.disabled = true;
    }

    // Update charts
    updateCharts();

    // Update timestamp
    updateLastUpdateTime();

    // Re-enable button after a short delay
    setTimeout(() => {
        if (btn) {
            btn.classList.remove('loading');
            btn.disabled = false;
        }
    }, 1000);
}

// Update dashboard when time range changes
function updateDashboard() {
    updateCharts();
    updateLastUpdateTime();
}

// Check all switches manually
async function checkAllSwitches() {
    const btn = document.getElementById('checkAllBtn');
    const originalText = btn.innerHTML;

    // Disable button and show loading state
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Checking...';

    try {
        const response = await fetch('/api/check-all-switches', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error('Check request failed');
        }

        const data = await response.json();

        // Show success message
        btn.innerHTML = '<i class="bi bi-check-circle"></i> Success!';
        btn.classList.remove('btn-success');
        btn.classList.add('btn-info');

        // Reload page after short delay to show updated results
        setTimeout(() => {
            location.reload();
        }, 1500);

    } catch (error) {
        console.error('Error checking switches:', error);

        // Show error state
        btn.innerHTML = '<i class="bi bi-exclamation-circle"></i> Error';
        btn.classList.remove('btn-success');
        btn.classList.add('btn-danger');

        // Reset button after delay
        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.classList.remove('btn-danger');
            btn.classList.add('btn-success');
            btn.disabled = false;
        }, 3000);
    }
}

// Start auto-refresh
function startAutoRefresh() {
    // Clear any existing timers
    if (refreshTimer) {
        clearInterval(refreshTimer);
    }
    if (timeUpdateTimer) {
        clearInterval(timeUpdateTimer);
    }

    // Set up chart refresh timer
    refreshTimer = setInterval(() => {
        updateCharts();
        updateLastUpdateTime();
    }, REFRESH_INTERVAL);

    // Set up relative time update timer (more frequent)
    timeUpdateTimer = setInterval(() => {
        convertTimesToLocal();
    }, TIME_UPDATE_INTERVAL);

    console.log(`Auto-refresh enabled: charts every ${REFRESH_INTERVAL / 1000}s, times every ${TIME_UPDATE_INTERVAL / 1000}s`);
}

// Stop auto-refresh
function stopAutoRefresh() {
    if (refreshTimer) {
        clearInterval(refreshTimer);
        refreshTimer = null;
    }
    if (timeUpdateTimer) {
        clearInterval(timeUpdateTimer);
        timeUpdateTimer = null;
    }
    console.log('Auto-refresh disabled');
}

// Convert UTC timestamps to relative time
function getRelativeTime(date) {
    const now = new Date();
    const diffMs = now - date;
    const diffSeconds = Math.floor(diffMs / 1000);
    const diffMinutes = Math.floor(diffSeconds / 60);
    const diffHours = Math.floor(diffMinutes / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffSeconds < 60) {
        return diffSeconds <= 1 ? 'just now' : `${diffSeconds} seconds ago`;
    } else if (diffMinutes < 60) {
        return diffMinutes === 1 ? '1 minute ago' : `${diffMinutes} minutes ago`;
    } else if (diffHours < 24) {
        return diffHours === 1 ? '1 hour ago' : `${diffHours} hours ago`;
    } else {
        return diffDays === 1 ? '1 day ago' : `${diffDays} days ago`;
    }
}

// Convert UTC timestamps to relative time
function convertTimesToLocal() {
    const timeElements = document.querySelectorAll('.local-time');

    timeElements.forEach(element => {
        const utcTime = element.getAttribute('data-utc');
        if (utcTime) {
            const date = new Date(utcTime);
            element.textContent = getRelativeTime(date);
            element.setAttribute('title', date.toLocaleString()); // Show full time on hover
        }
    });
}

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function () {
    console.log('PowerMon Dashboard initialized');

    // Set initial last update time
    updateLastUpdateTime();

    // Convert all UTC times to local timezone
    convertTimesToLocal();

    // Start auto-refresh
    startAutoRefresh();

    // Stop auto-refresh when page is hidden
    document.addEventListener('visibilitychange', function () {
        if (document.hidden) {
            stopAutoRefresh();
        } else {
            startAutoRefresh();
        }
    });
});

// Clean up on page unload
window.addEventListener('beforeunload', function () {
    stopAutoRefresh();
});
