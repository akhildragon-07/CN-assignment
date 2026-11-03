import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import streamlit as st
import pandas as pd

from simulator.topology import NetworkTopology
from simulator.traffic import TrafficGenerator
from simulator.simulation import SimulationEngine
from metrics.comparison import RoutingComparison
from visualization.topology_view import plot_topology_graph
from visualization.charts import (
    plot_pdr_comparison,
    plot_packet_drops_breakdown,
    plot_delay_comparison,
    plot_queue_dynamics,
    plot_parent_switches,
    plot_energy_consumption,
)
from experiments.configurations import DEFAULT_CONFIG
from experiments.demo_scenario import run_faculty_demo

st.set_page_config(
    page_title="BAS-RPL Simulator",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .main-title {
        font-size: 2rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #475569;
        margin-bottom: 1.2rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 0.95rem;
        font-weight: 600;
        padding: 8px 16px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def get_or_create_topology(num_nodes: int, seed: int) -> NetworkTopology:
    key = f"topo_{num_nodes}_{seed}"
    if key not in st.session_state:
        st.session_state[key] = NetworkTopology(
            num_nodes=num_nodes,
            seed=seed,
            queue_capacity=DEFAULT_CONFIG["queue_capacity"],
            initial_energy=DEFAULT_CONFIG["initial_energy"],
        )
    return st.session_state[key]


if "demo_results" not in st.session_state:
    st.session_state.demo_results = None

if "comparison_results" not in st.session_state:
    st.session_state.comparison_results = None

if "live_sim" not in st.session_state:
    st.session_state.live_sim = None

with st.sidebar:
    st.markdown("### Simulation Settings")

    num_nodes = st.radio(
        "Node Count:",
        options=[30, 50],
        index=0,
    )

    traffic_mode = st.selectbox(
        "Traffic Pattern:",
        options=["Sudden Burst", "Periodic", "Mixed", "High Congestion"],
        index=0,
    )

    sim_steps = st.slider("Simulation Steps:", min_value=25, max_value=80, value=50, step=5)
    random_seed = st.number_input("Random Seed:", min_value=1, max_value=9999, value=42)

    st.markdown("---")
    st.markdown("### BAS-RPL Parameters")
    with st.expander("Cost Function Weights", expanded=False):
        w1_etx = st.slider("w1 (ETX):", 0.0, 1.0, 0.35, 0.05)
        w2_delay = st.slider("w2 (Delay):", 0.0, 1.0, 0.15, 0.05)
        w3_cong = st.slider("w3 (Congestion):", 0.0, 1.0, 0.35, 0.05)
        w4_energy = st.slider("w4 (Energy):", 0.0, 1.0, 0.15, 0.05)
        sw_thresh = st.slider("Switching Threshold:", 0.05, 0.40, 0.18, 0.01)
        cooldown = st.slider("Cooldown Steps:", 1, 8, 4, 1)

    st.markdown("---")
    if st.button("Run Predefined Demo Scenario", type="primary", use_container_width=True):
        with st.spinner("Running simulation benchmark..."):
            st.session_state.demo_results = run_faculty_demo(
                seed=int(random_seed),
                num_nodes=int(num_nodes),
                burst_start=15,
                burst_duration=10,
                burst_rate=2,
            )
            st.success("Simulation finished successfully!")

    if st.button("Reset Network", use_container_width=True):
        st.session_state.clear()
        st.rerun()

st.markdown(
    '<div class="main-title">BAS-RPL: Burst-Aware Stability-Constrained Routing Protocol</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="sub-title">Performance Evaluation of Proposed BAS-RPL vs Standard RPL (MRHOF) in Wireless Sensor Networks</div>',
    unsafe_allow_html=True,
)

topo = get_or_create_topology(num_nodes, random_seed)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Topology & Network",
    "Live Simulation",
    "Performance Comparison",
    "Graphical Analysis",
    "Protocol & Design",
])

