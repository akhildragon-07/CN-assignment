from typing import Dict, List, Optional, Set
from simulator.topology import NetworkTopology
from routing.energy_manager import EnergyManager


class ParentSelector:
    def __init__(self, topology: NetworkTopology, energy_manager: EnergyManager):
        self.topology = topology
        self.energy_mgr = energy_manager

    def get_candidate_parents(
        self,
        node_id: int,
        current_parent_map: Dict[int, Optional[int]],
        ranks: Dict[int, float],
    ) -> List[int]:
        if node_id == self.topology.gateway_id:
            return []

        candidates = []
        node_depth = self.topology.get_hop_depth(node_id)
        node_rank = ranks.get(node_id, float("inf"))

        for neighbor in self.topology.get_neighbors(node_id):
            if neighbor == node_id:
                continue

            if self.energy_mgr.is_dead(neighbor):
                continue

            if neighbor == self.topology.gateway_id:
                candidates.append(neighbor)
                continue

            nbr_depth = self.topology.get_hop_depth(neighbor)
            nbr_rank = ranks.get(neighbor, float("inf"))

            if (nbr_depth < node_depth) or (nbr_depth == node_depth and nbr_rank < node_rank):
                if not self._creates_cycle(node_id, neighbor, current_parent_map):
                    candidates.append(neighbor)

        return candidates

    def _creates_cycle(
        self,
        node_id: int,
        prospective_parent: int,
        parent_map: Dict[int, Optional[int]]
    ) -> bool:
        curr = prospective_parent
        visited: Set[int] = {node_id}
        while curr is not None and curr != self.topology.gateway_id:
            if curr in visited:
                return True
            visited.add(curr)
            curr = parent_map.get(curr)
        return False
