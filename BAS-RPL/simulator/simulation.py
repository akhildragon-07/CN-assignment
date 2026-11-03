from typing import Dict, List, Optional, Any
from simulator.topology import NetworkTopology
from simulator.traffic import TrafficGenerator
from simulator.network import Network
from simulator.packet import Packet
from routing.energy_manager import EnergyManager
from routing.baseline_rpl import BaselineRPL
from routing.bas_rpl import BASRPL


class SimulationEngine:
    def __init__(
        self,
        topology: NetworkTopology,
        algorithm_name: str = "BAS-RPL",
        traffic_generator: Optional[TrafficGenerator] = None,
        total_steps: int = 50,
        seed: int = 42,
        routing_params: Optional[Dict[str, Any]] = None,
    ):
        self.topology = topology
        self.algorithm_name = algorithm_name
        self.total_steps = total_steps
        self.seed = seed
        self.current_step = 0
        self.is_completed = False

        if traffic_generator is None:
            self.traffic_gen = TrafficGenerator(num_nodes=topology.num_nodes, seed=seed)
        else:
            self.traffic_gen = traffic_generator

        self.packet_schedule = self.traffic_gen.generate_schedule(total_steps=total_steps)

        init_energy_map = {n: topology.graph.nodes[n]["initial_energy"] for n in topology.graph.nodes}
        self.energy_mgr = EnergyManager(init_energy_map)

        self.network = Network(
            topology=self.topology,
            energy_manager=self.energy_mgr,
            service_rate=2,
            max_link_retries=2,
            seed=seed,
        )

        params = routing_params or {}
        if algorithm_name == "Baseline RPL":
            self.routing = BaselineRPL(topology=self.topology, energy_manager=self.energy_mgr)
        else:
            self.routing = BASRPL(
                topology=self.topology,
                energy_manager=self.energy_mgr,
                w1_etx=params.get("w1_etx", 0.35),
                w2_delay=params.get("w2_delay", 0.15),
                w3_congestion=params.get("w3_congestion", 0.35),
                w4_energy=params.get("w4_energy", 0.15),
                base_switching_threshold=params.get("base_switching_threshold", 0.18),
                cooldown_steps=params.get("cooldown_steps", 4),
            )

        self.metrics_history: List[Dict[str, Any]] = []
        self.step_transmission_logs: Dict[int, List[Any]] = {}

    def step(self) -> Dict[str, Any]:
        if self.current_step >= self.total_steps:
            self.is_completed = True
            return self.get_latest_metrics()

        step = self.current_step

        current_queues = self.network.get_queue_lengths()
        self.routing.update_routing(step=step, node_queues=current_queues)

        new_packets = self.packet_schedule.get(step, [])
        self.network.inject_packets(new_packets, step=step)

        tx_log = self.network.process_hop_forwarding(self.routing, step=step)
        self.step_transmission_logs[step] = tx_log

        step_metrics = self._calculate_step_metrics(step)
        self.metrics_history.append(step_metrics)

        self.current_step += 1
        if self.current_step >= self.total_steps:
            self.is_completed = True

        return step_metrics

    def run_all(self) -> List[Dict[str, Any]]:
        while not self.is_completed:
            self.step()
        return self.metrics_history

    def _calculate_step_metrics(self, step: int) -> Dict[str, Any]:
        all_pkts = list(self.network.all_packets.values())
        total_gen = len(all_pkts)
        delivered_pkts = self.network.delivered_packets
        dropped_pkts = self.network.dropped_packets

        delivered_count = len(delivered_pkts)
        dropped_count = len(dropped_pkts)
        in_flight_count = sum(1 for p in all_pkts if p.status == Packet.STATUS_IN_FLIGHT)

        pdr = (delivered_count / total_gen * 100.0) if total_gen > 0 else 100.0
        plr = (dropped_count / total_gen * 100.0) if total_gen > 0 else 0.0

        drops_queue = sum(1 for p in dropped_pkts if p.status == Packet.STATUS_DROPPED_QUEUE)
        drops_link = sum(1 for p in dropped_pkts if p.status == Packet.STATUS_DROPPED_LINK)
        drops_loop = sum(1 for p in dropped_pkts if p.status == Packet.STATUS_DROPPED_LOOP)
        drops_ttl = sum(1 for p in dropped_pkts if p.status == Packet.STATUS_DROPPED_TTL)

        if delivered_pkts:
            avg_delay = sum(p.e2e_delay for p in delivered_pkts if p.e2e_delay is not None) / len(delivered_pkts)
        else:
            avg_delay = 0.0

        energy_stats = self.energy_mgr.get_network_energy_stats()
        routing_stats = self.routing.get_metrics_summary()

        queue_lengths = self.network.get_queue_lengths()
        max_queue = max(queue_lengths.values()) if queue_lengths else 0
        avg_queue = sum(queue_lengths.values()) / len(queue_lengths) if queue_lengths else 0

        congested_nodes_count = sum(1 for q in queue_lengths.values() if q >= self.topology.queue_capacity * 0.70)

        return {
            "step": step,
            "algorithm": self.algorithm_name,
            "packets_generated": total_gen,
            "packets_delivered": delivered_count,
            "packets_dropped": dropped_count,
            "packets_in_flight": in_flight_count,
            "pdr": round(pdr, 2),
            "plr": round(plr, 2),
            "drops_queue": drops_queue,
            "drops_link": drops_link,
            "drops_loop": drops_loop,
            "drops_ttl": drops_ttl,
            "avg_e2e_delay": round(avg_delay, 2),
            "parent_switches": routing_stats.get("total_parent_switches", 0),
            "control_overhead": routing_stats.get("control_overhead_packets", 0),
            "total_consumed_energy": energy_stats.get("total_consumed_energy", 0.0),
            "avg_remaining_pct": energy_stats.get("avg_remaining_pct", 100.0),
            "min_node_energy": energy_stats.get("min_node_energy", 0.0),
            "dead_nodes": energy_stats.get("dead_nodes_count", 0),
            "max_queue_len": max_queue,
            "avg_queue_len": round(avg_queue, 2),
            "congested_nodes": congested_nodes_count,
            "parent_map": self.routing.get_parent_map(),
            "queue_lengths": queue_lengths,
        }

    def get_latest_metrics(self) -> Dict[str, Any]:
        if self.metrics_history:
            return self.metrics_history[-1]
        return self._calculate_step_metrics(0)