with tab1:
    st.subheader("Network Deployment & Topology")
    st.write(
        "Deployment field with wireless sensor nodes and a central root Gateway (Node 0 at top-center). "
        "Links represent physical communication ranges with realistic packet reception ratios and transmission counts."
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Nodes", topo.num_nodes)
    with col2:
        st.metric("Total Links", topo.graph.number_of_edges())
    with col3:
        st.metric("Average Degree", f"{2.0 * topo.graph.number_of_edges() / topo.num_nodes:.1f}")
    with col4:
        max_d = max(topo.graph.nodes[n]["hop_depth"] for n in topo.graph.nodes)
        st.metric("Maximum Hop Depth", f"{max_d} hops")

    st.markdown("---")

    col_ctrl, col_chart = st.columns([1, 3])
    with col_ctrl:
        color_by = st.selectbox(
            "Node Color Attribute:",
            options=["congestion", "queue", "energy", "role"],
            index=0,
            format_func=lambda x: {
                "congestion": "Congestion Index",
                "queue": "Queue Occupancy",
                "energy": "Remaining Battery",
                "role": "Topological Depth / Role",
            }[x],
        )

        show_dag = st.checkbox("Show Initial Parent Routes", value=True)

        st.info(
            "**Legend**:\n"
            "- ⭐ **Gateway (0)**: Sink node\n"
            "- 🟢 **Relay Nodes**: Intermediate forwarders\n"
            "- 🔵 **Sensors**: Source nodes"
        )

    sim_init = SimulationEngine(topo, algorithm_name="Baseline RPL", total_steps=1, seed=random_seed)
    parent_map = sim_init.routing.get_parent_map() if show_dag else None

    with col_chart:
        fig_topo = plot_topology_graph(
            topology=topo,
            parent_map=parent_map,
            color_by=color_by,
            title=f"Sensor Network Topology ({topo.num_nodes} Nodes)",
        )
        st.plotly_chart(fig_topo, use_container_width=True)

    with st.expander("Node Details Table"):
        records = []
        for n in topo.graph.nodes:
            records.append({
                "Node ID": n,
                "Role": topo.graph.nodes[n].get("role", "sensor"),
                "Hop Depth": topo.graph.nodes[n].get("hop_depth", 0),
                "Neighbors": topo.graph.degree[n],
                "Battery (J)": round(topo.graph.nodes[n].get("initial_energy", 100.0), 1),
                "Queue Capacity": topo.graph.nodes[n].get("queue_capacity", 20),
                "Location": f"({topo.positions[n][0]:.1f}, {topo.positions[n][1]:.1f})",
            })
        st.dataframe(pd.DataFrame(records), use_container_width=True, height=240)

with tab2:
    st.subheader("Step-by-Step Simulation Execution")

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        algo_choice = st.selectbox("Routing Protocol:", ["BAS-RPL", "Baseline RPL"], index=0)
    with col_s2:
        stepper_mode = st.radio("Run Mode:", ["Step-by-Step", "Run to Completion"], horizontal=True)

    engine_key = f"engine_{algo_choice}_{num_nodes}_{traffic_mode}_{sim_steps}_{random_seed}"
    if engine_key not in st.session_state:
        traffic_gen = TrafficGenerator(
            num_nodes=num_nodes,
            mode=traffic_mode,
            seed=random_seed,
            burst_start_step=15,
            burst_duration=10,
            burst_rate=2,
            base_rate=0.18,
        )
        st.session_state[engine_key] = SimulationEngine(
            topology=topo,
            algorithm_name=algo_choice,
            traffic_generator=traffic_gen,
            total_steps=sim_steps,
            seed=random_seed,
            routing_params={
                "w1_etx": w1_etx,
                "w2_delay": w2_delay,
                "w3_congestion": w3_cong,
                "w4_energy": w4_energy,
                "base_switching_threshold": sw_thresh,
                "cooldown_steps": cooldown,
            },
        )

    current_engine: SimulationEngine = st.session_state[engine_key]

    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("▶ Next Step", use_container_width=True):
            if not current_engine.is_completed:
                current_engine.step()
                st.rerun()
            else:
                st.warning("Simulation finished.")
    with b2:
        if st.button("⏩ Run All", use_container_width=True):
            with st.spinner("Running simulation steps..."):
                current_engine.run_all()
                st.rerun()
    with b3:
        if st.button("Reset Simulation", use_container_width=True):
            del st.session_state[engine_key]
            st.rerun()

    latest_metrics = current_engine.get_latest_metrics()
    step_now = current_engine.current_step

    st.markdown(f"**Step:** `{step_now} / {sim_steps}`")

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    with m1:
        st.metric("Generated", latest_metrics.get("packets_generated", 0))
    with m2:
        st.metric("Delivered", latest_metrics.get("packets_delivered", 0))
    with m3:
        st.metric("Total Drops", latest_metrics.get("packets_dropped", 0))
    with m4:
        st.metric("PDR", f"{latest_metrics.get('pdr', 100.0):.1f}%")
    with m5:
        st.metric("Queue Drops", latest_metrics.get("drops_queue", 0))
    with m6:
        st.metric("Parent Switches", latest_metrics.get("parent_switches", 0))

    col_graph, col_logs = st.columns([3, 2])
    with col_graph:
        active_parent_map = current_engine.routing.get_parent_map()
        active_queues = current_engine.network.get_queue_lengths()

        fig_live = plot_topology_graph(
            topology=topo,
            parent_map=active_parent_map,
            queue_lengths=active_queues,
            color_by="queue",
            title=f"Step {step_now}: Routes & Queue Levels ({algo_choice})",
        )
        st.plotly_chart(fig_live, use_container_width=True)

    with col_logs:
        st.markdown("**Recent Packet Hops:**")
        recent_tx = current_engine.step_transmission_logs.get(max(0, step_now - 1), [])
        if recent_tx:
            log_entries = []
            for sender, receiver, success, pkt_id in recent_tx[-12:]:
                status_icon = "✓" if success else "✗"
                target_label = "Gateway" if receiver == 0 else f"Node {receiver}"
                log_entries.append(f"{status_icon} Pkt #{pkt_id}: Node {sender} -> {target_label}")
            st.text_area("Hops", "\n".join(log_entries), height=320, label_visibility="collapsed")
        else:
            st.info("No transmissions in the last step.")

        if step_now >= 15 and step_now <= 25 and traffic_mode == "Sudden Burst":
            st.warning("Burst window active on cluster nodes.")

with tab3:
    st.subheader("Benchmark Comparison")

    if st.button("Run Side-by-Side Comparison", type="primary"):
        with st.spinner("Evaluating Baseline RPL and BAS-RPL..."):
            runner = RoutingComparison(
                topology=topo,
                traffic_mode=traffic_mode,
                total_steps=sim_steps,
                seed=random_seed,
                bas_rpl_params={
                    "w1_etx": w1_etx,
                    "w2_delay": w2_delay,
                    "w3_congestion": w3_cong,
                    "w4_energy": w4_energy,
                    "base_switching_threshold": sw_thresh,
                    "cooldown_steps": cooldown,
                },
            )
            df_b, df_p, df_sum = runner.run_benchmark()
            st.session_state.comparison_results = {
                "df_base": df_b,
                "df_prop": df_p,
                "df_summary": df_sum,
            }

    results_to_show = None
    if st.session_state.comparison_results is not None:
        results_to_show = st.session_state.comparison_results
    elif st.session_state.demo_results is not None:
        results_to_show = {
            "df_base": st.session_state.demo_results["df_baseline"],
            "df_prop": st.session_state.demo_results["df_bas_rpl"],
            "df_summary": st.session_state.demo_results["df_summary"],
        }

    if results_to_show:
        df_base = results_to_show["df_base"]
        df_prop = results_to_show["df_prop"]
        df_sum = results_to_show["df_summary"]

        last_b = df_base.iloc[-1]
        last_p = df_prop.iloc[-1]

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            diff_pdr = last_p["pdr"] - last_b["pdr"]
            st.metric("Packet Delivery Ratio", f"{last_p['pdr']:.1f}%", f"{diff_pdr:+.1f}%")
        with c2:
            diff_drops = last_p["drops_queue"] - last_b["drops_queue"]
            st.metric("Queue Drops", last_p["drops_queue"], f"{diff_drops:+d}", delta_color="inverse")
        with c3:
            st.metric("Parent Switches", last_p["parent_switches"], f"{last_p['parent_switches'] - last_b['parent_switches']:+d}")
        with c4:
            st.metric("Control Overhead", f"{last_p['control_overhead']} pkts", f"{last_p['control_overhead'] - last_b['control_overhead']:+d}", delta_color="inverse")

        st.markdown("---")
        st.dataframe(df_sum, use_container_width=True, hide_index=True)

        st.markdown("### Observations")
        st.write(
            f"- **Buffer Loss Prevention:** Baseline RPL had **{last_b['drops_queue']} buffer overflow drops**, while BAS-RPL had **{last_p['drops_queue']} drops** (a reduction of **{last_b['drops_queue'] - last_p['drops_queue']} drops**).\n"
            f"- **Root Cause:** Standard RPL only considers link ETX. When traffic surges, it keeps funneling packets into the same bottleneck relay until buffers drop packets.\n"
            f"- **Adaptive Cost:** BAS-RPL predicts queue growth and routes around congested nodes using alternate parents before buffers fill up.\n"
            f"- **Route Stability:** The cooldown parameter and switching threshold prevent the nodes from constantly oscillating between parents."
        )
    else:
        st.info("Run the comparison using the button above or from the sidebar.")

with tab4:
    st.subheader("Performance Charts")

    data_ready = False
    if st.session_state.comparison_results:
        df_b = st.session_state.comparison_results["df_base"]
        df_p = st.session_state.comparison_results["df_prop"]
        data_ready = True
    elif st.session_state.demo_results:
        df_b = st.session_state.demo_results["df_baseline"]
        df_p = st.session_state.demo_results["df_bas_rpl"]
        data_ready = True

    if data_ready:
        g1, g2 = st.columns(2)
        with g1:
            st.plotly_chart(plot_pdr_comparison(df_b, df_p), use_container_width=True)
        with g2:
            st.plotly_chart(plot_packet_drops_breakdown(df_b, df_p), use_container_width=True)

        g3, g4 = st.columns(2)
        with g3:
            st.plotly_chart(plot_queue_dynamics(df_b, df_p), use_container_width=True)
        with g4:
            st.plotly_chart(plot_delay_comparison(df_b, df_p), use_container_width=True)

        g5, g6 = st.columns(2)
        with g5:
            st.plotly_chart(plot_parent_switches(df_b, df_p), use_container_width=True)
        with g6:
            st.plotly_chart(plot_energy_consumption(df_b, df_p), use_container_width=True)

        st.markdown("---")
        st.subheader("Route Shift During Burst")

        b1, b2 = st.columns(2)
        with b1:
            step_pre = 14
            parent_pre = df_p.iloc[step_pre]["parent_map"] if len(df_p) > step_pre else df_p.iloc[0]["parent_map"]
            queues_pre = df_p.iloc[step_pre]["queue_lengths"] if len(df_p) > step_pre else df_p.iloc[0]["queue_lengths"]
            fig_pre = plot_topology_graph(
                topo, parent_map=parent_pre, queue_lengths=queues_pre,
                title=f"Step {step_pre}: Before Burst"
            )
            st.plotly_chart(fig_pre, use_container_width=True)

        with b2:
            step_post = 20
            parent_post = df_p.iloc[step_post]["parent_map"] if len(df_p) > step_post else df_p.iloc[-1]["parent_map"]
            queues_post = df_p.iloc[step_post]["queue_lengths"] if len(df_p) > step_post else df_p.iloc[-1]["queue_lengths"]
            fig_post = plot_topology_graph(
                topo, parent_map=parent_post, queue_lengths=queues_post,
                title=f"Step {step_post}: During Burst (Rerouted)"
            )
            st.plotly_chart(fig_post, use_container_width=True)
    else:
        st.info("Run the comparison in Tab 3 to view graphs.")

with tab5:
    st.subheader("Protocol Details & Mathematical Formulation")

    st.markdown(
        """
        ### 1. Problem Overview
        Standard RPL (RFC 6550 / RFC 6719) routes packets using MRHOF based on path ETX:
        $$\\text{PathETX}(u) = \\text{PathETX}(p) + \\text{LinkETX}(u, p)$$
        Because ETX measures radio link retransmissions rather than queue lengths, all sensors route through the same bottleneck relay during sudden bursts, causing queue drop-tail drops.

        ---

        ### 2. BAS-RPL Mechanism

        #### A. Queue Growth Prediction
        Monitors queue length velocity over time:
        $$\\Delta Q(t) = \\frac{Q(t) - Q(t-1)}{\\Delta t}$$
        Smoothed using an Exponential Moving Average (EMA):
        $$\\text{EMA}(t) = \\alpha \\cdot \\Delta Q(t) + (1 - \\alpha) \\cdot \\text{EMA}(t-1)$$
        Lookahead projected queue:
        $$Q_{\\text{pred}}(t) = \\max(0, Q(t) + H \\cdot \\text{EMA}(t))$$
        Normalized to congestion index:
        $$C(t) = \\min\\left(1.0, \\frac{Q_{\\text{pred}}(t)}{Q_{\\max}}\\right)$$

        #### B. Multi-Objective Cost Function
        $$\\text{Cost}(i, j) = w_1 \\cdot \\widehat{\\text{ETX}} + w_2 \\cdot \\widehat{\\text{Delay}} + w_3 \\cdot \\widehat{\\text{Congestion}} + w_4 \\cdot \\widehat{\\text{EnergyPenalty}}$$
        Weights: $w_1 = 0.35, w_2 = 0.15, w_3 = 0.35, w_4 = 0.15$.

        #### C. Route Stability & Loop Prevention
        - **Cooldown Period:** Nodes must wait $T_{\\text{cooldown}}$ steps between parent switches.
        - **Switching Threshold:** An alternative candidate must provide at least an 18% improvement over current parent.
        - **Loop Prevention:** Candidate parents must strictly have a lower hop depth or lower DAG rank, verified by an acyclic path check.
        """
    )

    st.markdown("### 3. Core Algorithm Logic")
    st.code(
        """
Algorithm: BAS-RPL Parent Selection
Input: Node i, Candidate Neighbors N(i), Current Parent p_curr
Output: Selected Parent

1:  Update queue lengths Q(t)
2:  For each node v:
3:      Delta_Q <- (Q(t) - Q(t-1)) / dt
4:      EMA <- alpha * Delta_Q + (1 - alpha) * EMA
5:      Q_pred <- max(0, Q(t) + H * EMA)
6:      Congestion[v] <- min(1.0, Q_pred / Q_max)
7:  EndFor
8:
9:  Candidates <- { v in N(i) | Depth(v) < Depth(i) and v is alive and LoopFree(i, v) }
10: best_cand <- NULL, best_cost <- INFINITY
11: For each cand in Candidates:
12:     Cost <- w1*ETX + w2*Delay + w3*Congestion[cand] + w4*EnergyPenalty[cand]
13:     If Cost < best_cost:
14:         best_cost <- Cost
15:         best_cand <- cand
16: EndFor
17:
18: CooldownDone <- (Step - LastSwitch[i] >= T_cooldown)
19: SignificantImprovement <- (best_cost + SwitchPenalty < CurrentCost * (1 - delta_switch))
20:
21: If p_curr is NULL or p_curr is Dead or (CooldownDone and SignificantImprovement):
22:     p_curr <- best_cand
23:     LastSwitch[i] <- Step
24: EndIf
25: Return p_curr
        """,
        language="text",
    )

    st.markdown("### 4. Implementation Notes")
    with st.expander("Loop Prevention Verification", expanded=True):
        st.write(
            "Every candidate parent is checked for monotonic hop-depth/rank ordering. "
            "In addition, an upstream path traversal check (`ParentSelector._creates_cycle`) verifies that "
            "the node itself never appears in the candidate's upstream path to the Gateway."
        )

    with st.expander("Delay vs Drop Trade-off"):
        st.write(
            "When BAS-RPL diverts traffic to secondary relays, packets may traverse an extra hop or use slightly "
            "higher latency links. This is a realistic networking trade-off that trades a fraction of a millisecond "
            "of delay to prevent catastrophic packet drops."
        )
