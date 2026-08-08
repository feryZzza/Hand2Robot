"""Deterministic validation for the HandObservation contract."""

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import Sequence, Tuple


EXPECTED_SCHEMA_VERSION = "0.1.0"
HAND_JOINT_COUNT = 21
HANDEDNESS_VALUES = frozenset((0, 1, 2))
Point3 = Tuple[float, float, float]


class ValidationCode(str, Enum):
    OK = "ok"
    UNSUPPORTED_SCHEMA = "unsupported_schema"
    TIMESTAMP_INVALID = "timestamp_invalid"
    TIMESTAMP_NON_MONOTONIC = "timestamp_non_monotonic"
    SEQUENCE_NON_MONOTONIC = "sequence_non_monotonic"
    SEQUENCE_GAP = "sequence_gap"
    FRAME_ID_EMPTY = "frame_id_empty"
    SOURCE_EMPTY = "source_empty"
    HANDEDNESS_INVALID = "handedness_invalid"
    ARRAY_LENGTH = "array_length"
    NON_FINITE = "non_finite"
    IMAGE_Z_NONZERO = "image_z_nonzero"
    CONFIDENCE_RANGE = "confidence_range"
    OBSERVATION_MARKED_INVALID = "observation_marked_invalid"
    LOW_CONFIDENCE = "low_confidence"


@dataclass(frozen=True)
class HandObservationData:
    timestamp_ns: int
    frame_id: str
    schema_version: str
    sequence: int
    handedness: int
    source: str
    joints_2d_px: Sequence[Point3]
    joints_3d_m: Sequence[Point3]
    joints_3d_valid: Sequence[bool]
    confidence: Sequence[float]
    valid: bool


@dataclass(frozen=True)
class ValidationResult:
    accepted: bool
    code: ValidationCode
    message: str
    dropped_since_last: int = 0
    confident_joint_count: int = 0


