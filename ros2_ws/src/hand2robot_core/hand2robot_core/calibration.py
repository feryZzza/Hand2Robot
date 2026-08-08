"""Strict loading and application of camera-to-robot calibration records."""

from dataclasses import dataclass
from datetime import datetime
import json
from math import isfinite, pi, sqrt
from pathlib import Path

from .geometry import RigidTransform, Vector3
from .validation import EXPECTED_SCHEMA_VERSION, HandObservationData


@dataclass(frozen=True)
class CalibrationRecord:
    schema_version: str
    transform: RigidTransform
    method: str
    source: str
    created_at: str
    residual_translation_m: float
    residual_rotation_rad: float


def load_calibration(
    path: str | Path,
    *,
    expected_parent_frame: str | None = None,
    expected_child_frame: str | None = None,
    maximum_translation_m: float = 10.0,
) -> CalibrationRecord:
    source_path = Path(path)
    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot load calibration {source_path}: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError("calibration root must be an object")

    try:
        schema_version = str(payload["schema_version"])
        parent_frame = str(payload["parent_frame"])
        child_frame = str(payload["child_frame"])
        translation_m = tuple(float(value) for value in payload["translation_m"])
        quaternion_xyzw = tuple(float(value) for value in payload["quaternion_xyzw"])
        method = str(payload["method"]).strip()
        source = str(payload["source"]).strip()
        created_at = str(payload["created_at"])
        residual_translation_m = float(payload["residual_translation_m"])
        residual_rotation_rad = float(payload["residual_rotation_rad"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"invalid calibration field: {error}") from error

    if schema_version != EXPECTED_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported schema {schema_version!r}; expected {EXPECTED_SCHEMA_VERSION}"
        )
    transform = RigidTransform(
        parent_frame=parent_frame,
        child_frame=child_frame,
        translation_m=translation_m,
        quaternion_xyzw=quaternion_xyzw,
    )
    if expected_parent_frame and transform.parent_frame != expected_parent_frame:
        raise ValueError(
            f"expected parent {expected_parent_frame}, got {transform.parent_frame}"
        )
    if expected_child_frame and transform.child_frame != expected_child_frame:
        raise ValueError(
            f"expected child {expected_child_frame}, got {transform.child_frame}"
        )
    translation_norm = sqrt(sum(value * value for value in transform.translation_m))
    if not isfinite(maximum_translation_m) or maximum_translation_m <= 0.0:
        raise ValueError("maximum_translation_m must be finite and positive")
    if translation_norm > maximum_translation_m:
        raise ValueError(
            f"translation norm {translation_norm:.3f} m exceeds "
            f"{maximum_translation_m:.3f} m; check metre/millimetre units"
        )
    if not method or not source:
        raise ValueError("method and source must be non-empty")
    try:
        timestamp = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("created_at must be an ISO-8601 timestamp") from error
    if timestamp.tzinfo is None:
        raise ValueError("created_at must include a timezone")
    if (
        not isfinite(residual_translation_m)
        or residual_translation_m < 0.0
        or residual_translation_m > maximum_translation_m
    ):
        raise ValueError("residual_translation_m is invalid or uses the wrong unit")
    if (
        not isfinite(residual_rotation_rad)
        or residual_rotation_rad < 0.0
        or residual_rotation_rad > pi
    ):
        raise ValueError("residual_rotation_rad must be in [0, pi]; check radian units")

    return CalibrationRecord(
        schema_version=schema_version,
        transform=transform,
        method=method,
        source=source,
        created_at=created_at,
        residual_translation_m=residual_translation_m,
        residual_rotation_rad=residual_rotation_rad,
    )


def transform_observation_points(
    observation: HandObservationData,
    calibration: CalibrationRecord,
) -> tuple[Vector3, ...]:
    transform = calibration.transform
    if observation.frame_id != transform.child_frame:
        raise ValueError(
            f"observation frame {observation.frame_id!r} does not match "
            f"calibration child {transform.child_frame!r}"
        )
    output = []
    for point, valid in zip(observation.joints_3d_m, observation.joints_3d_valid):
        output.append(transform.apply(point) if valid else (0.0, 0.0, 0.0))
    return tuple(output)
