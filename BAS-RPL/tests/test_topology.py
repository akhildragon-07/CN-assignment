import pytest
import networkx as nx
from simulator.topology import NetworkTopology


def test_topology_30_nodes_connectivity():
    topo = NetworkTopology(num_nodes=30, seed=42)
    assert topo.num_nodes == 30
    assert topo.graph.number_of_nodes() == 30
    assert nx.is_connected(topo.graph)
    assert topo.gateway_id == 0
    assert topo.graph.nodes[0]["is_root"] is True


def test_topology_50_nodes_connectivity():
    topo = NetworkTopology(num_nodes=50, seed=99)
    assert topo.num_nodes == 50
    assert nx.is_connected(topo.graph)
    for node_id in topo.graph.nodes:
        assert nx.has_path(topo.graph, node_id, 0)


def test_link_properties():
    topo = NetworkTopology(num_nodes=30, seed=42)
    for u, v, data in topo.graph.edges(data=True):
        assert "etx" in data
        assert "prr" in data
        assert "latency_ms" in data
        assert data["prr"] > 0.0
        assert data["etx"] >= 1.0
        assert data["latency_ms"] > 0.0


def test_hop_depth_calculation():
    topo = NetworkTopology(num_nodes=30, seed=42)
    assert topo.get_hop_depth(0) == 0
    for node_id in range(1, 30):
        assert topo.get_hop_depth(node_id) >= 1
