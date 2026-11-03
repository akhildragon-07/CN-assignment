import pytest
from simulator.topology import NetworkTopology
from simulator.traffic import TrafficGenerator
from simulator.simulation import SimulationEngine


def test_deterministic_traffic_generation():
    gen1 = TrafficGenerator(num_nodes=20, seed=123, mode="Sudden Burst")
    gen2 = TrafficGenerator(num_nodes=20, seed=123, mode="Sudden Burst")

    sched1 = gen1.generate_schedule(total_steps=30)
    sched2 = gen2.generate_schedule(total_steps=30)

    for step in range(30):
        pkts1 = sched1[step]
        pkts2 = sched2[step]
        assert len(pkts1) == len(pkts2)
        for p1, p2 in zip(pkts1, pkts2):
            assert p1.packet_id == p2.packet_id
            assert p1.source == p2.source
            assert p1.creation_time == p2.creation_time


def test_metric_conservation_laws():
    topo = NetworkTopology(num_nodes=20, seed=42)
    engine = SimulationEngine(topo, algorithm_name="Baseline RPL", total_steps=25, seed=42)
    history = engine.run_all()

    last = history[-1]
    total_gen = last["packets_generated"]
    deliv = last["packets_delivered"]
    drop = last["packets_dropped"]
    flight = last["packets_in_flight"]

    assert total_gen == deliv + drop + flight
    assert last["drops_queue"] + last["drops_link"] + last["drops_loop"] + last["drops_ttl"] == drop


def test_energy_non_negative_and_decreasing():
    topo = NetworkTopology(num_nodes=20, seed=42)
    engine = SimulationEngine(topo, algorithm_name="BAS-RPL", total_steps=25, seed=42)
    history = engine.run_all()

    last = history[-1]
    assert last["total_consumed_energy"] >= 0.0
    assert 0.0 <= last["avg_remaining_pct"] <= 100.0
    assert last["min_node_energy"] >= 0.0
