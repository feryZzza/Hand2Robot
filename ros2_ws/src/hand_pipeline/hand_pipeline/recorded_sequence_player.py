"""Publish a versioned recorded hand sequence without rewriting capture timestamps."""

import time

import rclpy
from geometry_msgs.msg import Point
from hand2robot_core.recorded_sequence import RecordedSequence, load_recorded_sequence
from hand_msgs.msg import HandObservation
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data


class RecordedSequencePlayer(Node):
    def __init__(self) -> None:
        super().__init__("recorded_sequence_player")
        self.declare_parameter("sequence_path", "")
        self.declare_parameter("playback_rate", 1.0)
        self.declare_parameter("startup_delay_s", 0.5)
        self.declare_parameter("discovery_timeout_s", 5.0)

        sequence_path = str(self.get_parameter("sequence_path").value)
        self._playback_rate = float(self.get_parameter("playback_rate").value)
        self._startup_delay_s = float(self.get_parameter("startup_delay_s").value)
        self._discovery_timeout_s = float(
            self.get_parameter("discovery_timeout_s").value
        )
        if not sequence_path:
            raise ValueError("sequence_path must be provided")
        if self._playback_rate <= 0.0:
            raise ValueError("playback_rate must be positive")
        if self._startup_delay_s < 0.0:
            raise ValueError("startup_delay_s must be non-negative")
        if self._discovery_timeout_s <= 0.0:
            raise ValueError("discovery_timeout_s must be positive")

        self._sequence: RecordedSequence = load_recorded_sequence(sequence_path)
        self._publisher = self.create_publisher(
            HandObservation,
            "/hand/observation/raw",
            qos_profile_sensor_data,
        )
        self._next_frame_index = 0
        self._discovery_started_at = time.monotonic()
        self._playback_started_at: float | None = None
        self._discovery_error_reported = False
        self._timer = self.create_timer(0.01, self._tick)
        self.get_logger().info(
            f"loaded {len(self._sequence.frames)} frames from {sequence_path}"
        )

    def _tick(self) -> None:
        now = time.monotonic()
        if self._publisher.get_subscription_count() == 0:
            if (
                not self._discovery_error_reported
                and now - self._discovery_started_at >= self._discovery_timeout_s
            ):
                self.get_logger().error("no raw-observation subscriber discovered")
                self._discovery_error_reported = True
            return

        if self._playback_started_at is None:
            self._playback_started_at = now + self._startup_delay_s
            return
        if now < self._playback_started_at:
            return

        first_timestamp_ns = self._sequence.frames[0].capture_timestamp_ns
        elapsed_s = now - self._playback_started_at
        while self._next_frame_index < len(self._sequence.frames):
            frame = self._sequence.frames[self._next_frame_index]
            scheduled_s = (
                (frame.capture_timestamp_ns - first_timestamp_ns)
                / 1_000_000_000.0
                / self._playback_rate
            )
            if scheduled_s > elapsed_s:
                break
            self._publisher.publish(self._message_for_frame(self._next_frame_index))
            self._next_frame_index += 1

        if self._next_frame_index == len(self._sequence.frames):
            self.get_logger().info(
                f"published all {self._next_frame_index} recorded frames"
            )
            self._timer.cancel()

    def _message_for_frame(self, frame_index: int) -> HandObservation:
        data = self._sequence.observation_at(frame_index)
        message = HandObservation()
        message.header.stamp.sec = data.timestamp_ns // 1_000_000_000
        message.header.stamp.nanosec = data.timestamp_ns % 1_000_000_000
        message.header.frame_id = data.frame_id
        message.schema_version = data.schema_version
        message.sequence = data.sequence
        message.handedness = data.handedness
        message.source = data.source
        for index, point in enumerate(data.joints_2d_px):
            message.joints_2d_px[index] = Point(x=point[0], y=point[1], z=point[2])
        for index, point in enumerate(data.joints_3d_m):
            message.joints_3d_m[index] = Point(x=point[0], y=point[1], z=point[2])
        message.joints_3d_valid = list(data.joints_3d_valid)
        message.confidence = list(data.confidence)
        message.valid = data.valid
        return message


def main(args=None) -> None:
    rclpy.init(args=args)
    node = RecordedSequencePlayer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
