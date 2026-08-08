"""Fail-closed CPU retargeting from a validated hand to a prototype target."""

from dataclasses import dataclass
from enum import IntEnum
import json
from math import acos, isfinite, pi, sqrt
from pathlib import Path
from typing import Iterable

from .calibration import CalibrationRecord, transform_observation_points
from .filtering import OneEuroVectorFilter
from .geometry import QuaternionXyzw, Vector3, quaternion_from_basis, rotate_vector
from .palm import PalmNormalizedHand, build_palm_frame, normalize_hand
from .validation import EXPECTED_SCHEMA_VERSION, HandObservationData


FINGER_CHAINS = (
    (1, 2, 3, 4),
    (5, 6, 7, 8),
    (9, 10, 11, 12),
    (13, 14, 15, 16),
    (17, 18, 19, 20),
)


class RetargetStatus(IntEnum):
    OK = 0
    INPUT_INVALID = 1
    CALIBRATION_INVALID = 2
    IK_FAILED = 3
    OUT_OF_WORKSPACE = 4
    JOINT_LIMIT = 5
    STALE_INPUT = 6


@dataclass(frozen=True)
class RetargetingConfig:
    schema_version: str
    output_frame: str
    target_handedness: str
    target_palm_width_m: float
    minimum_palm_width_m: float
    workspace_min_m: Vector3
    workspace_max_m: Vector3
    finger_joint_names: tuple[str, ...]
    finger_position_min_rad: tuple[float, ...]
    finger_position_max_rad: tuple[float, ...]
    max_ee_linear_velocity_m_s: float
    max_ee_angular_velocity_rad_s: float
    max_finger_velocity_rad_s: tuple[float, ...]
    maximum_input_age_ms: float
    one_euro_min_cutoff_hz: float
    one_euro_beta: float
    one_euro_derivative_cutoff_hz: float


@dataclass(frozen=True)
class RobotTargetData:
    timestamp_ns: int
    frame_id: str
    schema_version: str
    sequence: int
    position_m: Vector3
    quaternion_xyzw: QuaternionXyzw
    finger_joint_names: tuple[str, ...]
    finger_joint_positions_rad: tuple[float, ...]
    max_ee_linear_velocity_m_s: float
    max_ee_angular_velocity_rad_s: float
    max_finger_velocity_rad_s: tuple[float, ...]
    valid: bool
    status_code: RetargetStatus
    status_message: str
    mapping: str
    rate_limited: bool


def _finite_tuple(values: Iterable[float], length: int, label: str) -> tuple[float, ...]:
    converted = tuple(float(value) for value in values)
    if len(converted) != length or not all(isfinite(value) for value in converted):
        raise ValueError(f"{label} must contain {length} finite values")
    return converted


def _positive(value: float, label: str, *, allow_zero: bool = False) -> float:
    converted = float(value)
    valid = converted >= 0.0 if allow_zero else converted > 0.0
    if not isfinite(converted) or not valid:
        qualifier = "non-negative" if allow_zero else "positive"
        raise ValueError(f"{label} must be finite and {qualifier}")
    return converted


