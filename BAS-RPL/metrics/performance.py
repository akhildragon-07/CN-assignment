from typing import Dict, List, Any
import pandas as pd
from simulator.packet import Packet


class PerformanceEvaluator:
    @staticmethod
    def compute_summary_metrics(
        all_packets: Dict[int, Packet],
        delivered_packets: List[Packet],
        dropped_packets: List[Packet],
        energy_stats: Dict[str, Any],
        routing_stats: Dict[str, Any],
        max_queue_observed: int = 0,
    ) -> Dict[str, Any]:
        total_gen = len(all_packets)
        delivered_count = len(delivered_packets)
        dropped_count = len(dropped_packets)

        pdr = (delivered_count / total_gen * 100.0) if total_gen > 0 else 0.0
        plr = (dropped_count / total_gen * 100.0) if total_gen > 0 else 0.0

        queue_drops = sum(1 for p in dropped_packets if p.status == Packet.STATUS_DROPPED_QUEUE)
        link_drops = sum(1 for p in dropped_packets if p.status == Packet.STATUS_DROPPED_LINK)
        loop_drops = sum(1 for p in dropped_packets if p.status == Packet.STATUS_DROPPED_LOOP)
        ttl_drops = sum(1 for p in dropped_packets if p.status == Packet.STATUS_DROPPED_TTL)

        delays = [p.e2e_delay for p in delivered_packets if p.e2e_delay is not None]
        avg_delay = (sum(delays) / len(delays)) if delays else 0.0
        max_delay = max(delays) if delays else 0.0
        min_delay = min(delays) if delays else 0.0

        return {
            "packets_generated": total_gen,
            "packets_delivered": delivered_count,
            "packets_dropped": dropped_count,
            "pdr_percent": round(pdr, 2),
            "plr_percent": round(plr, 2),
            "queue_drops": queue_drops,
            "link_drops": link_drops,
            "loop_drops": loop_drops,
            "ttl_drops": ttl_drops,
            "avg_e2e_delay_steps": round(avg_delay, 2),
            "min_e2e_delay_steps": round(min_delay, 2),
            "max_e2e_delay_steps": round(max_delay, 2),
            "total_energy_consumed_j": energy_stats.get("total_consumed_energy", 0.0),
            "avg_remaining_energy_pct": energy_stats.get("avg_remaining_pct", 100.0),
            "min_node_energy_j": energy_stats.get("min_node_energy", 0.0),
            "dead_nodes_count": energy_stats.get("dead_nodes_count", 0),
            "total_parent_switches": routing_stats.get("total_parent_switches", 0),
            "routing_control_overhead": routing_stats.get("control_overhead_packets", 0),
            "max_queue_observed": max_queue_observed,
        }

    @staticmethod
    def to_dataframe(history: List[Dict[str, Any]]) -> pd.DataFrame:
        return pd.DataFrame(history)
