import math
import random
from typing import Dict, Any, Tuple
import networkx as nx
import numpy as np


class NetworkTopology:
    def __init__(
        self,
        num_nodes: int = 30,
        area_size: Tuple[float, float] = (120.0, 120.0),
        comm_range: float = 32.0,
        seed: int = 42,
        queue_capacity: int = 20,
        initial_energy: float = 100.0,
    ):
        self.num_nodes = num_nodes
        self.area_size = area_size
        self.comm_range = comm_range
        self.seed = seed
        self.queue_capacity = queue_capacity
        self.initial_energy = initial_energy

        self.graph: nx.Graph = nx.Graph()
        self.positions: Dict[int, Tuple[float, float]] = {}
        self.gateway_id = 0

        self.generate()

    def generate(self):
        rng = np.random.default_rng(self.seed)
        width, height = self.area_size

        max_attempts = 50
        for attempt in range(max_attempts):
            G = nx.Graph()
            positions: Dict[int, Tuple[float, float]] = {}

            positions[self.gateway_id] = (width / 2.0, height * 0.90)
            G.add_node(
                self.gateway_id,
                pos=positions[self.gateway_id],
                is_root=True,
                initial_energy=float("inf"),
                energy=float("inf"),
                queue_capacity=1000,
                type="gateway",
                label="Gateway (0)",
            )

            for node_id in range(1, self.num_nodes):
                x = float(rng.uniform(10.0, width - 10.0))
                y = float(rng.uniform(10.0, height * 0.82))
                positions[node_id] = (x, y)

                init_e = float(rng.uniform(0.95 * self.initial_energy, 1.05 * self.initial_energy))
                G.add_node(
                    node_id,
                    pos=(x, y),
                    is_root=False,
                    initial_energy=init_e,
                    energy=init_e,
                    queue_capacity=self.queue_capacity,
                    type="sensor",
                    label=f"Sensor {node_id}",
                )

            for i in range(self.num_nodes):
                for j in range(i + 1, self.num_nodes):
                    pos_i = positions[i]
                    pos_j = positions[j]
                    dist = math.hypot(pos_i[0] - pos_j[0], pos_i[1] - pos_j[1])

                    if dist <= self.comm_range:
                        dist_norm = dist / self.comm_range
                        base_prr = max(0.70, 0.98 - 0.28 * (dist_norm ** 2))
                        jitter = rng.uniform(-0.03, 0.03)
                        prr = float(np.clip(base_prr + jitter, 0.65, 0.99))
                        etx = float(round(1.0 / prr, 3))
                        latency_ms = float(round(4.0 + 8.0 * dist_norm, 2))

                        G.add_edge(
                            i,
                            j,
                            distance=round(dist, 2),
                            prr=round(prr, 3),
                            etx=etx,
                            latency_ms=latency_ms,
                            is_active=True,
                        )

            if nx.has_path(G, self.gateway_id, 1) and nx.is_connected(G):
                self.graph = G
                self.positions = positions
                self._compute_topological_properties()
                return

            rng = np.random.default_rng(self.seed + attempt + 1)

        self._ensure_connectivity(G, positions)
        self.graph = G
        self.positions = positions
        self._compute_topological_properties()

    def _ensure_connectivity(self, G: nx.Graph, positions: Dict[int, Tuple[float, float]]):
        while not nx.is_connected(G):
            components = list(nx.connected_components(G))
            best_pair = None
            min_dist = float("inf")
            c0 = components[0]
            for c_other in components[1:]:
                for u in c0:
                    for v in c_other:
                        dist = math.hypot(
                            positions[u][0] - positions[v][0],
                            positions[u][1] - positions[v][1]
                        )
                        if dist < min_dist:
                            min_dist = dist
                            best_pair = (u, v)

            if best_pair:
                u, v = best_pair
                prr = 0.72
                G.add_edge(
                    u,
                    v,
                    distance=round(min_dist, 2),
                    prr=prr,
                    etx=round(1.0 / prr, 3),
                    latency_ms=12.0,
                    is_active=True,
                )

    def _compute_topological_properties(self):
        hop_depths = nx.single_source_shortest_path_length(self.graph, self.gateway_id)
        for node_id, depth in hop_depths.items():
            self.graph.nodes[node_id]["hop_depth"] = depth
            if node_id != self.gateway_id:
                if depth <= 2 and self.graph.degree[node_id] > 2:
                    self.graph.nodes[node_id]["role"] = "critical_relay"
                elif self.graph.degree[node_id] > 2:
                    self.graph.nodes[node_id]["role"] = "relay"
                else:
                    self.graph.nodes[node_id]["role"] = "leaf"
            else:
                self.graph.nodes[node_id]["role"] = "gateway"

    def get_neighbors(self, node_id: int):
        return list(self.graph.neighbors(node_id))

    def get_link_info(self, u: int, v: int) -> Dict[str, Any]:
        if self.graph.has_edge(u, v):
            return dict(self.graph.edges[u, v])
        return {}

    def get_hop_depth(self, node_id: int) -> int:
        return self.graph.nodes[node_id].get("hop_depth", 0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "num_nodes": self.num_nodes,
            "num_edges": self.graph.number_of_edges(),
            "avg_degree": round(2.0 * self.graph.number_of_edges() / self.num_nodes, 2),
            "max_hop_depth": max(self.graph.nodes[n]["hop_depth"] for n in self.graph.nodes),
            "seed": self.seed,
            "is_connected": nx.is_connected(self.graph),
        }
