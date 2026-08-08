"""Conversions between ROS messages and the ROS-agnostic core."""

from hand2robot_core.validation import HandObservationData
from hand_msgs.msg import HandObservation


def hand_observation_from_ros(message: HandObservation) -> HandObservationData:
    timestamp_ns = message.header.stamp.sec * 1_000_000_000 + message.header.stamp.nanosec
    return HandObservationData(
        timestamp_ns=timestamp_ns,
        frame_id=message.header.frame_id,
        schema_version=message.schema_version,
        sequence=message.sequence,
        handedness=message.handedness,
        source=message.source,
        joints_2d_px=tuple((point.x, point.y, point.z) for point in message.joints_2d_px),
        joints_3d_m=tuple((point.x, point.y, point.z) for point in message.joints_3d_m),
        joints_3d_valid=tuple(message.joints_3d_valid),
        confidence=tuple(message.confidence),
        valid=message.valid,
    )