def load_retargeting_config(path: str | Path) -> RetargetingConfig:
    source_path = Path(path)
    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot load retargeting config {source_path}: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError("retargeting config root must be an object")
    try:
        schema_version = str(payload["schema_version"])
        output_frame = str(payload["output_frame"]).strip()
        target_handedness = str(payload["target_handedness"]).strip().lower()
        target_palm_width_m = _positive(
            payload["target_palm_width_m"], "target_palm_width_m"
        )
        minimum_palm_width_m = _positive(
            payload["minimum_palm_width_m"], "minimum_palm_width_m"
        )
        workspace_min_m = _finite_tuple(payload["workspace_min_m"], 3, "workspace_min_m")
        workspace_max_m = _finite_tuple(payload["workspace_max_m"], 3, "workspace_max_m")
        names = tuple(str(value).strip() for value in payload["finger_joint_names"])
        position_min = _finite_tuple(
            payload["finger_position_min_rad"], len(names), "finger_position_min_rad"
        )
        position_max = _finite_tuple(
            payload["finger_position_max_rad"], len(names), "finger_position_max_rad"
        )
        max_finger_velocity = _finite_tuple(
            payload["max_finger_velocity_rad_s"],
            len(names),
            "max_finger_velocity_rad_s",
        )
        max_linear = _positive(
            payload["max_ee_linear_velocity_m_s"], "max_ee_linear_velocity_m_s"
        )
        max_angular = _positive(
            payload["max_ee_angular_velocity_rad_s"],
            "max_ee_angular_velocity_rad_s",
        )
        maximum_input_age_ms = _positive(
            payload["maximum_input_age_ms"], "maximum_input_age_ms"
        )
        filter_payload = payload["one_euro_filter"]
        min_cutoff = _positive(filter_payload["min_cutoff_hz"], "min_cutoff_hz")
        beta = _positive(filter_payload["beta"], "beta", allow_zero=True)
        derivative_cutoff = _positive(
            filter_payload["derivative_cutoff_hz"], "derivative_cutoff_hz"
        )
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, ValueError) and not isinstance(error, KeyError):
            raise
        raise ValueError(f"invalid retargeting config field: {error}") from error

    if schema_version != EXPECTED_SCHEMA_VERSION:
        raise ValueError(f"unsupported schema {schema_version!r}")
    if not output_frame:
        raise ValueError("output_frame must be non-empty")
    if target_handedness not in ("left", "right"):
        raise ValueError("target_handedness must be left or right")
    if len(names) != len(FINGER_CHAINS) or any(not name for name in names):
        raise ValueError("exactly five unique non-empty finger_joint_names are required")
    if len(set(names)) != len(names):
        raise ValueError("finger_joint_names must be unique")
    if any(minimum >= maximum for minimum, maximum in zip(position_min, position_max)):
        raise ValueError("each finger position minimum must be below its maximum")
    if any(value <= 0.0 for value in max_finger_velocity):
        raise ValueError("finger velocity limits must be positive")
    if any(minimum >= maximum for minimum, maximum in zip(workspace_min_m, workspace_max_m)):
        raise ValueError("workspace minimum must be below maximum on every axis")

    return RetargetingConfig(
        schema_version=schema_version,
        output_frame=output_frame,
        target_handedness=target_handedness,
        target_palm_width_m=target_palm_width_m,
        minimum_palm_width_m=minimum_palm_width_m,
        workspace_min_m=workspace_min_m,
        workspace_max_m=workspace_max_m,
        finger_joint_names=names,
        finger_position_min_rad=position_min,
        finger_position_max_rad=position_max,
        max_ee_linear_velocity_m_s=max_linear,
        max_ee_angular_velocity_rad_s=max_angular,
        max_finger_velocity_rad_s=max_finger_velocity,
        maximum_input_age_ms=maximum_input_age_ms,
        one_euro_min_cutoff_hz=min_cutoff,
        one_euro_beta=beta,
        one_euro_derivative_cutoff_hz=derivative_cutoff,
    )


def _finger_closure(points: tuple[Vector3, ...], chain: tuple[int, ...]) -> float:
    """Return an invariant [0, 1] curl proxy from three internal joint angles."""

    bend = 0.0
    for previous, middle, following in zip(chain, chain[1:], chain[2:]):
        first = tuple(points[previous][axis] - points[middle][axis] for axis in range(3))
        second = tuple(points[following][axis] - points[middle][axis] for axis in range(3))
        first_norm = sqrt(sum(value * value for value in first))
        second_norm = sqrt(sum(value * value for value in second))
        if first_norm < 1e-9 or second_norm < 1e-9:
            raise ValueError("finger segment is degenerate")
        cosine = sum(first[axis] * second[axis] for axis in range(3)) / (
            first_norm * second_norm
        )
        interior_angle = acos(max(-1.0, min(1.0, cosine)))
        bend += pi - interior_angle
    return max(0.0, min(1.0, bend / pi))


def _limit_vector_step(
    previous: Vector3,
    requested: Vector3,
    maximum_step: float,
) -> tuple[Vector3, bool]:
    delta = tuple(requested[index] - previous[index] for index in range(3))
    distance = sqrt(sum(value * value for value in delta))
    if distance <= maximum_step or distance == 0.0:
        return requested, False
    ratio = maximum_step / distance
    return (
        tuple(previous[index] + ratio * delta[index] for index in range(3)),
        True,
    )


