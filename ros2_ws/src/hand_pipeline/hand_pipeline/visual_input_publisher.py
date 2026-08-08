"""Publish camera or video-file frames through one stable ROS2 image topic."""

import time

import cv2
from cv_bridge import CvBridge
from hand2robot_core.visual_input import VisualInputSettings
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image


class VisualInputPublisher(Node):
    def __init__(self) -> None:
        super().__init__("visual_input_publisher")
        self.declare_parameter("input_mode", "camera")
        self.declare_parameter("camera_device", 0)
        self.declare_parameter("video_path", "")
        self.declare_parameter("loop_video", False)
        self.declare_parameter("playback_rate", 1.0)
        self.declare_parameter("fallback_frequency_hz", 30.0)
        self.declare_parameter("startup_delay_s", 0.5)
        self.declare_parameter("discovery_timeout_s", 5.0)
        self.declare_parameter("minimum_subscription_count", 1)
        self.declare_parameter("frame_id", "camera_optical_frame")
        self.declare_parameter("output_topic", "/visual/input/image_raw")

        self._settings = VisualInputSettings(
            mode=str(self.get_parameter("input_mode").value),
            camera_device=int(self.get_parameter("camera_device").value),
            video_path=str(self.get_parameter("video_path").value),
            loop_video=bool(self.get_parameter("loop_video").value),
            playback_rate=float(self.get_parameter("playback_rate").value),
            fallback_frequency_hz=float(
                self.get_parameter("fallback_frequency_hz").value
            ),
        )
        self._startup_delay_s = float(self.get_parameter("startup_delay_s").value)
        self._discovery_timeout_s = float(
            self.get_parameter("discovery_timeout_s").value
        )
        self._minimum_subscription_count = int(
            self.get_parameter("minimum_subscription_count").value
        )
        self._frame_id = str(self.get_parameter("frame_id").value).strip()
        self._output_topic = str(self.get_parameter("output_topic").value).strip()
        if self._startup_delay_s < 0.0:
            raise ValueError("startup_delay_s must be non-negative")
        if self._discovery_timeout_s <= 0.0:
            raise ValueError("discovery_timeout_s must be positive")
        if self._minimum_subscription_count <= 0:
            raise ValueError("minimum_subscription_count must be positive")
        if not self._frame_id:
            raise ValueError("frame_id must be non-empty")
        if not self._output_topic:
            raise ValueError("output_topic must be non-empty")

        self._capture = cv2.VideoCapture(self._settings.capture_source)
        if not self._capture.isOpened():
            self._capture.release()
            raise RuntimeError(
                f"could not open visual input {self._settings.source_label}"
            )
        native_frequency_hz = float(self._capture.get(cv2.CAP_PROP_FPS))
        self._frequency_hz = self._settings.output_frequency_hz(native_frequency_hz)
        self._bridge = CvBridge()
        self._publisher = self.create_publisher(
            Image,
            self._output_topic,
            qos_profile_sensor_data,
        )
        self._discovery_started_at = time.monotonic()
        self._playback_starts_at: float | None = None
        self._discovery_error_reported = False
        self._published_count = 0
        self.done = False
        self.failed = False
        self._timer = self.create_timer(1.0 / self._frequency_hz, self._tick)
        self.get_logger().info(
            f"visual input ready: mode={self._settings.mode}, "
            f"source={self._settings.source_label}, topic={self._output_topic}, "
            f"rate={self._frequency_hz:.3f} Hz, loop={self._settings.loop_video}"
        )

    def _tick(self) -> None:
        now = time.monotonic()
        if self._publisher.get_subscription_count() < self._minimum_subscription_count:
            if (
                not self._discovery_error_reported
                and now - self._discovery_started_at >= self._discovery_timeout_s
            ):
                self.get_logger().error(
                    "insufficient image subscribers: "
                    f"need {self._minimum_subscription_count}, "
                    f"found {self._publisher.get_subscription_count()}"
                )
                self._discovery_error_reported = True
            return
        if self._playback_starts_at is None:
            self._playback_starts_at = now + self._startup_delay_s
            return
        if now < self._playback_starts_at:
            return

        available, frame = self._capture.read()
        if not available and self._settings.mode == "video" and self._settings.loop_video:
            if self._capture.set(cv2.CAP_PROP_POS_FRAMES, 0.0):
                available, frame = self._capture.read()
        if not available:
            if self._settings.mode == "video" and not self._settings.loop_video:
                self.get_logger().info(
                    f"video input completed after {self._published_count} frames"
                )
            else:
                self.failed = True
                self.get_logger().error(
                    f"failed to read visual input after {self._published_count} frames"
                )
            self.done = True
            self._timer.cancel()
            return

        message = self._bridge.cv2_to_imgmsg(frame, encoding="bgr8")
        message.header.stamp = self.get_clock().now().to_msg()
        message.header.frame_id = self._frame_id
        self._publisher.publish(message)
        self._published_count += 1

    def destroy_node(self) -> bool:
        self._capture.release()
        return super().destroy_node()


def main(args=None) -> int:
    rclpy.init(args=args)
    node = VisualInputPublisher()
    try:
        while rclpy.ok() and not node.done:
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        failed = node.failed
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 1 if failed else 0
