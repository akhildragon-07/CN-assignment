from typing import Dict, Any
import pandas as pd
from simulator.topology import NetworkTopology
from simulator.traffic import TrafficGenerator
from simulator.simulation import SimulationEngine
from metrics.comparison import RoutingComparison
from experiments.configurations import DEFAULT_CONFIG


def run_faculty_demo(
    seed: int = 42,
    num_nodes: int = 30,
    burst_start: int = 15,
    burst_duration: int = 10,
    burst_rate: int = 2,
) -> Dict[str, Any]:
    topo = NetworkTopology(
        num_nodes=num_nodes,
        area_size=DEFAULT_CONFIG["area_size"],
        comm_range=DEFAULT_CONFIG["comm_range"],
        seed=seed,
        queue_capacity=DEFAULT_CONFIG["queue_capacity"],
        initial_energy=DEFAULT_CONFIG["initial_energy"],
    )

    traffic_gen = TrafficGenerator(
        num_nodes=num_nodes,
        mode="Sudden Burst",
        seed=seed,
        burst_start_step=burst_start,
        burst_duration=burst_duration,
        burst_rate=burst_rate,
        base_rate=0.18,
    )

    sim_baseline = SimulationEngine(
        topology=topo,
        algorithm_name="Baseline RPL",
        traffic_generator=traffic_gen,
        total_steps=DEFAULT_CONFIG["total_steps"],
        seed=seed,
    )
    history_baseline = sim_baseline.run_all()

    sim_bas_rpl = SimulationEngine(
        topology=topo,
        algorithm_name="BAS-RPL",
        traffic_generator=traffic_gen,
        total_steps=DEFAULT_CONFIG["total_steps"],
        seed=seed,
        routing_params={
            "w1_etx": DEFAULT_CONFIG["w1_etx"],
            "w2_delay": DEFAULT_CONFIG["w2_delay"],
            "w3_congestion": DEFAULT_CONFIG["w3_congestion"],
            "w4_energy": DEFAULT_CONFIG["w4_energy"],
            "base_switching_threshold": DEFAULT_CONFIG["base_switching_threshold"],
            "cooldown_steps": DEFAULT_CONFIG["cooldown_steps"],
        },
    )
    history_bas_rpl = sim_bas_rpl.run_all()

    df_base = pd.DataFrame(history_baseline)
    df_prop = pd.DataFrame(history_bas_rpl)

    comparison_runner = RoutingComparison(
        topology=topo,
        traffic_mode="Sudden Burst",
        total_steps=DEFAULT_CONFIG["total_steps"],
        seed=seed,
    )
    comparison_runner.baseline_history = history_baseline
    comparison_runner.bas_rpl_history = history_bas_rpl
    df_summary = comparison_runner.build_summary_table()

    key_events = [
        {
            "step": burst_start,
            "event": "Traffic Burst Injected",
            "description": f"Nodes {traffic_gen.burst_nodes} generate {burst_rate} packets/step.",
        },
        {
            "step": burst_start + 2,
            "event": "Congestion Begins",
            "description": "Baseline RPL stays on primary ETX path, increasing relay queue.",
        },
        {
            "step": burst_start + 3,
            "event": "Congestion Prediction",
            "description": "BAS-RPL detects rising queue growth rate and flags impending overflow.",
        },
        {
            "step": burst_start + 4,
            "event": "Parent Switch",
            "description": "BAS-RPL shifts upstream packets to secondary relay with free queue.",
        },
        {
            "step": burst_start + burst_duration,
            "event": "Burst Recovery",
            "description": "Burst subsides; queues drain and routes stabilize.",
        },
    ]

    return {
        "topology": topo,
        "df_baseline": df_base,
        "df_bas_rpl": df_prop,
        "df_summary": df_summary,
        "sim_baseline": sim_baseline,
        "sim_bas_rpl": sim_bas_rpl,
        "key_events": key_events,
    }


if __name__ == "__main__":
    results = run_faculty_demo()
    print("Benchmark Results:")
    print(results["df_summary"].to_string(index=False))
