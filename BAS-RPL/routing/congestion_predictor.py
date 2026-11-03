from typing import Dict, List, Any


class CongestionPredictor:
    def __init__(
        self,
        node_id: int,
        queue_capacity: int = 20,
        alpha: float = 0.40,
        lookahead_steps: int = 2,
        congestion_threshold_ratio: float = 0.65,
    ):
        self.node_id = node_id
        self.queue_capacity = queue_capacity
        self.alpha = alpha
        self.lookahead_steps = lookahead_steps
        self.congestion_threshold_ratio = congestion_threshold_ratio

        self.current_queue: int = 0
        self.previous_queue: int = 0
        self.raw_growth_rate: float = 0.0
        self.ema_growth_rate: float = 0.0
        self.predicted_queue: float = 0.0
        self.congestion_index: float = 0.0
        self.is_congested: bool = False

        self.history_queue: List[int] = []
        self.history_index: List[float] = []

    def update(self, current_queue: int, time_interval: float = 1.0) -> float:
        if time_interval <= 0:
            time_interval = 1.0

        self.current_queue = current_queue
        self.raw_growth_rate = (self.current_queue - self.previous_queue) / time_interval

        self.ema_growth_rate = (
            self.alpha * self.raw_growth_rate + (1.0 - self.alpha) * self.ema_growth_rate
        )

        predicted = self.current_queue + (self.lookahead_steps * self.ema_growth_rate)
        self.predicted_queue = max(0.0, predicted)

        utilization_ratio = self.current_queue / self.queue_capacity if self.queue_capacity > 0 else 0.0
        predicted_ratio = self.predicted_queue / self.queue_capacity if self.queue_capacity > 0 else 0.0

        if self.ema_growth_rate > 0:
            self.congestion_index = min(1.0, 0.4 * utilization_ratio + 0.6 * predicted_ratio)
        else:
            self.congestion_index = min(1.0, utilization_ratio)

        self.is_congested = (
            self.congestion_index >= self.congestion_threshold_ratio
            or (self.current_queue >= self.queue_capacity * 0.70)
        )

        self.previous_queue = self.current_queue
        self.history_queue.append(self.current_queue)
        self.history_index.append(self.congestion_index)

        return self.congestion_index

    def reset(self):
        self.current_queue = 0
        self.previous_queue = 0
        self.raw_growth_rate = 0.0
        self.ema_growth_rate = 0.0
        self.predicted_queue = 0.0
        self.congestion_index = 0.0
        self.is_congested = False
        self.history_queue.clear()
        self.history_index.clear()

    def get_state(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "current_queue": self.current_queue,
            "raw_growth_rate": round(self.raw_growth_rate, 2),
            "ema_growth_rate": round(self.ema_growth_rate, 2),
            "predicted_queue": round(self.predicted_queue, 2),
            "congestion_index": round(self.congestion_index, 3),
            "is_congested": self.is_congested,
        }
