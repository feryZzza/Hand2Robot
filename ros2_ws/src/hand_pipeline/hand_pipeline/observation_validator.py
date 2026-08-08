"""ROS2 boundary validator and SystemStatus publisher."""

import time

import rclpy
from hand2robot_core.validation import HandObservationValidator, ValidationCode
from hand_msgs.msg import HandObservation, SystemStatus
from rclpy.node import Node
from rclpy.qos import (
    DurabilityPolicy,
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
    qos_profile_sensor_data,
)

from .conversion import hand_observation_from_ros


SCHEMA_VERSION = "0.1.0"


def status_qos() -> QoSProfile:
    return QoSProfile(
        reliability=ReliabilityPolicy.RELIABLE,
        durability=DurabilityPolicy.VOLATILE,
        history=HistoryPolicy.KEEP_LAST,
        depth=10,
    )


class ObservationValidatorNode(Node):
    def __init__(self) -> None:
        super().__init__("hand_observation_validator")
        self.declare_parameter("confidence_threshold", 0.5)
        self.declare_parameter("minimum_confident_joints", 15)
        self.declare_parameter("stale_after_ms", 500.0)
        self.declare_parameter("status_frequency_hz", 2.0)

        confidence_threshold = float(
            self.get_parameter("confidence_threshold").value
        )
        minimum_confident_joints = int(
            self.get_parameter("minimum_confident_joints").value
        )
        self._stale_after_ms = float(self.get_parameter("stale_after_ms").value)
        status_frequency_hz = float(
            self.get_parameter("status_frequency_hz").value
        )
        if self._stale_after_ms <= 0.0:
            raise ValueError("stale_after_ms must be positive")
        if status_frequency_hz < 1.0:
            raise ValueError("status_frequency_hz must be at least 1 Hz")

        self._validator = HandObservationValidator(
            confidence_threshold=confidence_threshold,
            minimum_confident_joints=minimum_confident_joints,
        )
        self._validated_publisher = self.create_publisher(
            HandObservation,
            "/hand/observation",
            qos_profile_sensor_data,
        )
        self._status_publisher = self.create_publisher(
            SystemStatus,
            "/system/status",
            status_qos(),
        )
        self._subscription = self.create_subscription(
            HandObservation,
            "/hand/observation/raw",
            self._on_observation,
            qos_profile_sensor_data,
        )
        self._status_timer = self.create_timer(
            1.0 / status_frequency_hz,
            self._publish_status,
        )

        now_monotonic_ns = time.monotonic_ns()
        self._last_arrival_monotonic_ns: int | None = None
        self._last_status_monotonic_ns = now_monotonic_ns
        self._previous_status_received_count = 0
        self._last_result_accepted = False
        self._last_latency_ms = 0.0
        self._last_latency_valid = False
        self.get_logger().info("validating /hand/observation/raw")

    def _on_observation(self, message: HandObservation) -> None:
        self._last_arrival_monotonic_ns = time.monotonic_ns()
        data = hand_observation_from_ros(message)
        result = self._validator.validate(data)

        now_ns = self.get_clock().now().nanoseconds
        latency_ns = now_ns - data.timestamp_ns
        self._last_latency_valid = latency_ns >= 0
        self._last_latency_ms = latency_ns / 1_000_000.0 if latency_ns >= 0 else 0.0
        self._last_result_accepted = result.accepted

        if result.accepted:
            self._validated_publisher.publish(message)
        else:
            self.get_logger().warning(
                f"rejected sequence {message.sequence}: {result.code.value}: {result.message}"
            )

    def _publish_status(self) -> None:
        now_monotonic_ns = time.monotonic_ns()
        elapsed_s = max(
            (now_monotonic_ns - self._last_status_monotonic_ns) / 1_000_000_000.0,
            1e-9,
        )
        received_delta = (
            self._validator.received_count - self._previous_status_received_count
        )

        status = SystemStatus()
        status.header.stamp = self.get_clock().now().to_msg()
        status.header.frame_id = ""
        status.schema_version = SCHEMA_VERSION
        status.active_source = self._validator.active_source
        status.input_rate_hz = float(received_delta / elapsed_s)
        status.end_to_end_latency_ms = float(self._last_latency_ms)
        status.end_to_end_latency_valid = self._last_latency_valid
        status.drop_rate = float(self._validator.drop_rate)
        status.received_count = self._validator.received_count
        status.valid_count = self._validator.valid_count
        status.invalid_count = self._validator.invalid_count
        status.dropped_count = self._validator.dropped_count
        status.last_error_code = self._validator.last_error_code
        status.last_error_message = self._validator.last_error_message

        if self._last_arrival_monotonic_ns is None:
            status.input_age_ms = 0.0
            status.state = SystemStatus.STATE_INIT
        else:
            status.input_age_ms = float(
                (now_monotonic_ns - self._last_arrival_monotonic_ns) / 1_000_000.0
            )
            if status.input_age_ms > self._stale_after_ms:
                status.state = SystemStatus.STATE_DEGRADED
                status.last_error_code = "stale_input"
                status.last_error_message = (
                    f"input age {status.input_age_ms:.1f} ms exceeds "
                    f"{self._stale_after_ms:.1f} ms"
                )
            elif self._last_result_accepted:
                status.state = SystemStatus.STATE_RUNNING
            else:
                status.state = SystemStatus.STATE_DEGRADED

        if (
            self._validator.last_error_code == ValidationCode.UNSUPPORTED_SCHEMA.value
        ):
            status.state = SystemStatus.STATE_ERROR

        self._status_publisher.publish(status)
        self._previous_status_received_count = self._validator.received_count
        self._last_status_monotonic_ns = now_monotonic_ns


def main(args=None) -> None:
    rclpy.init(args=args)
    node = ObservationValidatorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
