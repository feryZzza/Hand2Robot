"""Finite local smoke-test subscriber with a process exit status."""

import time

import rclpy
from hand_msgs.msg import HandObservation, SystemStatus
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from .observation_validator import status_qos


class SmokeCheck(Node):
    def __init__(self) -> None:
        super().__init__("hand_smoke_check")
        self.declare_parameter("required_observations", 10)
        self.declare_parameter("timeout_s", 8.0)
        self._required_observations = int(
            self.get_parameter("required_observations").value
        )
        self._timeout_s = float(self.get_parameter("timeout_s").value)
        if self._required_observations <= 0:
            raise ValueError("required_observations must be positive")
        if self._timeout_s <= 0.0:
            raise ValueError("timeout_s must be positive")

        self.success = False
        self.done = False
        self._observation_count = 0
        self._running_status: SystemStatus | None = None
        self._started_at = time.monotonic()
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

    def _on_observation(self, _: HandObservation) -> None:
        self._observation_count += 1

    def _on_status(self, status: SystemStatus) -> None:
        if status.state == SystemStatus.STATE_RUNNING:
            self._running_status = status

    def _check(self) -> None:
        status = self._running_status
        if (
            self._observation_count >= self._required_observations
            and status is not None
            and status.valid_count >= self._required_observations
            and status.invalid_count == 0
            and status.end_to_end_latency_valid
        ):
            self.success = True
            self.get_logger().info(
                "smoke passed: "
                f"observations={self._observation_count}, "
                f"valid={status.valid_count}, invalid={status.invalid_count}, "
                f"drops={status.dropped_count}, rate={status.input_rate_hz:.1f} Hz, "
                f"latency={status.end_to_end_latency_ms:.2f} ms"
            )
            self.done = True
            return

        if time.monotonic() - self._started_at >= self._timeout_s:
            self.get_logger().error(
                "smoke timed out: "
                f"observations={self._observation_count}, "
                f"running_status={status is not None}"
            )
            self.done = True


def main(args=None) -> int:
    rclpy.init(args=args)
    node = SmokeCheck()
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
