from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MSG_ROOT = PROJECT_ROOT / "ros2_ws" / "src" / "hand_msgs" / "msg"


def active_lines(path: Path) -> set[str]:
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


class ContractDefinitionTest(unittest.TestCase):
    def test_all_versioned_interfaces_exist(self) -> None:
        for name in (
            "HandObservation.msg",
            "RobotTarget.msg",
            "SystemStatus.msg",
            "EpisodeRecord.msg",
        ):
            self.assertTrue((MSG_ROOT / name).is_file(), name)
            self.assertIn("string schema_version", active_lines(MSG_ROOT / name))

    def test_hand_observation_has_fixed_21_joint_arrays(self) -> None:
        lines = active_lines(MSG_ROOT / "HandObservation.msg")
        expected = {
            "geometry_msgs/Point[21] joints_2d_px",
            "geometry_msgs/Point[21] joints_3d_m",
            "bool[21] joints_3d_valid",
            "float32[21] confidence",
        }
        self.assertTrue(expected.issubset(lines))

    def test_episode_keeps_independent_timestamps_and_missing_masks(self) -> None:
        lines = active_lines(MSG_ROOT / "EpisodeRecord.msg")
        expected = {
            "builtin_interfaces/Time observation_timestamp",
            "builtin_interfaces/Time action_timestamp",
            "bool observation_missing",
            "bool action_missing",
        }
        self.assertTrue(expected.issubset(lines))

    def test_status_marks_latency_measurement_validity(self) -> None:
        lines = active_lines(MSG_ROOT / "SystemStatus.msg")
        self.assertIn("float32 end_to_end_latency_ms", lines)
        self.assertIn("bool end_to_end_latency_valid", lines)

    def test_documented_joint_order_is_complete_and_unique(self) -> None:
        text = (PROJECT_ROOT / "docs" / "interfaces.md").read_text(encoding="utf-8")
        names = (
            "wrist",
            "thumb_cmc",
            "thumb_mcp",
            "thumb_ip",
            "thumb_tip",
            "index_mcp",
            "index_pip",
            "index_dip",
            "index_tip",
            "middle_mcp",
            "middle_pip",
            "middle_dip",
            "middle_tip",
            "ring_mcp",
            "ring_pip",
            "ring_dip",
            "ring_tip",
            "little_mcp",
            "little_pip",
            "little_dip",
            "little_tip",
        )
        self.assertEqual(len(names), len(set(names)))
        for name in names:
            self.assertEqual(text.count(f"`{name}`"), 1, name)

    def test_transform_direction_is_explicit(self) -> None:
        text = (PROJECT_ROOT / "docs" / "frames.md").read_text(encoding="utf-8")
        self.assertIn("p_A = T_A_B * p_B", text)
        self.assertIn("p_robot_base = T_robot_base_camera_optical * p_camera_optical", text)


if __name__ == "__main__":
    unittest.main()
