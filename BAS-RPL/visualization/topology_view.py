from typing import Dict, Optional
import plotly.graph_objects as go
from simulator.topology import NetworkTopology


def plot_topology_graph(
    topology: NetworkTopology,
    parent_map: Optional[Dict[int, Optional[int]]] = None,
    queue_lengths: Optional[Dict[int, int]] = None,
    congestion_indices: Optional[Dict[int, float]] = None,
    energy_ratios: Optional[Dict[int, float]] = None,
    title: str = "Network Topology",
    color_by: str = "congestion",
    highlight_node: Optional[int] = None,
) -> go.Figure:
    G = topology.graph
    positions = topology.positions

    edge_x = []
    edge_y = []
    for u, v in G.edges():
        x0, y0 = positions[u]
        x1, y1 = positions[v]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    trace_bg_edges = go.Scatter(
        x=edge_x,
        y=edge_y,
        mode="lines",
        line=dict(width=1, color="rgba(180, 190, 205, 0.45)"),
        hoverinfo="none",
        name="Wireless Link",
    )

    dag_x = []
    dag_y = []
    if parent_map:
        for child, parent in parent_map.items():
            if parent is not None and child in positions and parent in positions:
                x0, y0 = positions[child]
                x1, y1 = positions[parent]
                dag_x.extend([x0, x1, None])
                dag_y.extend([y0, y1, None])

    trace_dag_edges = go.Scatter(
        x=dag_x,
        y=dag_y,
        mode="lines",
        line=dict(width=2.5, color="#1f77b4"),
        hoverinfo="none",
        name="Active Route",
    )

    sensor_nodes = [n for n in G.nodes if n != topology.gateway_id]
    sensor_x = [positions[n][0] for n in sensor_nodes]
    sensor_y = [positions[n][1] for n in sensor_nodes]

    node_colors = []
    hover_texts = []
    node_sizes = []

    for n in sensor_nodes:
        cap = G.nodes[n].get("queue_capacity", topology.queue_capacity)
        q_len = queue_lengths.get(n, 0) if queue_lengths else 0
        cong_idx = congestion_indices.get(n, 0.0) if congestion_indices else (q_len / cap if cap else 0.0)
        e_ratio = energy_ratios.get(n, 1.0) if energy_ratios else 1.0
        role = G.nodes[n].get("role", "sensor")
        curr_parent = parent_map.get(n) if parent_map else "None"
        depth = G.nodes[n].get("hop_depth", 1)

        hover_info = (
            f"<b>Node {n}</b> ({role})<br>"
            f"Hop Depth: {depth}<br>"
            f"Parent: Node {curr_parent}<br>"
            f"Queue: {q_len} / {cap} pkts<br>"
            f"Congestion: {cong_idx:.2f}<br>"
            f"Battery: {e_ratio*100:.1f}%"
        )
        hover_texts.append(hover_info)

        base_size = 22 if role == "critical_relay" else 17
        if highlight_node == n:
            base_size += 8
        node_sizes.append(base_size)

        if color_by == "congestion":
            node_colors.append(cong_idx)
        elif color_by == "energy":
            node_colors.append(e_ratio)
        elif color_by == "queue":
            node_colors.append(q_len)
        else:
            node_colors.append(depth)

    colorscale = "RdYlGn_r" if color_by in ["congestion", "queue"] else "Viridis"
    colorbar_title = "Congestion" if color_by == "congestion" else color_by.capitalize()

    trace_sensors = go.Scatter(
        x=sensor_x,
        y=sensor_y,
        mode="markers+text",
        marker=dict(
            size=node_sizes,
            color=node_colors,
            colorscale=colorscale,
            cmin=0.0,
            cmax=1.0 if color_by in ["congestion", "energy"] else None,
            colorbar=dict(title=colorbar_title, len=0.6, thickness=12, x=1.02),
            line=dict(width=1.5, color="#333333"),
            opacity=0.95,
        ),
        text=[str(n) for n in sensor_nodes],
        textposition="middle center",
        textfont=dict(size=9, color="black"),
        hoverinfo="text",
        hovertext=hover_texts,
        name="Sensors",
    )

    gw_pos = positions[topology.gateway_id]
    trace_gateway = go.Scatter(
        x=[gw_pos[0]],
        y=[gw_pos[1]],
        mode="markers+text",
        marker=dict(
            size=28,
            symbol="star",
            color="#FFD700",
            line=dict(width=2.5, color="#B8860B"),
        ),
        text=["GW (0)"],
        textposition="top center",
        textfont=dict(size=12, color="#111827", family="Arial Black"),
        hoverinfo="text",
        hovertext="<b>Gateway (Sink)</b><br>Rank: 1.0",
        name="Gateway",
    )

    fig = go.Figure(data=[trace_bg_edges, trace_dag_edges, trace_sensors, trace_gateway])

    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color="#1e293b")),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="center",
            x=0.5,
            font=dict(size=11),
        ),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor="#f8fafc",
        paper_bgcolor="#ffffff",
        margin=dict(l=20, r=20, t=50, b=50),
        height=540,
    )

    return fig
