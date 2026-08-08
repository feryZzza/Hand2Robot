from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from hand2robot_core.calibration import load_calibration
from hand2robot_core.geometry import quaternion_norm
from hand2robot_core.recorded_sequence import load_recorded_sequence
from hand2robot_core.retargeting import (
    RetargetStatus,
    SafeRetargeter,
    load_retargeting_config,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CALIBRATION_PATH = PROJECT_ROOT / "configs/calibration/synthetic_camera_to_robot_v0.1.json"
CONFIG_PATH = PROJECT_ROOT / "configs/retargeting/cpu_prototype_v0.1.json"
SEQUENCE_PATH = PROJECT_ROOT / "ros2_ws/src/hand_pipeline/examples/recorded_hand_static_v0.1.json"


class SafeRetargeterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.calibration = load_calibration(CALIBRATION_PATH)
        self.config = load_retargeting_config(CONFIG_PATH)
        self.observation = load_recorded_sequence(SEQUENCE_PATH).observation_at(0)

    def make_retargeter(self) -> SafeRetargeter:
        return SafeRetargeter(self.calibration, self.config)

    def test_valid_target_is_bounded_and_in_robot_frame(self) -> None:
        target = self.make_retargeter().retarget(
            self.observation,
            target_timestamp_ns=self.observation.timestamp_ns + 10_000_000,
            monotonic_timestamp_ns=1_000_000,
        )
        self.assertTrue(target.valid)
        self.assertEqual(target.status_code, RetargetStatus.OK)
        self.assertEqual(target.frame_id, "robot_base")
        self.assertEqual(target.position_m, (0.5, 0.06, 1.25))
        self.assertAlmostEqual(quaternion_norm(target.quaternion_xyzw), 1.0)
        self.assertEqual(len(target.finger_joint_names), 5)
        self.assertEqual(len(target.finger_joint_positions_rad), 5)
        for value, minimum, maximum in zip(
            target.finger_joint_positions_rad,
            self.config.finger_position_min_rad,
            self.config.finger_position_max_rad,
        ):
            self.assertGreaterEqual(value, minimum)
            self.assertLessEqual(value, maximum)

    def test_rejects_stale_input(self) -> None:
        target = self.make_retargeter().retarget(
            self.observation,
            target_timestamp_ns=self.observation.timestamp_ns + 600_000_000,
        )
        self.assertFalse(target.valid)
        self.assertEqual(target.status_code, RetargetStatus.STALE_INPUT)

    def test_rejects_out_of_workspace(self) -> None:
        points = tuple((x + 1.0, y, z) for x, y, z in self.observation.joints_3d_m)
        observation = replace(self.observation, joints_3d_m=points)
        target = self.make_retargeter().retarget(
            observation,
            target_timestamp_ns=observation.timestamp_ns + 1_000_000,
        )
        self.assertFalse(target.valid)
        self.assertEqual(target.status_code, RetargetStatus.OUT_OF_WORKSPACE)

    def test_rejects_missing_required_finger_joint(self) -> None:
        valid = list(self.observation.joints_3d_valid)
        valid[8] = False
        observation = replace(self.observation, joints_3d_valid=tuple(valid))
        target = self.make_retargeter().retarget(
            observation,
            target_timestamp_ns=observation.timestamp_ns + 1_000_000,
        )
        self.assertFalse(target.valid)
        self.assertEqual(target.status_code, RetargetStatus.INPUT_INVALID)

    def test_watchdog_emits_one_invalid_target(self) -> None:
        retargeter = self.make_retargeter()
        retargeter.retarget(
            self.observation,
            target_timestamp_ns=self.observation.timestamp_ns + 1_000_000,
            monotonic_timestamp_ns=1_000_000_000,
        )
        self.assertIsNone(
            retargeter.watchdog_target(
                target_timestamp_ns=self.observation.timestamp_ns + 100_000_000,
                monotonic_timestamp_ns=1_100_000_000,
            )
        )
        stale = retargeter.watchdog_target(
            target_timestamp_ns=self.observation.timestamp_ns + 600_000_000,
            monotonic_timestamp_ns=1_600_000_000,
        )
        self.assertIsNotNone(stale)
        self.assertFalse(stale.valid)
        self.assertEqual(stale.status_code, RetargetStatus.STALE_INPUT)
        self.assertIsNone(
            retargeter.watchdog_target(
                target_timestamp_ns=self.observation.timestamp_ns + 700_000_000,
                monotonic_timestamp_ns=1_700_000_000,
            )
        )

    def test_linear_velocity_limit_bounds_step(self) -> None:
        retargeter = self.make_retargeter()
        first = retargeter.retarget(
            self.observation,
            target_timestamp_ns=self.observation.timestamp_ns + 1_000_000,
        )
        shifted = replace(
            self.observation,
            timestamp_ns=self.observation.timestamp_ns + 100_000_000,
            sequence=1,
            joints_3d_m=tuple((x + 0.2, y, z) for x, y, z in self.observation.joints_3d_m),
        )
        second = retargeter.retarget(
            shifted,
            target_timestamp_ns=shifted.timestamp_ns + 1_000_000,
        )
        delta = sum((second.position_m[i] - first.position_m[i]) ** 2 for i in range(3)) ** 0.5
        self.assertTrue(second.rate_limited)
        self.assertLessEqual(delta, self.config.max_ee_linear_velocity_m_s * 0.1 + 1e-12)

    def test_rejects_mismatched_config_lengths(self) -> None:
        payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        payload["finger_joint_names"] = ["only_one"]
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bad.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_retargeting_config(path)


if __name__ == "__main__":
    unittest.main()
