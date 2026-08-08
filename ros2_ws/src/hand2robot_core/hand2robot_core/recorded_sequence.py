"""Versioned, dependency-free recorded hand-sequence loader."""

from dataclasses import dataclass
import json
from math import isfinite
from pathlib import Path
from typing import Any

from .validation import (
    EXPECTED_SCHEMA_VERSION,
    HAND_JOINT_COUNT,
    HandObservationData,
    HandObservationValidator,
    Point3,
    ValidationCode,
)


HANDEDNESS_BY_NAME = {"unknown": 0, "left": 1, "right": 2}


@dataclass(frozen=True)
class RecordedPose:
    joints_2d_px: tuple[Point3, ...]
    joints_3d_m: tuple[Point3, ...]
    joints_3d_valid: tuple[bool, ...]
    confidence: tuple[float, ...]


@dataclass(frozen=True)
class RecordedFrame:
    capture_timestamp_ns: int
    sequence: int
    pose_index: int
    valid: bool


@dataclass(frozen=True)
class RecordedSequence:
    schema_version: str
    frame_id: str
    handedness: int
    source: str
    nominal_rate_hz: float
    poses: tuple[RecordedPose, ...]
    frames: tuple[RecordedFrame, ...]

    def observation_at(self, frame_index: int) -> HandObservationData:
        frame = self.frames[frame_index]
        pose = self.poses[frame.pose_index]
        return HandObservationData(
            timestamp_ns=frame.capture_timestamp_ns,
            frame_id=self.frame_id,
            schema_version=self.schema_version,
            sequence=frame.sequence,
            handedness=self.handedness,
            source=self.source,
            joints_2d_px=pose.joints_2d_px,
            joints_3d_m=pose.joints_3d_m,
            joints_3d_valid=pose.joints_3d_valid,
            confidence=pose.confidence,
            valid=frame.valid,
        )


def load_recorded_sequence(path: str | Path) -> RecordedSequence:
    source_path = Path(path)
    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot load recorded sequence {source_path}: {error}") from error

    if not isinstance(payload, dict):
        raise ValueError("recorded sequence root must be an object")

    try:
        schema_version = str(payload["schema_version"])
        frame_id = str(payload["frame_id"]).strip()
        handedness_name = str(payload["handedness"]).lower()
        source = str(payload["source"]).strip()
        nominal_rate_hz = float(payload["nominal_rate_hz"])
        raw_poses = payload["poses"]
        raw_frames = payload["frames"]
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"invalid recorded sequence metadata: {error}") from error

    if schema_version != EXPECTED_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported schema {schema_version!r}; expected {EXPECTED_SCHEMA_VERSION}"
        )
    if not frame_id:
        raise ValueError("frame_id must be non-empty")
    if handedness_name not in HANDEDNESS_BY_NAME:
        raise ValueError("handedness must be unknown, left, or right")
    if not source:
        raise ValueError("source must be non-empty")
    if not isfinite(nominal_rate_hz) or nominal_rate_hz <= 0.0:
        raise ValueError("nominal_rate_hz must be finite and positive")
    if not isinstance(raw_poses, list) or not raw_poses:
        raise ValueError("poses must be a non-empty array")
    if not isinstance(raw_frames, list) or not raw_frames:
        raise ValueError("frames must be a non-empty array")

    poses = tuple(_parse_pose(raw_pose, index) for index, raw_pose in enumerate(raw_poses))
    frames = tuple(
        _parse_frame(raw_frame, index, len(poses))
        for index, raw_frame in enumerate(raw_frames)
    )
    sequence = RecordedSequence(
        schema_version=schema_version,
        frame_id=frame_id,
        handedness=HANDEDNESS_BY_NAME[handedness_name],
        source=source,
        nominal_rate_hz=nominal_rate_hz,
        poses=poses,
        frames=frames,
    )
    _validate_frame_order_and_content(sequence)
    return sequence


