"""Deterministic synthetic HandObservation publisher."""

from math import sin

import rclpy
from geometry_msgs.msg import Point
from hand_msgs.msg import HandObservation
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data


SCHEMA_VERSION = "0.1.0"

BASE_HAND_POINTS_M = (
    (0.000, 0.060, 0.450),
    (-0.025, 0.030, 0.448),
    (-0.045, 0.005, 0.446),
    (-0.060, -0.020, 0.444),
    (-0.072, -0.043, 0.442),
    (-0.025, 0.000, 0.450),
    (-0.027, -0.040, 0.447),
    (-0.028, -0.072, 0.445),
    (-0.029, -0.100, 0.443),
    (0.000, -0.005, 0.450),
    (0.000, -0.050, 0.447),
    (0.000, -0.085, 0.445),
    (0.000, -0.115, 0.443),
    (0.025, 0.000, 0.450),
    (0.027, -0.045, 0.447),
    (0.028, -0.078, 0.445),
    (0.029, -0.106, 0.443),
    (0.047, 0.010, 0.450),
    (0.052, -0.030, 0.447),
    (0.055, -0.060, 0.445),
    (0.058, -0.085, 0.443),
)


def build_synthetic_observation(
    *,
    stamp,
    sequence: int,
    frame_id: str,
    source: str,
    handedness: int,
    confidence: float,
    motion_amplitude_m: float,
) -> HandObservation:
    message = HandObservation()
    message.header.stamp = stamp
    message.header.frame_id = frame_id
    message.schema_version = SCHEMA_VERSION
    message.sequence = sequence
    message.handedness = handedness
    message.source = source

    phase = sequence * 0.08
    offset_x = motion_amplitude_m * sin(phase)
    focal_length_px = 600.0

    for index, (base_x, base_y, base_z) in enumerate(BASE_HAND_POINTS_M):
        x = base_x + offset_x
        point_3d = Point(x=x, y=base_y, z=base_z)
        point_2d = Point(
            x=320.0 + focal_length_px * x / base_z,
            y=240.0 + focal_length_px * base_y / base_z,
            z=0.0,
        )
        message.joints_2d_px[index] = point_2d
        message.joints_3d_m[index] = point_3d

    message.joints_3d_valid = [True] * len(BASE_HAND_POINTS_M)
    message.confidence = [confidence] * len(BASE_HAND_POINTS_M)
    message.valid = True
    return message


class SyntheticHandPublisher(Node):
    def __init__(self) -> None:
        super().__init__("synthetic_hand_publisher")
        self.declare_parameter("frequency_hz", 30.0)
        self.declare_parameter("frame_id", "camera_optical_frame")
        self.declare_parameter("source", "synthetic")
        self.declare_parameter("handedness", "right")
        self.declare_parameter("confidence", 0.99)
        self.declare_parameter("motion_amplitude_m", 0.015)

        self._frequency_hz = float(self.get_parameter("frequency_hz").value)
        self._frame_id = str(self.get_parameter("frame_id").value)
        self._source = str(self.get_parameter("source").value)
        self._confidence = float(self.get_parameter("confidence").value)
        self._motion_amplitude_m = float(
            self.get_parameter("motion_amplitude_m").value
        )
        handedness = str(self.get_parameter("handedness").value).lower()

        if self._frequency_hz <= 0.0:
            raise ValueError("frequency_hz must be positive")
        if not self._frame_id:
            raise ValueError("frame_id must be non-empty")
        if not self._source:
            raise ValueError("source must be non-empty")
        if not 0.0 <= self._confidence <= 1.0:
            raise ValueError("confidence must be in [0, 1]")
        handedness_values = {
            "unknown": HandObservation.HANDEDNESS_UNKNOWN,
            "left": HandObservation.HANDEDNESS_LEFT,
            "right": HandObservation.HANDEDNESS_RIGHT,
        }
        if handedness not in handedness_values:
            raise ValueError("handedness must be unknown, left, or right")
        self._handedness = handedness_values[handedness]

        self._sequence = 0
        self._publisher = self.create_publisher(
            HandObservation,
            "/hand/observation/raw",
            qos_profile_sensor_data,
        )
        self._timer = self.create_timer(1.0 / self._frequency_hz, self._publish)
        self.get_logger().info(
            f"publishing deterministic synthetic hand at {self._frequency_hz:.1f} Hz"
        )

    def _publish(self) -> None:
        message = build_synthetic_observation(
            stamp=self.get_clock().now().to_msg(),
            sequence=self._sequence,
            frame_id=self._frame_id,
            source=self._source,
            handedness=self._handedness,
            confidence=self._confidence,
            motion_amplitude_m=self._motion_amplitude_m,
        )
        self._publisher.publish(message)
        self._sequence += 1


def main(args=None) -> None:
    rclpy.init(args=args)
    node = SyntheticHandPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
