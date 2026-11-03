import random
from typing import Dict, List
from simulator.packet import Packet


class TrafficGenerator:
    MODE_PERIODIC = "Periodic"
    MODE_BURST = "Sudden Burst"
    MODE_MIXED = "Mixed"
    MODE_HIGH_CONGESTION = "High Congestion"

    def __init__(
        self,
        num_nodes: int = 30,
        mode: str = "Sudden Burst",
        seed: int = 42,
        destination: int = 0,
        burst_start_step: int = 15,
        burst_duration: int = 10,
        burst_nodes: List[int] = None,
        burst_rate: int = 2,
        base_rate: float = 0.18,
    ):
        self.num_nodes = num_nodes
        self.mode = mode
        self.seed = seed
        self.destination = destination
        self.burst_start_step = burst_start_step
        self.burst_duration = burst_duration
        self.burst_rate = burst_rate
        self.base_rate = base_rate

        if burst_nodes is None:
            self.burst_nodes = list(range(max(1, self.num_nodes // 3), min(self.num_nodes, (2 * self.num_nodes) // 3 + 2)))
        else:
            self.burst_nodes = burst_nodes

    def generate_schedule(self, total_steps: int = 50) -> Dict[int, List[Packet]]:
        rng = random.Random(self.seed)
        schedule: Dict[int, List[Packet]] = {step: [] for step in range(total_steps)}
        packet_counter = 1

        for step in range(total_steps):
            is_burst_active = (
                self.burst_start_step <= step < (self.burst_start_step + self.burst_duration)
            )

            for node_id in range(1, self.num_nodes):
                packets_to_create = 0

                if self.mode == self.MODE_PERIODIC:
                    if rng.random() < self.base_rate:
                        packets_to_create = 1

                elif self.mode == self.MODE_BURST:
                    if rng.random() < (self.base_rate * 0.7):
                        packets_to_create = 1
                    if is_burst_active and node_id in self.burst_nodes:
                        packets_to_create += self.burst_rate

                elif self.mode == self.MODE_MIXED:
                    if rng.random() < self.base_rate:
                        packets_to_create = 1
                    if (step % 12 >= 8) and (node_id % 3 == 0):
                        packets_to_create += 2

                elif self.mode == self.MODE_HIGH_CONGESTION:
                    packets_to_create = rng.randint(1, 3)

                for _ in range(packets_to_create):
                    pkt = Packet(
                        packet_id=packet_counter,
                        source=node_id,
                        destination=self.destination,
                        creation_time=step,
                    )
                    schedule[step].append(pkt)
                    packet_counter += 1

        return schedule
