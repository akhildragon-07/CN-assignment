from typing import Dict, Optional, List, Tuple, Any
from simulator.topology import NetworkTopology
from routing.energy_manager import EnergyManager
from routing.congestion_predictor import CongestionPredictor
from routing.parent_selection import ParentSelector


class BASRPL:
    def __init__(
        self,
        topology: NetworkTopology,
        energy_manager: EnergyManager,
        w1_etx: float = 0.35,
        w2_delay: float = 0.15,
        w3_congestion: float = 0.35,
        w4_energy: float = 0.15,
        base_switching_threshold: float = 0.18,
        cooldown_steps: int = 4,
    ):
        self.topology = topology
        self.energy_mgr = energy_manager
        self.selector = ParentSelector(topology, energy_manager)

        total_w = w1_etx + w2_delay + w3_congestion + w4_energy
        self.w1 = w1_etx / total_w
        self.w2 = w2_delay / total_w
        self.w3 = w3_congestion / total_w
        self.w4 = w4_energy / total_w

        self.base_switching_threshold = base_switching_threshold
        self.cooldown_steps = cooldown_steps

        self.parents: Dict[int, Optional[int]] = {n: None for n in topology.graph.nodes}
        self.ranks: Dict[int, float] = {n: float("inf") for n in topology.graph.nodes}
        self.path_etx: Dict[int, float] = {n: float("inf") for n in topology.graph.nodes}
        self.current_costs: Dict[int, float] = {n: float("inf") for n in topology.graph.nodes}

        self.last_switch_step: Dict[int, int] = {n: -999 for n in topology.graph.nodes}
        self.parent_switch_counts: Dict[int, int] = {n: 0 for n in topology.graph.nodes}
        self.total_switches = 0
        self.control_overhead_count = 0

        self.predictors: Dict[int, CongestionPredictor] = {
            n: CongestionPredictor(node_id=n, queue_capacity=topology.queue_capacity)
            for n in topology.graph.nodes
        }

        self._initialize_dag()

    def _initialize_dag(self):
        root = self.topology.gateway_id
        self.ranks[root] = 1.0
        self.path_etx[root] = 0.0
        self.current_costs[root] = 0.0
        self.parents[root] = None

        nodes_by_depth = sorted(
            [n for n in self.topology.graph.nodes if n != root],
            key=lambda x: self.topology.get_hop_depth(x),
        )

        for u in nodes_by_depth:
            self._evaluate_parent(u, step=0, initial=True)

    def calculate_candidate_cost(self, node_id: int, candidate_id: int) -> Tuple[float, Dict[str, float]]:
        link_info = self.topology.get_link_info(node_id, candidate_id)
        link_etx = link_info.get("etx", 1.5)
        path_etx = self.path_etx.get(candidate_id, 0.0) + link_etx
        norm_etx = min(1.0, path_etx / 12.0)

        cand_predictor = self.predictors[candidate_id]
        cand_queue = cand_predictor.current_queue
        link_lat = link_info.get("latency_ms", 8.0)
        norm_delay = min(1.0, (cand_queue * 2.0 + link_lat) / 45.0)

        norm_congestion = cand_predictor.congestion_index
        norm_energy = self.energy_mgr.compute_energy_penalty(candidate_id)

        if candidate_id == self.topology.gateway_id:
            norm_congestion = 0.0
            norm_delay = 0.0
            norm_energy = 0.0

        total_cost = (
            self.w1 * norm_etx
            + self.w2 * norm_delay
            + self.w3 * norm_congestion
            + self.w4 * norm_energy
        )

        metrics = {
            "norm_etx": round(norm_etx, 3),
            "norm_delay": round(norm_delay, 3),
            "norm_congestion": round(norm_congestion, 3),
            "norm_energy": round(norm_energy, 3),
            "total_cost": round(total_cost, 4),
        }

        return total_cost, metrics

    def _evaluate_parent(self, node_id: int, step: int, initial: bool = False):
        candidates = self.selector.get_candidate_parents(node_id, self.parents, self.ranks)
        if not candidates:
            return

        current_parent = self.parents[node_id]

        current_cost = float("inf")
        curr_congestion = 0.0
        if current_parent is not None and not self.energy_mgr.is_dead(current_parent):
            current_cost, _ = self.calculate_candidate_cost(node_id, current_parent)
            curr_congestion = self.predictors[current_parent].congestion_index
            self.current_costs[node_id] = current_cost

        best_candidate = None
        best_cand_cost = float("inf")

        for cand in candidates:
            cand_cost, _ = self.calculate_candidate_cost(node_id, cand)
            if cand_cost < best_cand_cost:
                best_cand_cost = cand_cost
                best_candidate = cand

        if best_candidate is None:
            return

        if curr_congestion >= 0.80:
            adaptive_threshold = 0.10
            effective_cooldown = max(2, self.cooldown_steps - 1)
        elif curr_congestion <= 0.35:
            adaptive_threshold = max(0.25, self.base_switching_threshold * 1.5)
            effective_cooldown = self.cooldown_steps + 1
        else:
            adaptive_threshold = self.base_switching_threshold
            effective_cooldown = self.cooldown_steps

        time_since_last_switch = step - self.last_switch_step[node_id]
        cooldown_satisfied = time_since_last_switch >= effective_cooldown

        switching_penalty = 0.04
        penalized_cand_cost = best_cand_cost + switching_penalty

        meaningful_improvement = penalized_cand_cost < (current_cost * (1.0 - adaptive_threshold))

        is_orphaned = current_parent is None
        is_curr_dead = current_parent is not None and self.energy_mgr.is_dead(current_parent)
        is_curr_overflowing = current_parent is not None and (
            self.predictors[current_parent].current_queue >= self.topology.queue_capacity
        )

        should_switch = (
            initial
            or is_orphaned
            or is_curr_dead
            or (cooldown_satisfied and is_curr_overflowing and best_cand_cost < current_cost)
            or (cooldown_satisfied and meaningful_improvement)
        )

        if should_switch and (best_candidate != current_parent):
            self.parents[node_id] = best_candidate
            self.current_costs[node_id] = best_cand_cost
            link_info = self.topology.get_link_info(node_id, best_candidate)
            self.path_etx[node_id] = self.path_etx[best_candidate] + link_info.get("etx", 1.5)
            self.ranks[node_id] = self.ranks[best_candidate] + link_info.get("etx", 1.0)
            self.last_switch_step[node_id] = step

            if not initial:
                self.parent_switch_counts[node_id] += 1
                self.total_switches += 1
                self.control_overhead_count += 2
                self.energy_mgr.consume_control(node_id, 2)
        elif current_parent is not None:
            link_info = self.topology.get_link_info(node_id, current_parent)
            self.path_etx[node_id] = self.path_etx[current_parent] + link_info.get("etx", 1.5)
            self.ranks[node_id] = self.ranks[current_parent] + link_info.get("etx", 1.0)

    def update_routing(self, step: int, node_queues: Dict[int, int]):
        for node_id, queue_len in node_queues.items():
            self.predictors[node_id].update(queue_len)

        nodes_by_depth = sorted(
            [n for n in self.topology.graph.nodes if n != self.topology.gateway_id],
            key=lambda x: self.topology.get_hop_depth(x),
        )

        for node_id in nodes_by_depth:
            current_parent = self.parents[node_id]
            is_periodic_check = (step % 10 == 0)
            is_curr_invalid = current_parent is None or self.energy_mgr.is_dead(current_parent)

            curr_congested = False
            if current_parent is not None:
                p_predictor = self.predictors[current_parent]
                curr_congested = (
                    p_predictor.is_congested
                    or p_predictor.congestion_index >= 0.40
                    or p_predictor.ema_growth_rate > 0.5
                )

            if is_curr_invalid or curr_congested or is_periodic_check:
                self._evaluate_parent(node_id, step=step, initial=False)

    def get_next_hop(self, current_node: int) -> Optional[int]:
        if current_node == self.topology.gateway_id:
            return None
        return self.parents.get(current_node)

    def get_parent_map(self) -> Dict[int, Optional[int]]:
        return dict(self.parents)

    def get_metrics_summary(self) -> Dict[str, Any]:
        return {
            "algorithm": "BAS-RPL",
            "total_parent_switches": self.total_switches,
            "control_overhead_packets": self.control_overhead_count,
            "connected_to_root_count": sum(1 for n, p in self.parents.items() if p is not None or n == 0),
        }
