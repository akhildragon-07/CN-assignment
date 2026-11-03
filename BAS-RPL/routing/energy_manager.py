from typing import Dict, Any


class EnergyManager:
    E_TX = 0.040
    E_RX = 0.020
    E_IDLE = 0.0005
    E_CTRL = 0.010

    def __init__(self, initial_energy_map: Dict[int, float]):
        self.initial_energy: Dict[int, float] = dict(initial_energy_map)
        self.remaining_energy: Dict[int, float] = dict(initial_energy_map)
        self.total_consumed: Dict[int, float] = {node_id: 0.0 for node_id in initial_energy_map}
        self.dead_nodes: set = set()

    def consume_tx(self, node_id: int, num_packets: int = 1):
        if node_id == 0:
            return
        cost = self.E_TX * num_packets
        self._deduct_energy(node_id, cost)

    def consume_rx(self, node_id: int, num_packets: int = 1):
        if node_id == 0:
            return
        cost = self.E_RX * num_packets
        self._deduct_energy(node_id, cost)

    def consume_idle(self, node_id: int):
        if node_id == 0:
            return
        self._deduct_energy(node_id, self.E_IDLE)

    def consume_control(self, node_id: int, count: int = 1):
        if node_id == 0:
            return
        self._deduct_energy(node_id, self.E_CTRL * count)

    def _deduct_energy(self, node_id: int, amount: float):
        if self.is_dead(node_id):
            return
        self.remaining_energy[node_id] = max(0.0, self.remaining_energy[node_id] - amount)
        self.total_consumed[node_id] += amount
        if self.remaining_energy[node_id] <= 0.0:
            self.dead_nodes.add(node_id)

    def is_dead(self, node_id: int) -> bool:
        if node_id == 0:
            return False
        return node_id in self.dead_nodes

    def get_remaining_ratio(self, node_id: int) -> float:
        if node_id == 0:
            return 1.0
        init_e = self.initial_energy.get(node_id, 100.0)
        rem_e = self.remaining_energy.get(node_id, 0.0)
        return float(rem_e / init_e) if init_e > 0 else 0.0

    def compute_energy_penalty(self, node_id: int) -> float:
        if node_id == 0:
            return 0.0
        ratio = self.get_remaining_ratio(node_id)
        if ratio >= 0.60:
            return 0.0
        elif ratio <= 0.05:
            return 1.0
        else:
            normalized_deficiency = (0.60 - ratio) / 0.55
            return float(min(1.0, normalized_deficiency ** 2))

    def get_network_energy_stats(self) -> Dict[str, Any]:
        sensor_nodes = [n for n in self.remaining_energy if n != 0]
        if not sensor_nodes:
            return {"total_consumed": 0.0, "avg_remaining_pct": 100.0, "min_energy": 0.0, "dead_count": 0}

        total_init = sum(self.initial_energy[n] for n in sensor_nodes)
        total_rem = sum(self.remaining_energy[n] for n in sensor_nodes)
        total_used = sum(self.total_consumed[n] for n in sensor_nodes)
        min_rem = min(self.remaining_energy[n] for n in sensor_nodes)

        return {
            "total_initial_energy": round(total_init, 2),
            "total_remaining_energy": round(total_rem, 2),
            "total_consumed_energy": round(total_used, 2),
            "avg_remaining_pct": round((total_rem / total_init) * 100.0, 2) if total_init > 0 else 0.0,
            "min_node_energy": round(min_rem, 2),
            "dead_nodes_count": len(self.dead_nodes),
        }