def _parse_pose(raw_pose: Any, index: int) -> RecordedPose:
    if not isinstance(raw_pose, dict):
        raise ValueError(f"pose {index} must be an object")
    try:
        points_2d = _parse_points(raw_pose["joints_2d_px"], f"pose {index} joints_2d_px")
        points_3d = _parse_points(raw_pose["joints_3d_m"], f"pose {index} joints_3d_m")
        valid_3d = _parse_bool_array(
            raw_pose["joints_3d_valid"], f"pose {index} joints_3d_valid"
        )
        confidence = _parse_confidence(
            raw_pose["confidence"], f"pose {index} confidence"
        )
    except KeyError as error:
        raise ValueError(f"pose {index} is missing {error.args[0]}") from error
    return RecordedPose(points_2d, points_3d, valid_3d, confidence)


def _parse_points(raw_points: Any, label: str) -> tuple[Point3, ...]:
    if not isinstance(raw_points, list) or len(raw_points) != HAND_JOINT_COUNT:
        raise ValueError(f"{label} must contain {HAND_JOINT_COUNT} points")
    points = []
    for point_index, raw_point in enumerate(raw_points):
        if not isinstance(raw_point, list) or len(raw_point) != 3:
            raise ValueError(f"{label}[{point_index}] must contain x, y, z")
        try:
            point = tuple(float(value) for value in raw_point)
        except (TypeError, ValueError) as error:
            raise ValueError(f"{label}[{point_index}] is not numeric") from error
        if not all(isfinite(value) for value in point):
            raise ValueError(f"{label}[{point_index}] must be finite")
        points.append(point)
    return tuple(points)


def _parse_bool_array(raw_values: Any, label: str) -> tuple[bool, ...]:
    if not isinstance(raw_values, list) or len(raw_values) != HAND_JOINT_COUNT:
        raise ValueError(f"{label} must contain {HAND_JOINT_COUNT} booleans")
    if not all(isinstance(value, bool) for value in raw_values):
        raise ValueError(f"{label} values must be booleans")
    return tuple(raw_values)


def _parse_confidence(raw_values: Any, label: str) -> tuple[float, ...]:
    if not isinstance(raw_values, list) or len(raw_values) != HAND_JOINT_COUNT:
        raise ValueError(f"{label} must contain {HAND_JOINT_COUNT} values")
    try:
        values = tuple(float(value) for value in raw_values)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} values must be numeric") from error
    if not all(isfinite(value) and 0.0 <= value <= 1.0 for value in values):
        raise ValueError(f"{label} values must be finite and in [0, 1]")
    return values


def _parse_frame(raw_frame: Any, index: int, pose_count: int) -> RecordedFrame:
    if not isinstance(raw_frame, dict):
        raise ValueError(f"frame {index} must be an object")
    try:
        timestamp_ns = int(raw_frame["capture_timestamp_ns"])
        sequence = int(raw_frame["sequence"])
        pose_index = int(raw_frame["pose_index"])
        valid = raw_frame["valid"]
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"invalid frame {index}: {error}") from error
    if timestamp_ns <= 0:
        raise ValueError(f"frame {index} timestamp must be positive")
    if sequence < 0:
        raise ValueError(f"frame {index} sequence must be non-negative")
    if not 0 <= pose_index < pose_count:
        raise ValueError(f"frame {index} pose_index {pose_index} is out of range")
    if not isinstance(valid, bool):
        raise ValueError(f"frame {index} valid must be a boolean")
    return RecordedFrame(timestamp_ns, sequence, pose_index, valid)


def _validate_frame_order_and_content(sequence: RecordedSequence) -> None:
    if sequence.frames[0].sequence != 0:
        raise ValueError("recorded source session must start at sequence 0")
    validator = HandObservationValidator(
        confidence_threshold=0.0,
        minimum_confident_joints=0,
    )
    for index in range(len(sequence.frames)):
        result = validator.validate(sequence.observation_at(index))
        if not result.accepted and result.code != ValidationCode.OBSERVATION_MARKED_INVALID:
            raise ValueError(f"frame {index} violates observation contract: {result.message}")
