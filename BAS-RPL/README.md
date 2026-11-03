# BAS-RPL: Burst-Aware Stability-Constrained Routing Protocol

Implementation and performance simulation of an adaptive IoT routing protocol for wireless sensor networks (WSN).

---

## Overview

In IEEE 802.15.4 and low-power IoT networks, standard RPL uses the MRHOF objective function based on Expected Transmission Count (ETX). While ETX provides reliable paths under static conditions, it is blind to node buffer queues. When sensor nodes experience sudden traffic bursts, packets converge on common bottleneck relays, leading to queue overflows and drop-tail losses.

**BAS-RPL** addresses this through:
1. **Queue Growth Prediction:** Uses an Exponential Moving Average (EMA) of queue rate-of-change $\Delta Q$ to detect impending congestion before packets drop.
2. **Adaptive Cost Metric:** Combines normalized ETX, delay, predicted congestion, and remaining energy:
   $$\text{Cost} = w_1 \cdot \text{ETX} + w_2 \cdot \text{Delay} + w_3 \cdot \text{Congestion} + w_4 \cdot \text{Energy}$$
3. **Route Stability (Anti-Flapping):** Enforces a cooldown period ($T_{\text{cooldown}}$) and a switching threshold barrier ($\delta$) to prevent route flapping between alternate relays.
4. **Loop-Free DAG:** Guarantees loop-freeness via hop-depth ordering and upstream path cycle validation.

---

## Project Structure

```text
BAS-RPL/
├── app.py                      # Streamlit interactive application
├── requirements.txt            # Python dependencies
├── README.md                   # Project documentation
│
├── simulator/
│   ├── topology.py             # 2D connected wireless sensor mesh generator
│   ├── packet.py               # Packet state, hop tracking, and drop status
│   ├── traffic.py              # Traffic pattern scheduler (Periodic, Burst, Mixed)
│   ├── network.py              # FIFO queues, PRR channels, retries, and drops
│   └── simulation.py           # Discrete-time simulation engine
│
├── routing/
│   ├── baseline_rpl.py         # Standard RPL (MRHOF ETX) implementation
│   ├── bas_rpl.py              # Proposed BAS-RPL protocol implementation
│   ├── congestion_predictor.py # EMA queue growth predictor
│   ├── parent_selection.py     # Candidate validation and cycle avoidance
│   └── energy_manager.py       # Radio energy consumption model
│
├── metrics/
│   ├── performance.py          # Metric calculations (PDR, PLR, Delay, Drops)
│   └── comparison.py           # Side-by-side benchmark comparison
│
├── visualization/
│   ├── topology_view.py        # Plotly 2D network visualizer
│   └── charts.py               # Plotly comparison charts
│
├── experiments/
│   ├── configurations.py       # Simulation parameters and presets
│   └── demo_scenario.py        # Bottleneck benchmark scenario
│
└── tests/
    ├── test_topology.py        # Graph connectivity and link property tests
    ├── test_routing.py         # Objective function and rank tests
    ├── test_packet_forwarding.py # Forwarding, retries, and queue limits
    ├── test_loop_prevention.py # Loop-freeness and DAG validation
    └── test_metrics.py         # Metric consistency tests
```

---

## Setup & Running

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Tests
```bash
python -m pytest BAS-RPL/tests -v
```

### 3. Run Benchmark (CLI)
```bash
python BAS-RPL/experiments/demo_scenario.py
```

### 4. Launch Dashboard
```bash
streamlit run app.py
```
Or:
```bash
streamlit run BAS-RPL/app.py
```

---

## Summary of Results (30 Nodes, Burst Scenario)

| Metric | Baseline RPL | BAS-RPL | Difference |
| :--- | :---: | :---: | :---: |
| **Buffer Overflow Drops** | 161 | 41 | **-120 drops (75% drop reduction)** |
| **Packets Delivered** | 226 | 228 | +2 |
| **Packet Delivery Ratio (PDR)** | 46.6% | 47.0% | +0.4% |
| **Control Overhead** | 350 pkts | 306 pkts | -44 pkts |
| **Average Remaining Battery** | 98.0% | 96.8% | Balanced across relays |
