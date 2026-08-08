"""Conversions between ROS messages and the ROS-agnostic core."""

from geometry_msgs.msg import Point
from hand2robot_core.episode import EpisodeRecordData
from hand2robot_core.retargeting import RetargetStatus, RobotTargetData
from hand2robot_core.validation import HandObservationData
from hand_msgs.msg import EpisodeRecord, HandObservation, RobotTarget


def hand_observation_from_ros(message: HandObservation) -> HandObservationData:
    timestamp_ns = message.header.stamp.sec * 1_000_000_000 + message.header.stamp.nanosec
    return HandObservationData(
        timestamp_ns=timestamp_ns,
        frame_id=message.header.frame_id,
        schema_version=message.schema_version,
        sequence=int(message.sequence),
        handedness=int(message.handedness),
        source=message.source,
        joints_2d_px=tuple(
            (float(point.x), float(point.y), float(point.z))
            for point in message.joints_2d_px
        ),
        joints_3d_m=tuple(
            (float(point.x), float(point.y), float(point.z))
            for point in message.joints_3d_m
        ),
        joints_3d_valid=tuple(bool(value) for value in message.joints_3d_valid),
        confidence=tuple(float(value) for value in message.confidence),
        valid=bool(message.valid),
    )


def _set_time(message, timestamp_ns: int) -> None:
    message.sec = int(timestamp_ns) // 1_000_000_000
    message.nanosec = int(timestamp_ns) % 1_000_000_000


def hand_observation_to_ros(data: HandObservationData) -> HandObservation:
    message = HandObservation()
    _set_time(message.header.stamp, data.timestamp_ns)
    message.header.frame_id = data.frame_id
    message.schema_version = data.schema_version
    message.sequence = int(data.sequence)
    message.handedness = int(data.handedness)
    message.source = data.source
    for index, point in enumerate(data.joints_2d_px):
        message.joints_2d_px[index] = Point(x=point[0], y=point[1], z=point[2])
    for index, point in enumerate(data.joints_3d_m):
        message.joints_3d_m[index] = Point(x=point[0], y=point[1], z=point[2])
    message.joints_3d_valid = [bool(value) for value in data.joints_3d_valid]
    message.confidence = [float(value) for value in data.confidence]
    message.valid = bool(data.valid)
    return message


def robot_target_from_ros(message: RobotTarget) -> RobotTargetData:
    timestamp_ns = message.header.stamp.sec * 1_000_000_000 + message.header.stamp.nanosec
    return RobotTargetData(
        timestamp_ns=timestamp_ns,
        frame_id=message.header.frame_id,
        schema_version=message.schema_version,
        sequence=int(message.sequence),
        position_m=(
            float(message.end_effector_pose.position.x),
            float(message.end_effector_pose.position.y),
            float(message.end_effector_pose.position.z),
        ),
        quaternion_xyzw=(
            float(message.end_effector_pose.orientation.x),
            float(message.end_effector_pose.orientation.y),
            float(message.end_effector_pose.orientation.z),
            float(message.end_effector_pose.orientation.w),
        ),
        finger_joint_names=tuple(message.finger_joint_names),
        finger_joint_positions_rad=tuple(
            float(value) for value in message.finger_joint_positions_rad
        ),
        max_ee_linear_velocity_m_s=float(message.max_ee_linear_velocity_m_s),
        max_ee_angular_velocity_rad_s=float(message.max_ee_angular_velocity_rad_s),
        max_finger_velocity_rad_s=tuple(
            float(value) for value in message.max_finger_velocity_rad_s
        ),
        valid=bool(message.valid),
        status_code=RetargetStatus(int(message.status_code)),
        status_message=message.status_message,
        mapping=_mapping_from_status(message.status_message),
        rate_limited="rate_limited=true" in message.status_message,
    )


def _mapping_from_status(status_message: str) -> str:
    for item in status_message.split(";"):
        key, separator, value = item.strip().partition("=")
        if separator and key == "mapping":
            return value
    return "unavailable"


def robot_target_to_ros(data: RobotTargetData) -> RobotTarget:
    message = RobotTarget()
    _set_time(message.header.stamp, data.timestamp_ns)
    message.header.frame_id = data.frame_id
    message.schema_version = data.schema_version
    message.sequence = int(data.sequence)
    message.end_effector_pose.position.x = data.position_m[0]
    message.end_effector_pose.position.y = data.position_m[1]
    message.end_effector_pose.position.z = data.position_m[2]
    message.end_effector_pose.orientation.x = data.quaternion_xyzw[0]
    message.end_effector_pose.orientation.y = data.quaternion_xyzw[1]
    message.end_effector_pose.orientation.z = data.quaternion_xyzw[2]
    message.end_effector_pose.orientation.w = data.quaternion_xyzw[3]
    message.finger_joint_names = list(data.finger_joint_names)
    message.finger_joint_positions_rad = [
        float(value) for value in data.finger_joint_positions_rad
    ]
    message.max_ee_linear_velocity_m_s = float(data.max_ee_linear_velocity_m_s)
    message.max_ee_angular_velocity_rad_s = float(data.max_ee_angular_velocity_rad_s)
    message.max_finger_velocity_rad_s = [
        float(value) for value in data.max_finger_velocity_rad_s
    ]
    message.valid = bool(data.valid)
    message.status_code = int(data.status_code)
    message.status_message = data.status_message
    return message


def episode_record_to_ros(data: EpisodeRecordData) -> EpisodeRecord:
    message = EpisodeRecord()
    message.schema_version = data.schema_version
    message.episode_id = data.episode_id
    message.step_index = data.step_index
    _set_time(message.record_timestamp, data.record_timestamp_ns)
    if data.observation is not None:
        message.observation = hand_observation_to_ros(data.observation)
    else:
        message.observation.schema_version = data.schema_version
        message.observation.valid = False
    if data.action is not None:
        message.action = robot_target_to_ros(data.action)
    else:
        message.action.schema_version = data.schema_version
        message.action.valid = False
        message.action.status_code = RobotTarget.STATUS_INPUT_INVALID
    _set_time(message.observation_timestamp, data.observation_timestamp_ns)
    _set_time(message.action_timestamp, data.action_timestamp_ns)
    message.observation_missing = data.observation_missing
    message.action_missing = data.action_missing
    message.task = data.task
    message.episode_complete = data.episode_complete
    message.success = data.success
    message.failure_reason = data.failure_reason
    return message