class SafeRetargeter:
    """Stateful filtered retargeter with workspace, staleness, and rate limits."""

    def __init__(self, calibration: CalibrationRecord, config: RetargetingConfig) -> None:
        if calibration.transform.parent_frame != config.output_frame:
            raise ValueError(
                "calibration parent frame does not match retargeting output frame"
            )
        self.calibration = calibration
        self.config = config
        self._position_filter = OneEuroVectorFilter(
            min_cutoff_hz=config.one_euro_min_cutoff_hz,
            beta=config.one_euro_beta,
            derivative_cutoff_hz=config.one_euro_derivative_cutoff_hz,
        )
        self._last_source: str | None = None
        self._last_target: RobotTargetData | None = None
        self._last_observation_timestamp_ns: int | None = None
        self._last_observation_monotonic_ns: int | None = None

    def reset(self) -> None:
        self._position_filter.reset()
        self._last_source = None
        self._last_target = None
        self._last_observation_timestamp_ns = None
        self._last_observation_monotonic_ns = None

    def retarget(
        self,
        observation: HandObservationData,
        *,
        target_timestamp_ns: int,
        monotonic_timestamp_ns: int | None = None,
    ) -> RobotTargetData:
        now = int(target_timestamp_ns)
        age_ms = (now - observation.timestamp_ns) / 1_000_000.0
        if age_ms < 0.0:
            return self._invalid(now, observation.sequence, RetargetStatus.INPUT_INVALID, "input timestamp is in the future")
        if age_ms > self.config.maximum_input_age_ms:
            return self._invalid(now, observation.sequence, RetargetStatus.STALE_INPUT, f"input age {age_ms:.1f} ms exceeds limit")
        if not observation.valid:
            return self._invalid(now, observation.sequence, RetargetStatus.INPUT_INVALID, "observation is marked invalid")
        required = {0, 5, 9, 17, *(joint for chain in FINGER_CHAINS for joint in chain)}
        if any(not observation.joints_3d_valid[index] for index in required):
            return self._invalid(now, observation.sequence, RetargetStatus.INPUT_INVALID, "required retargeting joint is missing")

        if self._last_source is not None and observation.source != self._last_source:
            self.reset()
        self._last_source = observation.source
        try:
            normalized = normalize_hand(
                observation.joints_3d_m,
                handedness={1: "left", 2: "right"}.get(observation.handedness, "unknown"),
                target_handedness=self.config.target_handedness,
                minimum_palm_width_m=self.config.minimum_palm_width_m,
            )
            scaled_points = normalized.points_at_scale(
                self.config.target_palm_width_m
            )
            points_robot = transform_observation_points(observation, self.calibration)
            position_requested = points_robot[0]
            position_filtered = self._position_filter.update(
                position_requested, observation.timestamp_ns
            )
            frame_camera = build_palm_frame(
                observation.joints_3d_m,
                handedness=normalized.frame.handedness,
                minimum_palm_width_m=self.config.minimum_palm_width_m,
            )
            quaternion = quaternion_from_basis(
                rotate_vector(self.calibration.transform.quaternion_xyzw, frame_camera.x_axis),
                rotate_vector(self.calibration.transform.quaternion_xyzw, frame_camera.y_axis),
                rotate_vector(self.calibration.transform.quaternion_xyzw, frame_camera.z_axis),
            )
            finger_requested = tuple(
                minimum + _finger_closure(scaled_points, chain) * (maximum - minimum)
                for chain, minimum, maximum in zip(
                    FINGER_CHAINS,
                    self.config.finger_position_min_rad,
                    self.config.finger_position_max_rad,
                )
            )
        except (IndexError, TypeError, ValueError) as error:
            return self._invalid(now, observation.sequence, RetargetStatus.INPUT_INVALID, str(error))

        if not all(
            minimum <= value <= maximum
            for value, minimum, maximum in zip(
                position_filtered,
                self.config.workspace_min_m,
                self.config.workspace_max_m,
            )
        ):
            return self._invalid(
                now,
                observation.sequence,
                RetargetStatus.OUT_OF_WORKSPACE,
                f"filtered wrist {position_filtered} is outside configured workspace",
                mapping=normalized.mapping,
            )

        position = position_filtered
        finger_positions = finger_requested
        rate_limited = False
        previous = self._last_target
        if (
            previous is not None
            and previous.valid
            and self._last_observation_timestamp_ns is not None
        ):
            dt_s = (
                observation.timestamp_ns - self._last_observation_timestamp_ns
            ) / 1_000_000_000.0
            if dt_s <= 0.0:
                return self._invalid(now, observation.sequence, RetargetStatus.INPUT_INVALID, "retarget timestamp is non-monotonic", mapping=normalized.mapping)
            position, position_limited = _limit_vector_step(
                previous.position_m,
                position,
                self.config.max_ee_linear_velocity_m_s * dt_s,
            )
            limited_fingers = []
            finger_limited = False
            for old, requested, velocity in zip(
                previous.finger_joint_positions_rad,
                finger_requested,
                self.config.max_finger_velocity_rad_s,
            ):
                maximum_delta = velocity * dt_s
                delta = requested - old
                limited_delta = max(-maximum_delta, min(maximum_delta, delta))
                limited_fingers.append(old + limited_delta)
                finger_limited = finger_limited or abs(limited_delta - delta) > 1e-12
            finger_positions = tuple(limited_fingers)
            rate_limited = position_limited or finger_limited

        target = RobotTargetData(
            timestamp_ns=now,
            frame_id=self.config.output_frame,
            schema_version=self.config.schema_version,
            sequence=observation.sequence,
            position_m=position,
            quaternion_xyzw=quaternion,
            finger_joint_names=self.config.finger_joint_names,
            finger_joint_positions_rad=finger_positions,
            max_ee_linear_velocity_m_s=self.config.max_ee_linear_velocity_m_s,
            max_ee_angular_velocity_rad_s=self.config.max_ee_angular_velocity_rad_s,
            max_finger_velocity_rad_s=self.config.max_finger_velocity_rad_s,
            valid=True,
            status_code=RetargetStatus.OK,
            status_message=(
                f"ok; mapping={normalized.mapping}; rate_limited={str(rate_limited).lower()}"
            ),
            mapping=normalized.mapping,
            rate_limited=rate_limited,
        )
        self._last_target = target
        self._last_observation_timestamp_ns = observation.timestamp_ns
        self._last_observation_monotonic_ns = (
            int(monotonic_timestamp_ns)
            if monotonic_timestamp_ns is not None
            else None
        )
        return target

    def watchdog_target(
        self,
        *,
        target_timestamp_ns: int,
        monotonic_timestamp_ns: int,
    ) -> RobotTargetData | None:
        """Emit one invalid target after input becomes stale; never repeat commands."""

        if self._last_target is None or not self._last_target.valid:
            return None
        if self._last_observation_monotonic_ns is None:
            return None
        age_ms = (
            int(monotonic_timestamp_ns) - self._last_observation_monotonic_ns
        ) / 1_000_000.0
        if age_ms <= self.config.maximum_input_age_ms:
            return None
        invalid = self._invalid(
            int(target_timestamp_ns),
            self._last_target.sequence,
            RetargetStatus.STALE_INPUT,
            f"watchdog input age {age_ms:.1f} ms exceeds limit",
            mapping=self._last_target.mapping,
        )
        self._last_target = invalid
        return invalid

    def _invalid(
        self,
        timestamp_ns: int,
        sequence: int,
        status: RetargetStatus,
        message: str,
        *,
        mapping: str = "unavailable",
    ) -> RobotTargetData:
        return RobotTargetData(
            timestamp_ns=timestamp_ns,
            frame_id=self.config.output_frame,
            schema_version=self.config.schema_version,
            sequence=sequence,
            position_m=(0.0, 0.0, 0.0),
            quaternion_xyzw=(0.0, 0.0, 0.0, 1.0),
            finger_joint_names=self.config.finger_joint_names,
            finger_joint_positions_rad=(0.0,) * len(self.config.finger_joint_names),
            max_ee_linear_velocity_m_s=self.config.max_ee_linear_velocity_m_s,
            max_ee_angular_velocity_rad_s=self.config.max_ee_angular_velocity_rad_s,
            max_finger_velocity_rad_s=self.config.max_finger_velocity_rad_s,
            valid=False,
            status_code=status,
            status_message=message,
            mapping=mapping,
            rate_limited=False,
        )
