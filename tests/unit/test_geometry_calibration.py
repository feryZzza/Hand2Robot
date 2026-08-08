import json
from math import cos, pi, sin
from pathlib import Path
import tempfile
import unittest

from hand2robot_core.calibration import load_calibration, transform_observation_points
from hand2robot_core.geometry import RigidTransform
from hand2robot_core.recorded_sequence import load_recorded_sequence


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CALIBRATION_PATH = (
    PROJECT_ROOT
    / "configs"
    / "calibration"
    / "synthetic_camera_to_robot_v0.1.json"
)
RECORDED_PATH = (
    PROJECT_ROOT
    / "ros2_ws"
    / "src"
    / "hand_pipeline"
    / "examples"
    / "recorded_hand_static_v0.1.json"
)


def assert_point_close(test_case, actual, expected, places=9):
    for actual_value, expected_value in zip(actual, expected):
        test_case.assertAlmostEqual(actual_value, expected_value, places=places)


class RigidTransformTest(unittest.TestCase):
    def test_identity(self) -> None:
        transform = RigidTransform.identity("camera_optical_frame")
        assert_point_close(self, transform.apply((1.0, 2.0, 3.0)), (1.0, 2.0, 3.0))

    def test_inverse_round_trip(self) -> None:
        half_angle = pi / 4.0
        transform = RigidTransform(
            "robot_base",
            "camera_optical_frame",
            (0.5, -0.2, 0.8),
            (0.0, 0.0, sin(half_angle), cos(half_angle)),
        )
        point = (0.1, -0.3, 0.4)
        assert_point_close(self, transform.inverse().apply(transform.apply(point)), point)

    def test_composition_order(self) -> None:
        transform_a_b = RigidTransform(
            "a", "b", (1.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)
        )
        transform_b_c = RigidTransform(
            "b", "c", (0.0, 2.0, 0.0), (0.0, 0.0, 0.0, 1.0)
        )
        transform_a_c = transform_a_b.compose(transform_b_c)
        self.assertEqual((transform_a_c.parent_frame, transform_a_c.child_frame), ("a", "c"))
        assert_point_close(self, transform_a_c.apply((0.0, 0.0, 3.0)), (1.0, 2.0, 3.0))

    def test_rejects_non_unit_quaternion(self) -> None:
        with self.assertRaisesRegex(ValueError, "unit length"):
            RigidTransform("a", "b", (0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 2.0))

    def test_rejects_frame_mismatch_during_composition(self) -> None:
        transform_a_b = RigidTransform.identity("a")
        transform_c_d = RigidTransform.identity("c")
        with self.assertRaisesRegex(ValueError, "frame mismatch"):
            transform_a_b.compose(transform_c_d)


class CalibrationTest(unittest.TestCase):
    def test_loads_fixture_in_declared_direction(self) -> None:
        calibration = load_calibration(
            CALIBRATION_PATH,
            expected_parent_frame="robot_base",
            expected_child_frame="camera_optical_frame",
        )
        self.assertEqual(calibration.transform.parent_frame, "robot_base")
        self.assertEqual(calibration.transform.child_frame, "camera_optical_frame")

    def test_transforms_recorded_wrist_without_publishing_command(self) -> None:
        calibration = load_calibration(CALIBRATION_PATH)
        sequence = load_recorded_sequence(RECORDED_PATH)
        points_robot_base = transform_observation_points(
            sequence.observation_at(0), calibration
        )
        assert_point_close(self, points_robot_base[0], (0.5, 0.06, 1.25))
        self.assertEqual(len(points_robot_base), 21)

    def test_rejects_reversed_expected_frames(self) -> None:
        with self.assertRaisesRegex(ValueError, "expected parent"):
            load_calibration(
                CALIBRATION_PATH,
                expected_parent_frame="camera_optical_frame",
                expected_child_frame="robot_base",
            )

    def test_detects_millimetres_stored_as_metres(self) -> None:
        payload = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))
        payload["translation_m"] = [500.0, 0.0, 800.0]
        with self.assertRaisesRegex(ValueError, "metre/millimetre"):
            self._load_modified(payload)

    def test_detects_degrees_stored_as_radians(self) -> None:
        payload = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))
        payload["residual_rotation_rad"] = 90.0
        with self.assertRaisesRegex(ValueError, "radian"):
            self._load_modified(payload)

    def test_rejects_observation_in_wrong_frame(self) -> None:
        calibration = load_calibration(CALIBRATION_PATH)
        sequence = load_recorded_sequence(RECORDED_PATH)
        observation = sequence.observation_at(0)
        wrong_frame_observation = type(observation)(
            **{**observation.__dict__, "frame_id": "world"}
        )
        with self.assertRaisesRegex(ValueError, "does not match"):
            transform_observation_points(wrong_frame_observation, calibration)

    def _load_modified(self, payload):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "calibration.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return load_calibration(path)


if __name__ == "__main__":
    unittest.main()
