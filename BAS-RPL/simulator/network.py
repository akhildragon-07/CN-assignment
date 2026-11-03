from collections import deque
import random
from typing import Dict, List, Tuple, Any
from simulator.topology import NetworkTopology
from simulator.packet import Packet
from routing.energy_manager import EnergyManager


class NetworkNode:
    def __init__(self, node_id: int, queue_capacity: int = 20, service_rate: int = 2):
        self.node_id = node_id
        self.queue_capacity = queue_capacity
        self.service_rate = service_rate
        self.queue: deque[Packet] = deque()

        self.packets_generated = 0
        self.packets_forwarded = 0
        self.packets_received = 0
        self.drops_queue = 0
        self.drops_link = 0

    def enqueue(self, packet: Packet, step: int) -> bool:
        if len(self.queue) >= self.queue_capacity:
            packet.mark_dropped(
                Packet.STATUS_DROPPED_QUEUE,
                f"Queue overflow at Node {self.node_id}",
                step,
            )
            self.drops_queue += 1
            return False

        self.queue.append(packet)
        return True

    def get_queue_length(self) -> int:
        return len(self.queue)


class Network:
    def __init__(
        self,
        topology: NetworkTopology,
        energy_manager: EnergyManager,
        service_rate: int = 2,
        max_link_retries: int = 2,
        seed: int = 42,
    ):
        self.topology = topology
        self.energy_mgr = energy_manager
        self.service_rate = service_rate
        self.max_link_retries = max_link_retries
        self.rng = random.Random(seed)

        self.nodes: Dict[int, NetworkNode] = {}
        for n in topology.graph.nodes:
            cap = topology.graph.nodes[n].get("queue_capacity", topology.queue_capacity)
            self.nodes[n] = NetworkNode(node_id=n, queue_capacity=cap, service_rate=service_rate)

        self.nodes[topology.gateway_id].queue_capacity = 10000

        self.all_packets: Dict[int, Packet] = {}
        self.delivered_packets: List[Packet] = []
        self.dropped_packets: List[Packet] = []

    def inject_packets(self, packets: List[Packet], step: int):
        for pkt in packets:
            self.all_packets[pkt.packet_id] = pkt
            src_node = self.nodes.get(pkt.source)
            if src_node is None:
                continue

            src_node.packets_generated += 1
            enqueued = src_node.enqueue(pkt, step)
            if not enqueued:
                self.dropped_packets.append(pkt)

    def process_hop_forwarding(
        self,
        routing_protocol: Any,
        step: int,
    ) -> List[Tuple[int, int, bool, int]]:
        transmission_log = []

        for node_id, node in self.nodes.items():
            if node_id == self.topology.gateway_id:
                continue

            if self.energy_mgr.is_dead(node_id):
                while node.queue:
                    pkt = node.queue.popleft()
                    pkt.mark_dropped(Packet.STATUS_DROPPED_LINK, f"Node {node_id} energy depleted", step)
                    self.dropped_packets.append(pkt)
                continue

            packets_to_send = min(len(node.queue), node.service_rate)
            for _ in range(packets_to_send):
                if not node.queue:
                    break

                pkt = node.queue.popleft()
                next_hop = routing_protocol.get_next_hop(node_id)

                if next_hop is None:
                    pkt.mark_dropped(Packet.STATUS_DROPPED_LINK, f"No route from Node {node_id}", step)
                    self.dropped_packets.append(pkt)
                    node.drops_link += 1
                    continue

                if self.energy_mgr.is_dead(next_hop):
                    pkt.mark_dropped(Packet.STATUS_DROPPED_LINK, f"Next hop {next_hop} dead", step)
                    self.dropped_packets.append(pkt)
                    node.drops_link += 1
                    continue

                self.energy_mgr.consume_tx(node_id, 1)

                link_info = self.topology.get_link_info(node_id, next_hop)
                prr = link_info.get("prr", 0.90)

                channel_success = self.rng.random() <= prr

                if not channel_success:
                    pkt.retries += 1
                    if pkt.retries <= self.max_link_retries:
                        node.queue.appendleft(pkt)
                        transmission_log.append((node_id, next_hop, False, pkt.packet_id))
                        break
                    else:
                        pkt.mark_dropped(
                            Packet.STATUS_DROPPED_LINK,
                            f"Channel transmission failed ({pkt.retries} retries)",
                            step,
                        )
                        self.dropped_packets.append(pkt)
                        node.drops_link += 1
                        transmission_log.append((node_id, next_hop, False, pkt.packet_id))
                        continue

                self.energy_mgr.consume_rx(next_hop, 1)
                node.packets_forwarded += 1

                if next_hop == self.topology.gateway_id:
                    pkt.record_hop(next_hop, step)
                    self.delivered_packets.append(pkt)
                    self.nodes[self.topology.gateway_id].packets_received += 1
                    transmission_log.append((node_id, next_hop, True, pkt.packet_id))
                    continue

                target_node = self.nodes[next_hop]
                target_node.packets_received += 1

                if next_hop in pkt.path:
                    pkt.mark_dropped(
                        Packet.STATUS_DROPPED_LOOP,
                        f"Routing loop detected at Node {next_hop}",
                        step,
                    )
                    self.dropped_packets.append(pkt)
                    transmission_log.append((node_id, next_hop, False, pkt.packet_id))
                    continue

                pkt.record_hop(next_hop, step)
                enqueued = target_node.enqueue(pkt, step)
                if enqueued:
                    transmission_log.append((node_id, next_hop, True, pkt.packet_id))
                else:
                    self.dropped_packets.append(pkt)
                    transmission_log.append((node_id, next_hop, False, pkt.packet_id))

        for node_id in self.nodes:
            if node_id != self.topology.gateway_id:
                self.energy_mgr.consume_idle(node_id)

        return transmission_log

    def get_queue_lengths(self) -> Dict[int, int]:
        return {n: node.get_queue_length() for n, node in self.nodes.items()}
