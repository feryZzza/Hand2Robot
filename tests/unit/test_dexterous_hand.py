from dataclasses import replace
import json
from math import pi
from pathlib import Path
import tempfile
import unittest

from hand2robot_core.dexterous_hand import (
    DEFAULT_ABDUCTION_SPAN_RAD,
    DEFAULT_FLEXION_SPAN_RAD,
    DexterousHandMapping,
    finger_angles,
    load_hand_mapping,
)
from hand2robot_core.palm import build_palm_frame, normalize_hand
from hand2robot_core.recorded_sequence import HANDEDNESS_BY_NAME, load_recorded_sequence


HANDEDNESS_NAME = {value: name for name, value in HANDEDNESS_BY_NAME.items()}


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = PROJECT_ROOT / "configs/assets/panda_allegro_v0.1.json"
SEQUENCE_PATH = PROJECT_ROOT / "ros2_ws/src/hand_pipeline/examples/recorded_hand_static_v0.1.json"


class HandMappingLoadTest(unittest.TestCase):
    def test_manifest_yields_sixteen_ordered_joints(self) -> None:
        mapping = load_hand_mapping(MANIFEST_PATH)
        self.assertEqual(len(mapping.joint_names), 16)
        self.assertEqual(len(set(mapping.joint_names)), 16)
        self.assertEqual(mapping.finger_order, ("index", "middle", "little", "thumb"))
        # Joint order must follow finger groups, so index i//4 identifies the finger.
        self.assertEqual(mapping.joint_names[:4], ("joint_0_0", "joint_1_0", "joint_2_0", "joint_3_0"))
        self.assertEqual(mapping.joint_names[12:], ("joint_12_0", "joint_13_0", "joint_14_0", "joint_15_0"))

    def test_limits_follow_the_joint_reordering(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text())
        hand = manifest["hand"]
        declared = dict(zip(hand["joint_names"], hand["joint_position_min_rad"]))
        mapping = load_hand_mapping(MANIFEST_PATH)
        for name, lower in zip(mapping.joint_names, mapping.position_min_rad):
            self.assertAlmostEqual(lower, declared[name], places=9)

    def test_unsupported_schema_version_is_rejected(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text())
        manifest["schema_version"] = "1.0.0"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                load_hand_mapping(path)

    def test_missing_finger_group_is_rejected(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text())
        del manifest["hand"]["finger_groups"]["thumb"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                load_hand_mapping(path)


class NeutralPoseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.mapping = load_hand_mapping(MANIFEST_PATH)

    def test_neutral_pose_is_inside_every_limit(self) -> None:
        neutral = self.mapping.neutral_positions_rad()
        self.assertEqual(len(neutral), 16)
        for name, value, lower, upper in zip(
            self.mapping.joint_names,
            neutral,
            self.mapping.position_min_rad,
            self.mapping.position_max_rad,
        ):
            self.assertGreaterEqual(value, lower, name)
            self.assertLessEqual(value, upper, name)

    def test_thumb_rotation_neutral_is_not_zero(self) -> None:
        # joint_12_0 has a strictly positive lower bound, so zero is out of range.
        index = self.mapping.joint_index("joint_12_0")
        self.assertGreater(self.mapping.position_min_rad[index], 0.0)
        self.assertGreater(self.mapping.neutral_positions_rad()[index], 0.0)


class FingerAngleTest(unittest.TestCase):
    def setUp(self) -> None:
        observation = load_recorded_sequence(SEQUENCE_PATH).observation_at(0)
        self.points = observation.joints_3d_m
        self.frame = build_palm_frame(
            self.points, handedness=HANDEDNESS_NAME[observation.handedness], minimum_palm_width_m=0.02
        )

    def test_flexion_is_bounded_and_finite(self) -> None:
        for finger in ("thumb", "index", "middle", "ring", "little"):
            angles = finger_angles(self.points, self.frame, finger)
            self.assertEqual(len(angles.flexion_rad), 3)
            for value in angles.flexion_rad:
                self.assertGreaterEqual(value, 0.0)
                self.assertLessEqual(value, pi)
            self.assertGreaterEqual(angles.abduction_rad, -pi)
            self.assertLessEqual(angles.abduction_rad, pi)

    def test_unknown_finger_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            finger_angles(self.points, self.frame, "pinky")

    def test_wrong_point_count_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            finger_angles(self.points[:20], self.frame, "index")

    def test_degenerate_segment_is_rejected(self) -> None:
        collapsed = list(self.points)
        collapsed[6] = collapsed[5]
        with self.assertRaises(ValueError):
            finger_angles(tuple(collapsed), self.frame, "index")


class MappingFromHumanTest(unittest.TestCase):
    def setUp(self) -> None:
        self.mapping = load_hand_mapping(MANIFEST_PATH)
        observation = load_recorded_sequence(SEQUENCE_PATH).observation_at(0)
        self.frame = build_palm_frame(
            observation.joints_3d_m,
            handedness=HANDEDNESS_NAME[observation.handedness],
            minimum_palm_width_m=0.02,
        )
        self.points = normalize_hand(
            observation.joints_3d_m,
            handedness=HANDEDNESS_NAME[observation.handedness],
            target_handedness="right",
            minimum_palm_width_m=0.02,
        ).points_at_scale(0.085)

    def test_every_mapped_joint_is_within_its_limits(self) -> None:
        positions = self.mapping.positions_from_human(self.points, self.frame)
        self.assertEqual(len(positions), 16)
        for name, value, lower, upper in zip(
            self.mapping.joint_names,
            positions,
            self.mapping.position_min_rad,
            self.mapping.position_max_rad,
        ):
            self.assertGreaterEqual(value, lower, name)
            self.assertLessEqual(value, upper, name)

    def test_mapping_is_deterministic(self) -> None:
        first = self.mapping.positions_from_human(self.points, self.frame)
        second = self.mapping.positions_from_human(self.points, self.frame)
        self.assertEqual(first, second)

    def test_rotation_joint_keeps_its_neutral_value(self) -> None:
        positions = self.mapping.positions_from_human(self.points, self.frame)
        index = self.mapping.joint_index("joint_12_0")
        self.assertAlmostEqual(
            positions[index], self.mapping.neutral_positions_rad()[index], places=9
        )

    def test_more_flexion_produces_larger_joint_angles(self) -> None:
        # Curling the index finger inward must raise its flexion joints, proving the
        # mapping tracks the human angle rather than returning a constant.
        curled = list(self.points)
        knuckle = curled[5]
        for offset, joint in enumerate((6, 7, 8), start=1):
            # Fold each successive point back toward the palm along the normal.
            curled[joint] = tuple(
                knuckle[axis] + 0.01 * offset * (-self.frame.z_axis[axis])
                for axis in range(3)
            )
        straight_positions = self.mapping.positions_from_human(self.points, self.frame)
        curled_positions = self.mapping.positions_from_human(tuple(curled), self.frame)
        straight_sum = sum(straight_positions[1:4])
        curled_sum = sum(curled_positions[1:4])
        self.assertGreater(curled_sum, straight_sum)


class ClampTest(unittest.TestCase):
    def setUp(self) -> None:
        self.mapping = load_hand_mapping(MANIFEST_PATH)

    def test_in_range_positions_are_unchanged(self) -> None:
        neutral = self.mapping.neutral_positions_rad()
        clamped, touched = self.mapping.clamp(neutral)
        self.assertEqual(clamped, neutral)
        self.assertFalse(touched)

    def test_out_of_range_positions_are_clamped_and_reported(self) -> None:
        over = tuple(upper + 1.0 for upper in self.mapping.position_max_rad)
        clamped, touched = self.mapping.clamp(over)
        self.assertTrue(touched)
        self.assertEqual(clamped, self.mapping.position_max_rad)

    def test_non_finite_position_is_rejected(self) -> None:
        values = list(self.mapping.neutral_positions_rad())
        values[0] = float("nan")
        with self.assertRaises(ValueError):
            self.mapping.clamp(values)

    def test_wrong_length_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.mapping.clamp((0.0, 0.0))


class MappingValidationTest(unittest.TestCase):
    def base(self) -> DexterousHandMapping:
        return load_hand_mapping(MANIFEST_PATH)

    def test_non_increasing_limits_are_rejected(self) -> None:
        mapping = self.base()
        bad_max = list(mapping.position_max_rad)
        bad_max[0] = mapping.position_min_rad[0]
        with self.assertRaises(ValueError):
            replace(mapping, position_max_rad=tuple(bad_max))

    def test_duplicate_joint_names_are_rejected(self) -> None:
        mapping = self.base()
        names = list(mapping.joint_names)
        names[1] = names[0]
        with self.assertRaises(ValueError):
            replace(mapping, joint_names=tuple(names))

    def test_non_increasing_span_is_rejected(self) -> None:
        mapping = self.base()
        with self.assertRaises(ValueError):
            replace(mapping, flexion_span_rad=(1.0, 1.0))

    def test_unknown_rotation_joint_is_rejected(self) -> None:
        mapping = self.base()
        with self.assertRaises(ValueError):
            replace(mapping, rotation_joint_names=("not_a_joint",))

    def test_default_spans_are_increasing(self) -> None:
        self.assertLess(DEFAULT_FLEXION_SPAN_RAD[0], DEFAULT_FLEXION_SPAN_RAD[1])
        self.assertLess(DEFAULT_ABDUCTION_SPAN_RAD[0], DEFAULT_ABDUCTION_SPAN_RAD[1])


if __name__ == "__main__":
    unittest.main()