class HandObservationValidator:
    """Stateful source-session validator with deterministic counters."""

    def __init__(
        self,
        confidence_threshold: float = 0.5,
        minimum_confident_joints: int = 15,
    ) -> None:
        if not 0.0 <= confidence_threshold <= 1.0:
            raise ValueError("confidence_threshold must be in [0, 1]")
        if not 0 <= minimum_confident_joints <= HAND_JOINT_COUNT:
            raise ValueError("minimum_confident_joints must be in [0, 21]")

        self.confidence_threshold = confidence_threshold
        self.minimum_confident_joints = minimum_confident_joints
        self.received_count = 0
        self.valid_count = 0
        self.invalid_count = 0
        self.dropped_count = 0
        self.last_error_code = ""
        self.last_error_message = ""
        self._last_timestamp_ns: int | None = None
        self._last_sequence: int | None = None
        self._active_source = ""

    @property
    def active_source(self) -> str:
        return self._active_source

    @property
    def drop_rate(self) -> float:
        denominator = self.received_count + self.dropped_count
        return self.dropped_count / denominator if denominator else 0.0

    def reset_source_session(self, source: str = "") -> None:
        """Reset only ordering state; cumulative diagnostic counters remain monotonic."""

        self._active_source = source.strip()
        self._last_timestamp_ns = None
        self._last_sequence = None

    def validate(self, observation: HandObservationData) -> ValidationResult:
        self.received_count += 1

        if observation.schema_version != EXPECTED_SCHEMA_VERSION:
            return self._reject(
                ValidationCode.UNSUPPORTED_SCHEMA,
                f"expected {EXPECTED_SCHEMA_VERSION}, got {observation.schema_version!r}",
            )
        if observation.timestamp_ns <= 0:
            return self._reject(
                ValidationCode.TIMESTAMP_INVALID,
                "timestamp must be positive",
            )
        if not observation.frame_id.strip():
            return self._reject(ValidationCode.FRAME_ID_EMPTY, "frame_id is empty")
        if not observation.source.strip():
            return self._reject(ValidationCode.SOURCE_EMPTY, "source is empty")
        if observation.handedness not in HANDEDNESS_VALUES:
            return self._reject(
                ValidationCode.HANDEDNESS_INVALID,
                f"unsupported handedness value {observation.handedness}",
            )

        lengths = (
            len(observation.joints_2d_px),
            len(observation.joints_3d_m),
            len(observation.joints_3d_valid),
            len(observation.confidence),
        )
        if any(length != HAND_JOINT_COUNT for length in lengths):
            return self._reject(
                ValidationCode.ARRAY_LENGTH,
                f"expected four arrays of length {HAND_JOINT_COUNT}, got {lengths}",
            )

        for index, point in enumerate(observation.joints_2d_px):
            if len(point) != 3 or not all(isfinite(value) for value in point):
                return self._reject(
                    ValidationCode.NON_FINITE,
                    f"2D joint {index} is malformed or non-finite",
                )
            if abs(point[2]) > 1e-9:
                return self._reject(
                    ValidationCode.IMAGE_Z_NONZERO,
                    f"2D joint {index} has non-zero z={point[2]}",
                )

        for index, point in enumerate(observation.joints_3d_m):
            if len(point) != 3 or not all(isfinite(value) for value in point):
                return self._reject(
                    ValidationCode.NON_FINITE,
                    f"3D joint {index} is malformed or non-finite",
                )

        for index, confidence in enumerate(observation.confidence):
            if not isfinite(confidence):
                return self._reject(
                    ValidationCode.NON_FINITE,
                    f"confidence {index} is non-finite",
                )
            if not 0.0 <= confidence <= 1.0:
                return self._reject(
                    ValidationCode.CONFIDENCE_RANGE,
                    f"confidence {index}={confidence} is outside [0, 1]",
                )

        if observation.source != self._active_source:
            self.reset_source_session(observation.source)

        if self._last_timestamp_ns is not None and observation.timestamp_ns <= self._last_timestamp_ns:
            return self._reject(
                ValidationCode.TIMESTAMP_NON_MONOTONIC,
                f"timestamp {observation.timestamp_ns} <= {self._last_timestamp_ns}",
            )
        if self._last_sequence is not None and observation.sequence <= self._last_sequence:
            return self._reject(
                ValidationCode.SEQUENCE_NON_MONOTONIC,
                f"sequence {observation.sequence} <= {self._last_sequence}",
            )

        dropped_since_last = 0
        if self._last_sequence is not None:
            dropped_since_last = observation.sequence - self._last_sequence - 1
            self.dropped_count += dropped_since_last

        self._last_timestamp_ns = observation.timestamp_ns
        self._last_sequence = observation.sequence

        if not observation.valid:
            return self._reject(
                ValidationCode.OBSERVATION_MARKED_INVALID,
                "source marked observation invalid",
                dropped_since_last=dropped_since_last,
            )

        confident_joint_count = sum(
            confidence >= self.confidence_threshold and is_3d_valid
            for confidence, is_3d_valid in zip(
                observation.confidence, observation.joints_3d_valid
            )
        )
        if confident_joint_count < self.minimum_confident_joints:
            return self._reject(
                ValidationCode.LOW_CONFIDENCE,
                (
                    f"{confident_joint_count} confident 3D joints; "
                    f"minimum is {self.minimum_confident_joints}"
                ),
                dropped_since_last=dropped_since_last,
                confident_joint_count=confident_joint_count,
            )

        self.valid_count += 1
        if dropped_since_last:
            code = ValidationCode.SEQUENCE_GAP
            message = f"accepted with {dropped_since_last} dropped sequence(s)"
            self.last_error_code = code.value
            self.last_error_message = message
        else:
            code = ValidationCode.OK
            message = "accepted"

        return ValidationResult(
            accepted=True,
            code=code,
            message=message,
            dropped_since_last=dropped_since_last,
            confident_joint_count=confident_joint_count,
        )

    def _reject(
        self,
        code: ValidationCode,
        message: str,
        dropped_since_last: int = 0,
        confident_joint_count: int = 0,
    ) -> ValidationResult:
        self.invalid_count += 1
        self.last_error_code = code.value
        self.last_error_message = message
        return ValidationResult(
            accepted=False,
            code=code,
            message=message,
            dropped_since_last=dropped_since_last,
            confident_joint_count=confident_joint_count,
        )
