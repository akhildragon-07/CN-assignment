import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def plot_pdr_comparison(df_base: pd.DataFrame, df_prop: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df_base["step"],
            y=df_base["pdr"],
            mode="lines+markers",
            name="Baseline RPL",
            line=dict(color="#ef4444", width=2.5, dash="dash"),
            marker=dict(size=5),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df_prop["step"],
            y=df_prop["pdr"],
            mode="lines+markers",
            name="BAS-RPL",
            line=dict(color="#10b981", width=3),
            marker=dict(size=5),
        )
    )

    fig.update_layout(
        title="Packet Delivery Ratio (PDR) Comparison",
        xaxis_title="Simulation Step",
        yaxis_title="PDR (%)",
        yaxis=dict(range=[0, 105]),
        plot_bgcolor="#f8fafc",
        paper_bgcolor="#ffffff",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=20, t=60, b=40),
        height=380,
    )
    return fig


def plot_packet_drops_breakdown(df_base: pd.DataFrame, df_prop: pd.DataFrame) -> go.Figure:
    last_base = df_base.iloc[-1]
    last_prop = df_prop.iloc[-1]

    categories = ["Buffer Overflow", "Channel Loss"]
    base_counts = [last_base["drops_queue"], last_base["drops_link"]]
    prop_counts = [last_prop["drops_queue"], last_prop["drops_link"]]

    fig = go.Figure(
        data=[
            go.Bar(name="Baseline RPL", x=categories, y=base_counts, marker_color="#ef4444"),
            go.Bar(name="BAS-RPL", x=categories, y=prop_counts, marker_color="#10b981"),
        ]
    )

    fig.update_layout(
        barmode="group",
        title="Packet Drop Breakdown",
        xaxis_title="Drop Cause",
        yaxis_title="Packets Dropped",
        plot_bgcolor="#f8fafc",
        paper_bgcolor="#ffffff",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=20, t=60, b=40),
        height=380,
    )
    return fig


def plot_delay_comparison(df_base: pd.DataFrame, df_prop: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df_base["step"],
            y=df_base["avg_e2e_delay"],
            mode="lines+markers",
            name="Baseline RPL",
            line=dict(color="#f97316", width=2.5, dash="dot"),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df_prop["step"],
            y=df_prop["avg_e2e_delay"],
            mode="lines+markers",
            name="BAS-RPL",
            line=dict(color="#06b6d4", width=2.5),
        )
    )

    fig.update_layout(
        title="Average End-to-End Delay",
        xaxis_title="Simulation Step",
        yaxis_title="Delay (steps)",
        plot_bgcolor="#f8fafc",
        paper_bgcolor="#ffffff",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=20, t=60, b=40),
        height=380,
    )
    return fig


def plot_queue_dynamics(df_base: pd.DataFrame, df_prop: pd.DataFrame) -> go.Figure:
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Peak Queue Length", "Congested Nodes (Q > 70%)")
    )

    fig.add_trace(
        go.Scatter(
            x=df_base["step"],
            y=df_base["max_queue_len"],
            mode="lines",
            name="Baseline Peak Queue",
            line=dict(color="#dc2626", width=2),
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df_prop["step"],
            y=df_prop["max_queue_len"],
            mode="lines",
            name="BAS-RPL Peak Queue",
            line=dict(color="#16a34a", width=2),
        ),
        row=1, col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df_base["step"],
            y=df_base["congested_nodes"],
            mode="lines",
            name="Baseline Congested",
            line=dict(color="#b91c1c", width=2, dash="dash"),
        ),
        row=1, col=2,
    )
    fig.add_trace(
        go.Scatter(
            x=df_prop["step"],
            y=df_prop["congested_nodes"],
            mode="lines",
            name="BAS-RPL Congested",
            line=dict(color="#15803d", width=2),
        ),
        row=1, col=2,
    )

    fig.update_layout(
        title="Queue Utilization & Congestion",
        plot_bgcolor="#f8fafc",
        paper_bgcolor="#ffffff",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
        margin=dict(l=40, r=20, t=70, b=40),
        height=380,
    )
    return fig


def plot_parent_switches(df_base: pd.DataFrame, df_prop: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df_base["step"],
            y=df_base["parent_switches"],
            mode="lines+markers",
            name="Baseline RPL",
            line=dict(color="#64748b", width=2),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df_prop["step"],
            y=df_prop["parent_switches"],
            mode="lines+markers",
            name="BAS-RPL",
            line=dict(color="#6366f1", width=2.5),
        )
    )

    fig.update_layout(
        title="Cumulative Parent Switches (Route Stability)",
        xaxis_title="Simulation Step",
        yaxis_title="Parent Switches",
        plot_bgcolor="#f8fafc",
        paper_bgcolor="#ffffff",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=20, t=60, b=40),
        height=380,
    )
    return fig


def plot_energy_consumption(df_base: pd.DataFrame, df_prop: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df_base["step"],
            y=df_base["avg_remaining_pct"],
            mode="lines",
            name="Baseline RPL",
            line=dict(color="#f43f5e", width=2),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df_prop["step"],
            y=df_prop["avg_remaining_pct"],
            mode="lines",
            name="BAS-RPL",
            line=dict(color="#0ea5e9", width=2.5),
        )
    )

    fig.update_layout(
        title="Average Remaining Energy (%)",
        xaxis_title="Simulation Step",
        yaxis_title="Remaining Battery (%)",
        yaxis=dict(range=[90, 101]),
        plot_bgcolor="#f8fafc",
        paper_bgcolor="#ffffff",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=20, t=60, b=40),
        height=380,
    )
    return fig
