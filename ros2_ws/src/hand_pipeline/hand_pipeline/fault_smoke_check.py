"""Self-contained ROS2 diagnostic smoke using low-confidence observations."""

import time

import rclpy
from hand_msgs.msg import HandObservation, SystemStatus
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from .observation_validator import ObservationValidatorNode, status_qos
from .synthetic_publisher import build_synthetic_observation


class LowConfidenceProbe(Node):
    def __init__(self) -> None:
        super().__init__("low_confidence_probe")
        self.declare_parameter("required_invalid", 5)
        self.declare_parameter("timeout_s", 8.0)
        self._required_invalid = int(self.get_parameter("required_invalid").value)
        self._timeout_s = float(self.get_parameter("timeout_s").value)
        self._started_at = time.monotonic()
        self._sequence = 0
        self.done = False
        self.success = False
        self._publisher = self.create_publisher(
            HandObservation,
            "/hand/observation/raw",
            qos_profile_sensor_data,
        )
        self._status_subscription = self.create_subscription(
            SystemStatus,
            "/system/status",
            self._on_status,
            status_qos(),
        )
        self._publish_timer = self.create_timer(0.05, self._publish_fault)
        self._timeout_timer = self.create_timer(0.1, self._check_timeout)

    def _publish_fault(self) -> None:
        message = build_synthetic_observation(
            stamp=self.get_clock().now().to_msg(),
            sequence=self._sequence,
            frame_id="camera_optical_frame",
            source="fault_low_confidence",
            handedness=HandObservation.HANDEDNESS_RIGHT,
            confidence=0.1,
            motion_amplitude_m=0.0,
        )
        self._publisher.publish(message)
        self._sequence += 1

    def _on_status(self, status: SystemStatus) -> None:
        if (
            status.invalid_count >= self._required_invalid
            and status.valid_count == 0
            and status.state == SystemStatus.STATE_DEGRADED
            and status.last_error_code == "low_confidence"
        ):
            self.success = True
            self.done = True
            self.get_logger().info(
                "fault smoke passed: "
                f"valid={status.valid_count}, invalid={status.invalid_count}, "
                f"error={status.last_error_code}"
            )

    def _check_timeout(self) -> None:
        if time.monotonic() - self._started_at >= self._timeout_s:
            self.done = True
            self.get_logger().error("fault smoke timed out before expected diagnostic")


def main(args=None) -> int:
    rclpy.init(args=args)
    validator = ObservationValidatorNode()
    probe = LowConfidenceProbe()
    executor = SingleThreadedExecutor()
    executor.add_node(validator)
    executor.add_node(probe)
    try:
        while rclpy.ok() and not probe.done:
            executor.spin_once(timeout_sec=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        success = probe.success
        executor.remove_node(probe)
        executor.remove_node(validator)
        probe.destroy_node()
        validator.destroy_node()
        executor.shutdown()
        if rclpy.ok():
            rclpy.shutdown()
    return 0 if success else 1
