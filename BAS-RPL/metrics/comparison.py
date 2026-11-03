from typing import Dict, Any, Tuple
import pandas as pd
from simulator.topology import NetworkTopology
from simulator.traffic import TrafficGenerator
from simulator.simulation import SimulationEngine


class RoutingComparison:
    def __init__(
        self,
        topology: NetworkTopology,
        traffic_mode: str = "Sudden Burst",
        total_steps: int = 50,
        seed: int = 42,
        bas_rpl_params: Dict[str, Any] = None,
    ):
        self.topology = topology
        self.traffic_mode = traffic_mode
        self.total_steps = total_steps
        self.seed = seed
        self.bas_rpl_params = bas_rpl_params or {}

        self.traffic_gen = TrafficGenerator(
            num_nodes=topology.num_nodes,
            mode=traffic_mode,
            seed=seed,
            burst_start_step=15,
            burst_duration=10,
            burst_rate=2,
            base_rate=0.18,
        )

        self.sim_baseline: SimulationEngine = None
        self.sim_bas_rpl: SimulationEngine = None
        self.baseline_history = []
        self.bas_rpl_history = []

    def run_benchmark(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        self.sim_baseline = SimulationEngine(
            topology=self.topology,
            algorithm_name="Baseline RPL",
            traffic_generator=self.traffic_gen,
            total_steps=self.total_steps,
            seed=self.seed,
        )
        self.baseline_history = self.sim_baseline.run_all()

        self.sim_bas_rpl = SimulationEngine(
            topology=self.topology,
            algorithm_name="BAS-RPL",
            traffic_generator=self.traffic_gen,
            total_steps=self.total_steps,
            seed=self.seed,
            routing_params=self.bas_rpl_params,
        )
        self.bas_rpl_history = self.sim_bas_rpl.run_all()

        df_base = pd.DataFrame(self.baseline_history)
        df_prop = pd.DataFrame(self.bas_rpl_history)
        df_summary = self.build_summary_table()
        return df_base, df_prop, df_summary

    def build_summary_table(self) -> pd.DataFrame:
        if not self.baseline_history or not self.bas_rpl_history:
            return pd.DataFrame()

        last_base = self.baseline_history[-1]
        last_prop = self.bas_rpl_history[-1]

        rows = [
            {
                "Metric": "Packet Delivery Ratio (PDR)",
                "Baseline RPL": f"{last_base['pdr']:.1f}%",
                "BAS-RPL": f"{last_prop['pdr']:.1f}%",
                "Difference": f"{last_prop['pdr'] - last_base['pdr']:+.1f}%",
            },
            {
                "Metric": "Packets Delivered",
                "Baseline RPL": last_base["packets_delivered"],
                "BAS-RPL": last_prop["packets_delivered"],
                "Difference": f"{last_prop['packets_delivered'] - last_base['packets_delivered']:+d}",
            },
            {
                "Metric": "Buffer Overflow Drops",
                "Baseline RPL": last_base["drops_queue"],
                "BAS-RPL": last_prop["drops_queue"],
                "Difference": f"{last_prop['drops_queue'] - last_base['drops_queue']:+d}",
            },
            {
                "Metric": "Channel Loss Drops",
                "Baseline RPL": last_base["drops_link"],
                "BAS-RPL": last_prop["drops_link"],
                "Difference": f"{last_prop['drops_link'] - last_base['drops_link']:+d}",
            },
            {
                "Metric": "Average End-to-End Delay",
                "Baseline RPL": f"{last_base['avg_e2e_delay']:.2f} steps",
                "BAS-RPL": f"{last_prop['avg_e2e_delay']:.2f} steps",
                "Difference": f"{last_prop['avg_e2e_delay'] - last_base['avg_e2e_delay']:+.2f} steps",
            },
            {
                "Metric": "Peak Queue Length",
                "Baseline RPL": max(h["max_queue_len"] for h in self.baseline_history),
                "BAS-RPL": max(h["max_queue_len"] for h in self.bas_rpl_history),
                "Difference": f"{max(h['max_queue_len'] for h in self.bas_rpl_history) - max(h['max_queue_len'] for h in self.baseline_history):+d}",
            },
            {
                "Metric": "Parent Route Switches",
                "Baseline RPL": last_base["parent_switches"],
                "BAS-RPL": last_prop["parent_switches"],
                "Difference": f"{last_prop['parent_switches'] - last_base['parent_switches']:+d}",
            },
            {
                "Metric": "Energy Consumed",
                "Baseline RPL": f"{last_base['total_consumed_energy']:.2f} J",
                "BAS-RPL": f"{last_prop['total_consumed_energy']:.2f} J",
                "Difference": f"{last_prop['total_consumed_energy'] - last_base['total_consumed_energy']:+.2f} J",
            },
            {
                "Metric": "Average Remaining Energy",
                "Baseline RPL": f"{last_base['avg_remaining_pct']:.1f}%",
                "BAS-RPL": f"{last_prop['avg_remaining_pct']:.1f}%",
                "Difference": f"{last_prop['avg_remaining_pct'] - last_base['avg_remaining_pct']:+.1f}%",
            },
            {
                "Metric": "Control Packet Overhead",
                "Baseline RPL": f"{last_base['control_overhead']}",
                "BAS-RPL": f"{last_prop['control_overhead']}",
                "Difference": f"{last_prop['control_overhead'] - last_base['control_overhead']:+d}",
            },
        ]

        return pd.DataFrame(rows)
