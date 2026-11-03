import pytest
from simulator.topology import NetworkTopology
from routing.energy_manager import EnergyManager
from routing.baseline_rpl import BaselineRPL
from routing.bas_rpl import BASRPL
from routing.parent_selection import ParentSelector


def check_parent_map_acyclic(parent_map, gateway_id=0):
    for node, parent in parent_map.items():
        if node == gateway_id:
            assert parent is None
            continue
        curr = node
        visited = set()
        hops = 0
        while curr is not None and curr != gateway_id:
            assert curr not in visited, f"Cycle detected in parent map at node {curr}"
            visited.add(curr)
            curr = parent_map.get(curr)
            hops += 1
            assert hops <= len(parent_map), "Loop detected (exceeded node count)"
        assert curr == gateway_id, f"Node {node} does not connect to gateway"


def test_baseline_loop_freeness():
    topo = NetworkTopology(num_nodes=30, seed=42)
    energy_mgr = EnergyManager({n: 100.0 for n in topo.graph.nodes})
    baseline = BaselineRPL(topo, energy_mgr)
    check_parent_map_acyclic(baseline.parents, gateway_id=0)


def test_bas_rpl_loop_freeness():
    topo = NetworkTopology(num_nodes=30, seed=42)
    energy_mgr = EnergyManager({n: 100.0 for n in topo.graph.nodes})
    bas_rpl = BASRPL(topo, energy_mgr)
    check_parent_map_acyclic(bas_rpl.parents, gateway_id=0)


def test_parent_selector_cycle_rejection():
    topo = NetworkTopology(num_nodes=10, seed=42)
    energy_mgr = EnergyManager({n: 100.0 for n in topo.graph.nodes})
    selector = ParentSelector(topo, energy_mgr)

    artificial_map = {0: None, 1: 2, 2: 3, 3: None}
    assert selector._creates_cycle(node_id=3, prospective_parent=1, parent_map=artificial_map) is True
    assert selector._creates_cycle(node_id=3, prospective_parent=0, parent_map=artificial_map) is False
