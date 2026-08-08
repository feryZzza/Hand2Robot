"""Verify that the recorded fixture crosses the ROS2 validation boundary exactly once."""

import time

import rclpy
from hand_msgs.msg import HandObservation, SystemStatus
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from .observation_validator import status_qos


class RecordedSmokeCheck(Node):
    def __init__(self) -> None:
        super().__init__("recorded_smoke_check")
        self.declare_parameter("expected_count", 5)
        self.declare_parameter("expected_source", "recorded_fixture")
        self.declare_parameter("timeout_s", 8.0)
        self._expected_count = int(self.get_parameter("expected_count").value)
        self._expected_source = str(self.get_parameter("expected_source").value)
        self._timeout_s = float(self.get_parameter("timeout_s").value)
        self._sequences: list[int] = []
        self._sources: list[str] = []
        self._latest_status: SystemStatus | None = None
        self._started_at = time.monotonic()
        self.done = False
        self.success = False
        self._observation_subscription = self.create_subscription(
            HandObservation,
            "/hand/observation",
            self._on_observation,
            qos_profile_sensor_data,
        )
        self._status_subscription = self.create_subscription(
            SystemStatus,
            "/system/status",
            self._on_status,
            status_qos(),
        )
        self._timer = self.create_timer(0.05, self._check)

    def _on_observation(self, observation: HandObservation) -> None:
        self._sequences.append(observation.sequence)
        self._sources.append(observation.source)

    def _on_status(self, status: SystemStatus) -> None:
        self._latest_status = status

    def _check(self) -> None:
        status = self._latest_status
        expected_sequences = list(range(self._expected_count))
        if (
            len(self._sequences) == self._expected_count
            and self._sequences == expected_sequences
            and set(self._sources) == {self._expected_source}
            and status is not None
            and status.valid_count == self._expected_count
            and status.invalid_count == 0
            and status.dropped_count == 0
        ):
            self.success = True
            self.done = True
            self.get_logger().info(
                "recorded smoke passed: "
                f"count={len(self._sequences)}, sequences={self._sequences}, "
                f"source={self._expected_source}"
            )
            return
        if len(self._sequences) > self._expected_count:
            self.done = True
            self.get_logger().error(
                f"received too many observations: {self._sequences}"
            )
            return
        if time.monotonic() - self._started_at >= self._timeout_s:
            self.done = True
            self.get_logger().error(
                f"recorded smoke timed out: sequences={self._sequences}, "
                f"status_valid={status.valid_count if status else 'none'}"
            )


def main(args=None) -> int:
    rclpy.init(args=args)
    node = RecordedSmokeCheck()
    try:
        while rclpy.ok() and not node.done:
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        success = node.success
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0 if success else 1
