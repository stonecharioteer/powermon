import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
from app import create_app

# Load environment variables
load_dotenv()

# Initialize Flask app for database access
app = create_app()

# Initialize Dash app
dash_app = dash.Dash(
    __name__, external_stylesheets=["https://codepen.io/chriddyp/pen/bWLwgP.css"]
)

dash_app.layout = html.Div(
    [
        html.H1("PowerMon Dashboard", className="header-title"),
        html.Div(
            [
                html.Div(
                    [
                        html.H3("Current Status"),
                        html.Div(id="current-status", className="status-container"),
                    ],
                    className="six columns",
                ),
                html.Div(
                    [
                        html.H3("Controls"),
                        html.Button(
                            "Refresh Data",
                            id="refresh-button",
                            n_clicks=0,
                            className="button-primary",
                        ),
                        html.Br(),
                        html.Label("Time Range:"),
                        dcc.Dropdown(
                            id="time-range-dropdown",
                            options=[
                                {"label": "Last Hour", "value": 1},
                                {"label": "Last 6 Hours", "value": 6},
                                {"label": "Last 24 Hours", "value": 24},
                                {"label": "Last 7 Days", "value": 168},
                                {"label": "Last 30 Days", "value": 720},
                            ],
                            value=24,
                        ),
                    ],
                    className="six columns",
                ),
            ],
            className="row",
        ),
        html.Hr(),
        html.Div([dcc.Graph(id="power-status-timeline")]),
        html.Div(
            [
                html.Div([dcc.Graph(id="uptime-chart")], className="six columns"),
                html.Div(
                    [dcc.Graph(id="outage-duration-chart")], className="six columns"
                ),
            ],
            className="row",
        ),
        html.Div(
            [html.H3("Recent Power Outages"), html.Div(id="recent-outages-table")]
        ),
        # Auto-refresh component
        dcc.Interval(
            id="interval-component",
            interval=30 * 1000,  # Update every 30 seconds
            n_intervals=0,
        ),
        # Store component for data
        dcc.Store(id="power-data-store"),
    ]
)


def get_power_data(hours: int = 24):
    """Get power monitoring data from the database"""
    with app.app_context():
        from app.models import SmartSwitch, PowerCheck, PowerOutage

        # Get time range
        since_time = datetime.utcnow() - timedelta(hours=hours)

        # Get switches
        switches = SmartSwitch.query.filter_by(is_active=True).all()

        # Get power checks
        power_checks = (
            PowerCheck.query.filter(PowerCheck.checked_at >= since_time)
            .order_by(PowerCheck.checked_at.asc())
            .all()
        )

        # Get power outages
        outages = (
            PowerOutage.query.filter(PowerOutage.started_at >= since_time)
            .order_by(PowerOutage.started_at.desc())
            .all()
        )

        return {
            "switches": [switch.to_dict() for switch in switches],
            "power_checks": [check.to_dict() for check in power_checks],
            "outages": [outage.to_dict() for outage in outages],
        }


@dash_app.callback(
    Output("power-data-store", "data"),
    [
        Input("interval-component", "n_intervals"),
        Input("refresh-button", "n_clicks"),
        Input("time-range-dropdown", "value"),
    ],
)
def update_power_data(n_intervals, n_clicks, hours):
    """Update power data store"""
    return get_power_data(hours)


@dash_app.callback(
    Output("current-status", "children"), [Input("power-data-store", "data")]
)
def update_current_status(data):
    """Update current status display"""
    if not data or not data.get("switches"):
        return html.P("No switch data available")

    # Get latest status for each switch
    status_cards = []
    for switch in data["switches"]:
        switch_checks = [
            check
            for check in data["power_checks"]
            if check["switch_id"] == switch["id"]
        ]

        if switch_checks:
            latest_check = max(switch_checks, key=lambda x: x["checked_at"])
            status = "Online" if latest_check["is_online"] else "Offline"
            color = "green" if latest_check["is_online"] else "red"

            status_cards.append(
                html.Div(
                    [
                        html.H5(switch["name"]),
                        html.P(f"Status: {status}", style={"color": color}),
                        html.P(f"Last Check: {latest_check['checked_at'][:19]}"),
                    ],
                    className="status-card",
                    style={
                        "border": f"2px solid {color}",
                        "padding": "10px",
                        "margin": "5px",
                        "border-radius": "5px",
                    },
                )
            )

    # Check for ongoing outage
    ongoing_outage = next((o for o in data["outages"] if o["is_ongoing"]), None)
    if ongoing_outage:
        outage_duration = (
            datetime.utcnow()
            - datetime.fromisoformat(
                ongoing_outage["started_at"].replace("Z", "+00:00")
            )
        ).total_seconds() / 60
        status_cards.insert(
            0,
            html.Div(
                [
                    html.H4("⚠️ POWER OUTAGE ONGOING", style={"color": "red"}),
                    html.P(f"Started: {ongoing_outage['started_at'][:19]}"),
                    html.P(f"Duration: {outage_duration:.0f} minutes"),
                ],
                style={
                    "background-color": "#ffebee",
                    "padding": "15px",
                    "margin": "10px 0",
                    "border-radius": "5px",
                    "border": "2px solid red",
                },
            ),
        )

    return status_cards


