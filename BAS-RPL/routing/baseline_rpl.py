from typing import Dict, Optional, Any
from simulator.topology import NetworkTopology
from routing.energy_manager import EnergyManager
from routing.parent_selection import ParentSelector


class BaselineRPL:
    PARENT_SWITCH_THRESHOLD = 0.05

    def __init__(self, topology: NetworkTopology, energy_manager: EnergyManager):
        self.topology = topology
        self.energy_mgr = energy_manager
        self.selector = ParentSelector(topology, energy_manager)

        self.parents: Dict[int, Optional[int]] = {n: None for n in topology.graph.nodes}
        self.ranks: Dict[int, float] = {n: float("inf") for n in topology.graph.nodes}
        self.path_etx: Dict[int, float] = {n: float("inf") for n in topology.graph.nodes}
        self.parent_switch_counts: Dict[int, int] = {n: 0 for n in topology.graph.nodes}
        self.total_switches = 0
        self.control_overhead_count = 0

        self._initialize_dag()

    def _initialize_dag(self):
        root = self.topology.gateway_id
        self.ranks[root] = 1.0
        self.path_etx[root] = 0.0
        self.parents[root] = None

        nodes_by_depth = sorted(
            [n for n in self.topology.graph.nodes if n != root],
            key=lambda x: self.topology.get_hop_depth(x),
        )

        for u in nodes_by_depth:
            self._select_best_parent(u, initial=True)

    def _select_best_parent(self, node_id: int, initial: bool = False):
        candidates = self.selector.get_candidate_parents(node_id, self.parents, self.ranks)
        if not candidates:
            return

        current_parent = self.parents[node_id]
        current_cost = self.path_etx[node_id] if current_parent is not None else float("inf")

        best_parent = None
        best_cost = float("inf")

        for cand in candidates:
            link_info = self.topology.get_link_info(node_id, cand)
            link_etx = link_info.get("etx", 1.5)
            cand_path_etx = self.path_etx.get(cand, float("inf"))
            total_cand_etx = cand_path_etx + link_etx

            if total_cand_etx < best_cost:
                best_cost = total_cand_etx
                best_parent = cand

        if best_parent is None:
            return

        should_switch = initial or (current_parent is None) or (best_cost < current_cost - self.PARENT_SWITCH_THRESHOLD)

        if current_parent is not None and self.energy_mgr.is_dead(current_parent):
            should_switch = True

        if should_switch and (best_parent != current_parent):
            self.parents[node_id] = best_parent
            self.path_etx[node_id] = best_cost
            link_info = self.topology.get_link_info(node_id, best_parent)
            self.ranks[node_id] = self.ranks[best_parent] + link_info.get("etx", 1.0)
            if not initial:
                self.parent_switch_counts[node_id] += 1
                self.total_switches += 1
                self.control_overhead_count += 2
                self.energy_mgr.consume_control(node_id, 2)
        elif current_parent is not None:
            link_info = self.topology.get_link_info(node_id, current_parent)
            self.path_etx[node_id] = self.path_etx[current_parent] + link_info.get("etx", 1.5)
            self.ranks[node_id] = self.ranks[current_parent] + link_info.get("etx", 1.0)

    def update_routing(self, step: int, node_queues: Optional[Dict[int, int]] = None):
        self.control_overhead_count += self.topology.num_nodes // 4

        nodes_by_depth = sorted(
            [n for n in self.topology.graph.nodes if n != self.topology.gateway_id],
            key=lambda x: self.topology.get_hop_depth(x),
        )

        for node_id in nodes_by_depth:
            self._select_best_parent(node_id, initial=False)

    def get_next_hop(self, current_node: int) -> Optional[int]:
        if current_node == self.topology.gateway_id:
            return None
        return self.parents.get(current_node)

    def get_parent_map(self) -> Dict[int, Optional[int]]:
        return dict(self.parents)

    def get_metrics_summary(self) -> Dict[str, Any]:
        return {
            "algorithm": "Baseline RPL",
            "total_parent_switches": self.total_switches,
            "control_overhead_packets": self.control_overhead_count,
            "connected_to_root_count": sum(1 for n, p in self.parents.items() if p is not None or n == 0),
        }
