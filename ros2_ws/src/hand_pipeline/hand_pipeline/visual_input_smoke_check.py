"""Finite subscriber that verifies the switchable visual-input ROS2 boundary."""

import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image


class VisualInputSmokeCheck(Node):
    def __init__(self) -> None:
        super().__init__("visual_input_smoke_check")
        self.declare_parameter("input_topic", "/visual/input/image_raw")
        self.declare_parameter("expected_frames", 5)
        self.declare_parameter("expected_width", 160)
        self.declare_parameter("expected_height", 120)
        self.declare_parameter("expected_frame_id", "camera_optical_frame")
        self.declare_parameter("timeout_s", 8.0)
        input_topic = str(self.get_parameter("input_topic").value)
        self._expected_frames = int(self.get_parameter("expected_frames").value)
        self._expected_width = int(self.get_parameter("expected_width").value)
        self._expected_height = int(self.get_parameter("expected_height").value)
        self._expected_frame_id = str(
            self.get_parameter("expected_frame_id").value
        )
        self._timeout_s = float(self.get_parameter("timeout_s").value)
        if self._expected_frames <= 0:
            raise ValueError("expected_frames must be positive")
        if self._expected_width <= 0 or self._expected_height <= 0:
            raise ValueError("expected image dimensions must be positive")
        if self._timeout_s <= 0.0:
            raise ValueError("timeout_s must be positive")

        self._timestamps_ns: list[int] = []
        self._errors: list[str] = []
        self._started_at = time.monotonic()
        self.success = False
        self.done = False
        self._subscription = self.create_subscription(
            Image,
            input_topic,
            self._on_image,
            qos_profile_sensor_data,
        )
        self._timer = self.create_timer(0.05, self._check)

    def _on_image(self, message: Image) -> None:
        timestamp_ns = (
            int(message.header.stamp.sec) * 1_000_000_000
            + int(message.header.stamp.nanosec)
        )
        if self._timestamps_ns and timestamp_ns <= self._timestamps_ns[-1]:
            self._errors.append("image timestamps are not strictly increasing")
        self._timestamps_ns.append(timestamp_ns)
        if message.header.frame_id != self._expected_frame_id:
            self._errors.append(f"unexpected frame_id {message.header.frame_id!r}")
        if message.width != self._expected_width or message.height != self._expected_height:
            self._errors.append(
                f"unexpected dimensions {message.width}x{message.height}"
            )
        if message.encoding != "bgr8":
            self._errors.append(f"unexpected encoding {message.encoding!r}")
        if message.step != message.width * 3:
            self._errors.append(f"unexpected row step {message.step}")
        if len(message.data) != message.step * message.height:
            self._errors.append(f"unexpected payload length {len(message.data)}")

    def _check(self) -> None:
        if self._errors:
            self.get_logger().error("; ".join(self._errors))
            self.done = True
            return
        if len(self._timestamps_ns) >= self._expected_frames:
            self.success = True
            self.done = True
            self.get_logger().info(
                "visual input smoke passed: "
                f"frames={len(self._timestamps_ns)}, "
                f"dimensions={self._expected_width}x{self._expected_height}, "
                "encoding=bgr8, timestamps=strict"
            )
            return
        if time.monotonic() - self._started_at >= self._timeout_s:
            self.get_logger().error(
                f"visual input smoke timed out after {len(self._timestamps_ns)} frames"
            )
            self.done = True


def main(args=None) -> int:
    rclpy.init(args=args)
    node = VisualInputSmokeCheck()
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
