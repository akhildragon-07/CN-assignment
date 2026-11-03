import pytest
from simulator.topology import NetworkTopology
from simulator.packet import Packet
from simulator.network import Network, NetworkNode
from routing.energy_manager import EnergyManager
from routing.baseline_rpl import BaselineRPL


def test_packet_creation_and_fields():
    pkt = Packet(packet_id=1, source=5, destination=0, creation_time=2)
    assert pkt.packet_id == 1
    assert pkt.source == 5
    assert pkt.destination == 0
    assert pkt.current_node == 5
    assert pkt.hop_count == 0
    assert pkt.path == [5]
    assert pkt.status == Packet.STATUS_IN_FLIGHT
    assert len(pkt.history) == 1


def test_queue_overflow_drop():
    node = NetworkNode(node_id=10, queue_capacity=3)
    p1 = Packet(1, 10, 0, 0)
    p2 = Packet(2, 10, 0, 0)
    p3 = Packet(3, 10, 0, 0)
    p4 = Packet(4, 10, 0, 0)

    assert node.enqueue(p1, step=0) is True
    assert node.enqueue(p2, step=0) is True
    assert node.enqueue(p3, step=0) is True
    assert node.enqueue(p4, step=0) is False
    assert p4.status == Packet.STATUS_DROPPED_QUEUE
    assert node.drops_queue == 1


def test_packet_delivery_at_gateway():
    pkt = Packet(1, 5, 0, 0)
    pkt.record_hop(next_node=2, step=1)
    assert pkt.current_node == 2
    assert pkt.hop_count == 1
    assert pkt.status == Packet.STATUS_IN_FLIGHT

    pkt.record_hop(next_node=0, step=3)
    assert pkt.current_node == 0
    assert pkt.hop_count == 2
    assert pkt.status == Packet.STATUS_DELIVERED
    assert pkt.e2e_delay == 3.0
    assert pkt.delivery_time == 3


def test_network_hop_forwarding():
    topo = NetworkTopology(num_nodes=10, seed=42)
    energy_mgr = EnergyManager({n: 100.0 for n in topo.graph.nodes})
    net = Network(topo, energy_mgr, service_rate=2, seed=42)
    routing = BaselineRPL(topo, energy_mgr)

    pkt = Packet(101, source=1, destination=0, creation_time=0)
    net.inject_packets([pkt], step=0)

    tx_log = net.process_hop_forwarding(routing, step=1)
    assert len(tx_log) > 0
    assert pkt.packet_id in net.all_packets
