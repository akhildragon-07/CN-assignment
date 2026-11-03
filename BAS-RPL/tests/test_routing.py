import pytest
from simulator.topology import NetworkTopology
from routing.energy_manager import EnergyManager
from routing.congestion_predictor import CongestionPredictor
from routing.baseline_rpl import BaselineRPL
from routing.bas_rpl import BASRPL


def test_baseline_rpl_initialization():
    topo = NetworkTopology(num_nodes=30, seed=42)
    energy_mgr = EnergyManager({n: 100.0 for n in topo.graph.nodes})
    baseline = BaselineRPL(topo, energy_mgr)

    assert baseline.parents[0] is None
    assert baseline.ranks[0] == 1.0

    for node_id in range(1, 30):
        parent = baseline.parents[node_id]
        assert parent is not None
        assert topo.get_hop_depth(parent) <= topo.get_hop_depth(node_id)


def test_congestion_predictor():
    predictor = CongestionPredictor(node_id=5, queue_capacity=20, alpha=0.5, lookahead_steps=2)

    idx0 = predictor.update(0)
    assert idx0 == 0.0
    assert not predictor.is_congested

    idx1 = predictor.update(10)
    assert predictor.raw_growth_rate == 10.0
    assert predictor.ema_growth_rate > 0.0
    assert predictor.predicted_queue > 10.0
    assert predictor.congestion_index > 0.50

    idx2 = predictor.update(18)
    assert predictor.is_congested is True
    assert predictor.congestion_index >= 0.70


def test_energy_manager_penalties():
    mgr = EnergyManager({0: float("inf"), 1: 100.0, 2: 100.0, 3: 100.0})

    assert mgr.compute_energy_penalty(0) == 0.0
    assert mgr.compute_energy_penalty(1) == 0.0

    mgr.remaining_energy[2] = 30.0
    pen2 = mgr.compute_energy_penalty(2)
    assert 0.0 < pen2 < 1.0

    mgr.remaining_energy[3] = 2.0
    assert mgr.compute_energy_penalty(3) == 1.0


def test_bas_rpl_cost_weights():
    topo = NetworkTopology(num_nodes=30, seed=42)
    energy_mgr = EnergyManager({n: 100.0 for n in topo.graph.nodes})
    bas = BASRPL(
        topo,
        energy_mgr,
        w1_etx=0.4,
        w2_delay=0.2,
        w3_congestion=0.2,
        w4_energy=0.2,
    )

    cost, metrics = bas.calculate_candidate_cost(node_id=1, candidate_id=0)
    assert 0.0 <= cost <= 1.0
    assert "norm_etx" in metrics
    assert "norm_congestion" in metrics
    assert "norm_energy" in metrics
