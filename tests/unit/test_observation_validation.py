from dataclasses import replace
from math import nan
import unittest

from hand2robot_core.validation import (
    EXPECTED_SCHEMA_VERSION,
    HAND_JOINT_COUNT,
    HandObservationData,
    HandObservationValidator,
    ValidationCode,
)


def valid_observation(**overrides) -> HandObservationData:
    observation = HandObservationData(
        timestamp_ns=1_000_000_000,
        frame_id="camera_optical_frame",
        schema_version=EXPECTED_SCHEMA_VERSION,
        sequence=0,
        handedness=2,
        source="synthetic",
        joints_2d_px=tuple((float(index), float(index + 1), 0.0) for index in range(21)),
        joints_3d_m=tuple((index * 0.001, 0.0, 0.45) for index in range(21)),
        joints_3d_valid=(True,) * HAND_JOINT_COUNT,
        confidence=(0.99,) * HAND_JOINT_COUNT,
        valid=True,
    )
    return replace(observation, **overrides)


class HandObservationValidatorTest(unittest.TestCase):
    def test_accepts_valid_observation(self) -> None:
        validator = HandObservationValidator()
        result = validator.validate(valid_observation())
        self.assertTrue(result.accepted)
        self.assertEqual(result.code, ValidationCode.OK)
        self.assertEqual(validator.valid_count, 1)
        self.assertEqual(validator.invalid_count, 0)

    def test_rejects_unsupported_schema(self) -> None:
        validator = HandObservationValidator()
        result = validator.validate(valid_observation(schema_version="1.0.0"))
        self.assertFalse(result.accepted)
        self.assertEqual(result.code, ValidationCode.UNSUPPORTED_SCHEMA)

    def test_rejects_non_monotonic_timestamp(self) -> None:
        validator = HandObservationValidator()
        validator.validate(valid_observation(sequence=10, timestamp_ns=2_000))
        result = validator.validate(valid_observation(sequence=11, timestamp_ns=2_000))
        self.assertEqual(result.code, ValidationCode.TIMESTAMP_NON_MONOTONIC)

    def test_rejects_non_monotonic_sequence(self) -> None:
        validator = HandObservationValidator()
        validator.validate(valid_observation(sequence=10, timestamp_ns=2_000))
        result = validator.validate(valid_observation(sequence=10, timestamp_ns=3_000))
        self.assertEqual(result.code, ValidationCode.SEQUENCE_NON_MONOTONIC)

    def test_counts_forward_sequence_gap_and_accepts_sample(self) -> None:
        validator = HandObservationValidator()
        validator.validate(valid_observation(sequence=10, timestamp_ns=2_000))
        result = validator.validate(valid_observation(sequence=13, timestamp_ns=3_000))
        self.assertTrue(result.accepted)
        self.assertEqual(result.code, ValidationCode.SEQUENCE_GAP)
        self.assertEqual(result.dropped_since_last, 2)
        self.assertEqual(validator.dropped_count, 2)
        self.assertAlmostEqual(validator.drop_rate, 0.5)

    def test_rejects_non_finite_joint(self) -> None:
        points = list(valid_observation().joints_3d_m)
        points[4] = (nan, 0.0, 0.45)
        validator = HandObservationValidator()
        result = validator.validate(valid_observation(joints_3d_m=tuple(points)))
        self.assertEqual(result.code, ValidationCode.NON_FINITE)

    def test_rejects_non_zero_image_z(self) -> None:
        points = list(valid_observation().joints_2d_px)
        points[0] = (1.0, 2.0, 0.1)
        validator = HandObservationValidator()
        result = validator.validate(valid_observation(joints_2d_px=tuple(points)))
        self.assertEqual(result.code, ValidationCode.IMAGE_Z_NONZERO)

    def test_rejects_confidence_outside_range(self) -> None:
        confidence = list(valid_observation().confidence)
        confidence[2] = 1.1
        validator = HandObservationValidator()
        result = validator.validate(valid_observation(confidence=tuple(confidence)))
        self.assertEqual(result.code, ValidationCode.CONFIDENCE_RANGE)

    def test_rejects_low_confidence(self) -> None:
        confidence = (0.1,) * 10 + (0.99,) * 11
        validator = HandObservationValidator(minimum_confident_joints=15)
        result = validator.validate(valid_observation(confidence=confidence))
        self.assertEqual(result.code, ValidationCode.LOW_CONFIDENCE)
        self.assertEqual(result.confident_joint_count, 11)

    def test_rejects_source_marked_invalid(self) -> None:
        validator = HandObservationValidator()
        result = validator.validate(valid_observation(valid=False))
        self.assertEqual(result.code, ValidationCode.OBSERVATION_MARKED_INVALID)

    def test_rejects_wrong_array_length(self) -> None:
        validator = HandObservationValidator()
        result = validator.validate(valid_observation(confidence=(0.9,) * 20))
        self.assertEqual(result.code, ValidationCode.ARRAY_LENGTH)

    def test_source_change_resets_ordering_baseline(self) -> None:
        validator = HandObservationValidator()
        validator.validate(
            valid_observation(source="camera_mediapipe", sequence=8, timestamp_ns=5_000)
        )
        result = validator.validate(
            valid_observation(source="recorded", sequence=0, timestamp_ns=2_000)
        )
        self.assertTrue(result.accepted)
        self.assertEqual(validator.active_source, "recorded")


if __name__ == "__main__":
    unittest.main()