@dash_app.callback(
    Output("power-status-timeline", "figure"), [Input("power-data-store", "data")]
)
def update_timeline_chart(data):
    """Update power status timeline chart"""
    if not data or not data["power_checks"]:
        return go.Figure().add_annotation(
            text="No data available", x=0.5, y=0.5, showarrow=False
        )

    # Create DataFrame
    df = pd.DataFrame(data["power_checks"])
    df["checked_at"] = pd.to_datetime(df["checked_at"])

    # Create timeline chart
    fig = go.Figure()

    # Add trace for each switch
    switches = {switch["id"]: switch["name"] for switch in data["switches"]}

    for switch_id, switch_name in switches.items():
        switch_data = df[df["switch_id"] == switch_id]
        if not switch_data.empty:
            fig.add_trace(
                go.Scatter(
                    x=switch_data["checked_at"],
                    y=switch_data["is_online"].astype(int),
                    mode="lines+markers",
                    name=switch_name,
                    line=dict(width=2),
                    marker=dict(size=4),
                )
            )

    # Add outage periods as shaded regions
    for outage in data["outages"]:
        start_time = pd.to_datetime(outage["started_at"])
        end_time = (
            pd.to_datetime(outage["ended_at"])
            if outage["ended_at"]
            else datetime.utcnow()
        )

        fig.add_vrect(
            x0=start_time,
            x1=end_time,
            fillcolor="red",
            opacity=0.2,
            layer="below",
            line_width=0,
        )

    fig.update_layout(
        title="Power Status Timeline",
        xaxis_title="Time",
        yaxis_title="Status",
        yaxis=dict(tickmode="array", tickvals=[0, 1], ticktext=["Offline", "Online"]),
        hovermode="x unified",
    )

    return fig


@dash_app.callback(
    Output("uptime-chart", "figure"), [Input("power-data-store", "data")]
)
def update_uptime_chart(data):
    """Update uptime percentage chart"""
    if not data or not data["power_checks"]:
        return go.Figure().add_annotation(
            text="No data available", x=0.5, y=0.5, showarrow=False
        )

    # Calculate uptime for each switch
    uptimes = []
    switches = {switch["id"]: switch["name"] for switch in data["switches"]}

    for switch_id, switch_name in switches.items():
        switch_checks = [
            check for check in data["power_checks"] if check["switch_id"] == switch_id
        ]
        if switch_checks:
            online_count = sum(1 for check in switch_checks if check["is_online"])
            uptime_pct = (online_count / len(switch_checks)) * 100
            uptimes.append({"switch": switch_name, "uptime": uptime_pct})

    if not uptimes:
        return go.Figure().add_annotation(
            text="No uptime data", x=0.5, y=0.5, showarrow=False
        )

    df_uptime = pd.DataFrame(uptimes)

    fig = px.bar(
        df_uptime,
        x="switch",
        y="uptime",
        title="Switch Uptime Percentage",
        labels={"uptime": "Uptime %", "switch": "Switch Name"},
    )

    fig.update_layout(yaxis=dict(range=[0, 100]))

    return fig


@dash_app.callback(
    Output("outage-duration-chart", "figure"), [Input("power-data-store", "data")]
)
def update_outage_chart(data):
    """Update outage duration chart"""
    if not data or not data["outages"]:
        return go.Figure().add_annotation(
            text="No outages in selected period", x=0.5, y=0.5, showarrow=False
        )

    # Filter completed outages
    completed_outages = [
        o for o in data["outages"] if not o["is_ongoing"] and o["duration_seconds"]
    ]

    if not completed_outages:
        return go.Figure().add_annotation(
            text="No completed outages", x=0.5, y=0.5, showarrow=False
        )

    # Create duration chart
    durations = [
        o["duration_seconds"] / 60 for o in completed_outages
    ]  # Convert to minutes
    start_times = [o["started_at"][:19] for o in completed_outages]

    fig = go.Figure(data=[go.Bar(x=start_times, y=durations, name="Outage Duration")])

    fig.update_layout(
        title="Power Outage Durations",
        xaxis_title="Outage Start Time",
        yaxis_title="Duration (minutes)",
    )

    return fig


@dash_app.callback(
    Output("recent-outages-table", "children"), [Input("power-data-store", "data")]
)
def update_outages_table(data):
    """Update recent outages table"""
    if not data or not data["outages"]:
        return html.P("No recent outages")

    # Create table rows
    rows = []
    for outage in data["outages"][:10]:  # Show last 10 outages
        status = (
            "Ongoing"
            if outage["is_ongoing"]
            else f"{outage['duration_seconds'] // 60} minutes"
        )
        rows.append(
            html.Tr(
                [
                    html.Td(outage["started_at"][:19]),
                    html.Td(
                        outage["ended_at"][:19] if outage["ended_at"] else "Ongoing"
                    ),
                    html.Td(status),
                    html.Td(
                        len(outage["switches_affected"])
                        if outage["switches_affected"]
                        else 0
                    ),
                ]
            )
        )

    table = html.Table(
        [
            html.Thead(
                [
                    html.Tr(
                        [
                            html.Th("Started"),
                            html.Th("Ended"),
                            html.Th("Duration"),
                            html.Th("Switches Affected"),
                        ]
                    )
                ]
            ),
            html.Tbody(rows),
        ],
        className="table",
    )

    return table


if __name__ == "__main__":
    dash_app.run_server(host="0.0.0.0", port=8050, debug=True)
