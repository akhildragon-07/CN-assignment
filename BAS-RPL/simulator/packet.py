from typing import List, Dict, Optional, Any


class Packet:
    STATUS_IN_FLIGHT = "in_flight"
    STATUS_DELIVERED = "delivered"
    STATUS_DROPPED_QUEUE = "dropped_queue"
    STATUS_DROPPED_LINK = "dropped_link"
    STATUS_DROPPED_LOOP = "dropped_loop"
    STATUS_DROPPED_TTL = "dropped_ttl"

    def __init__(
        self,
        packet_id: int,
        source: int,
        destination: int = 0,
        creation_time: int = 0,
        payload_size: int = 64,
        max_hops: int = 25,
    ):
        self.packet_id = packet_id
        self.source = source
        self.destination = destination
        self.creation_time = creation_time
        self.payload_size = payload_size
        self.max_hops = max_hops

        self.current_node = source
        self.hop_count = 0
        self.path: List[int] = [source]
        self.status = self.STATUS_IN_FLIGHT
        self.drop_reason: Optional[str] = None
        self.delivery_time: Optional[int] = None
        self.e2e_delay: Optional[float] = None
        self.retries: int = 0

        self.history: List[Dict[str, Any]] = [
            {
                "step": creation_time,
                "node": source,
                "action": "created",
                "details": f"Generated at node {source}",
            }
        ]

    def record_hop(self, next_node: int, step: int, delay_contribution: float = 1.0):
        self.current_node = next_node
        self.hop_count += 1
        self.path.append(next_node)
        self.retries = 0

        self.history.append({
            "step": step,
            "node": next_node,
            "action": "forwarded",
            "details": f"Forwarded to node {next_node}",
        })

        if next_node == self.destination:
            self.mark_delivered(step)
        elif self.hop_count > self.max_hops:
            self.mark_dropped(self.STATUS_DROPPED_TTL, f"Hop limit exceeded ({self.max_hops})", step)

    def mark_delivered(self, step: int):
        self.status = self.STATUS_DELIVERED
        self.delivery_time = step
        self.e2e_delay = float(step - self.creation_time)
        self.history.append({
            "step": step,
            "node": self.destination,
            "action": "delivered",
            "details": f"Delivered in {self.e2e_delay:.1f} steps",
        })

    def mark_dropped(self, reason_status: str, detail_message: str, step: int):
        self.status = reason_status
        self.drop_reason = detail_message
        self.history.append({
            "step": step,
            "node": self.current_node,
            "action": "dropped",
            "details": f"{reason_status}: {detail_message}",
        })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "source": self.source,
            "destination": self.destination,
            "creation_time": self.creation_time,
            "delivery_time": self.delivery_time,
            "e2e_delay": self.e2e_delay,
            "hop_count": self.hop_count,
            "path": " -> ".join(map(str, self.path)),
            "status": self.status,
            "drop_reason": self.drop_reason,
        }

    def __repr__(self) -> str:
        return f"Packet({self.packet_id}, {self.source}->{self.destination}, hop={self.hop_count}, {self.status})"
