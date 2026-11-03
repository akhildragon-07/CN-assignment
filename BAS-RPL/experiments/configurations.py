DEFAULT_CONFIG = {
    "num_nodes": 30,
    "area_size": (120.0, 120.0),
    "comm_range": 32.0,
    "seed": 42,
    "queue_capacity": 20,
    "initial_energy": 100.0,
    "total_steps": 50,
    "traffic_mode": "Sudden Burst",
    "burst_start_step": 15,
    "burst_duration": 10,
    "burst_rate": 2,
    "base_rate": 0.18,
    "w1_etx": 0.35,
    "w2_delay": 0.15,
    "w3_congestion": 0.35,
    "w4_energy": 0.15,
    "base_switching_threshold": 0.18,
    "cooldown_steps": 4,
}

CONFIG_50_NODES = {
    **DEFAULT_CONFIG,
    "num_nodes": 50,
    "area_size": (150.0, 150.0),
    "comm_range": 30.0,
    "seed": 99,
    "queue_capacity": 25,
}

CONFIG_PERIODIC = {
    **DEFAULT_CONFIG,
    "traffic_mode": "Periodic",
    "base_rate": 0.40,
}

CONFIG_HIGH_CONGESTION = {
    **DEFAULT_CONFIG,
    "traffic_mode": "High Congestion",
    "queue_capacity": 15,
}
