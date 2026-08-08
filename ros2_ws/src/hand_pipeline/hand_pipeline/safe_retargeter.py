"""ROS2 wrapper for the fail-closed CPU prototype retargeter."""

import time

import rclpy
from hand2robot_core.calibration import load_calibration
from hand2robot_core.retargeting import SafeRetargeter, load_retargeting_config
from hand_msgs.msg import HandObservation, RobotTarget
from rclpy.node import Node
from rclpy.qos import (
    DurabilityPolicy,
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
    qos_profile_sensor_data,
)

from .conversion import hand_observation_from_ros, robot_target_to_ros


def target_qos() -> QoSProfile:
    return QoSProfile(
        reliability=ReliabilityPolicy.RELIABLE,
        durability=DurabilityPolicy.VOLATILE,
        history=HistoryPolicy.KEEP_LAST,
        depth=1,
    )


class SafeRetargeterNode(Node):
    def __init__(self) -> None:
        super().__init__("safe_retargeter")
        self.declare_parameter("calibration_path", "")
        self.declare_parameter("retargeting_config_path", "")
        self.declare_parameter("watchdog_frequency_hz", 20.0)
        self.declare_parameter("enforce_capture_age", True)
        calibration_path = str(self.get_parameter("calibration_path").value)
        retargeting_config_path = str(
            self.get_parameter("retargeting_config_path").value
        )
        watchdog_frequency_hz = float(
            self.get_parameter("watchdog_frequency_hz").value
        )
        self._enforce_capture_age = bool(
            self.get_parameter("enforce_capture_age").value
        )
        if not calibration_path or not retargeting_config_path:
            raise ValueError("calibration_path and retargeting_config_path are required")
        if watchdog_frequency_hz <= 0.0:
            raise ValueError("watchdog_frequency_hz must be positive")
        calibration = load_calibration(
            calibration_path,
            expected_parent_frame="robot_base",
            expected_child_frame="camera_optical_frame",
        )
        config = load_retargeting_config(retargeting_config_path)
        self._retargeter = SafeRetargeter(calibration, config)
        self._publisher = self.create_publisher(RobotTarget, "/robot/target", target_qos())
        self._subscription = self.create_subscription(
            HandObservation,
            "/hand/observation",
            self._on_observation,
            qos_profile_sensor_data,
        )
        self._watchdog_timer = self.create_timer(
            1.0 / watchdog_frequency_hz, self._watchdog
        )
        self.get_logger().info(
            f"safe CPU retargeter ready in {config.output_frame}; "
            f"target hand={config.target_handedness}"
        )

    def _on_observation(self, message: HandObservation) -> None:
        target = self._retargeter.retarget(
            hand_observation_from_ros(message),
            target_timestamp_ns=self.get_clock().now().nanoseconds,
            monotonic_timestamp_ns=time.monotonic_ns(),
            enforce_input_age=self._enforce_capture_age,
        )
        self._publisher.publish(robot_target_to_ros(target))
        if not target.valid:
            self.get_logger().warning(
                f"invalid target sequence {target.sequence}: {target.status_message}"
            )

    def _watchdog(self) -> None:
        target = self._retargeter.watchdog_target(
            target_timestamp_ns=self.get_clock().now().nanoseconds,
            monotonic_timestamp_ns=time.monotonic_ns(),
        )
        if target is not None:
            self._publisher.publish(robot_target_to_ros(target))
            self.get_logger().warning(target.status_message)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = SafeRetargeterNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
