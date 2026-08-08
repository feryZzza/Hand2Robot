from pathlib import Path
import unittest

from hand2robot_core.calibration import load_calibration
from hand2robot_core.episode import EpisodeAligner, episode_record_to_dict
from hand2robot_core.recorded_sequence import load_recorded_sequence
from hand2robot_core.retargeting import SafeRetargeter, load_retargeting_config


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def fixture_pair(sequence_index=0):
    sequence = load_recorded_sequence(
        PROJECT_ROOT / "ros2_ws/src/hand_pipeline/examples/recorded_hand_static_v0.1.json"
    )
    observation = sequence.observation_at(sequence_index)
    retargeter = SafeRetargeter(
        load_calibration(PROJECT_ROOT / "configs/calibration/synthetic_camera_to_robot_v0.1.json"),
        load_retargeting_config(PROJECT_ROOT / "configs/retargeting/cpu_prototype_v0.1.json"),
    )
    action = retargeter.retarget(
        observation,
        target_timestamp_ns=observation.timestamp_ns + 1_000_000,
    )
    return observation, action


class EpisodeAlignerTest(unittest.TestCase):
    def test_pairs_action_first_and_preserves_timestamps(self) -> None:
        observation, action = fixture_pair()
        aligner = EpisodeAligner(episode_id="episode-001", task="follow_hand")
        self.assertIsNone(aligner.add_action(action, record_timestamp_ns=2))
        record = aligner.add_observation(observation, record_timestamp_ns=3)
        self.assertIsNotNone(record)
        self.assertEqual(record.observation_timestamp_ns, observation.timestamp_ns)
        self.assertEqual(record.action_timestamp_ns, action.timestamp_ns)
        self.assertFalse(record.observation_missing)
        self.assertFalse(record.action_missing)
        self.assertFalse(record.episode_complete)

    def test_marks_expected_final_step_complete(self) -> None:
        observation, action = fixture_pair()
        aligner = EpisodeAligner(
            episode_id="episode-001", task="follow_hand", expected_steps=1
        )
        aligner.add_observation(observation, record_timestamp_ns=2)
        record = aligner.add_action(action, record_timestamp_ns=3)
        self.assertTrue(record.episode_complete)
        self.assertTrue(record.success)
        self.assertTrue(aligner.complete)

    def test_flush_keeps_missing_masks_explicit(self) -> None:
        observation, _ = fixture_pair()
        aligner = EpisodeAligner(episode_id="episode-001", task="follow_hand")
        aligner.add_observation(observation, record_timestamp_ns=2)
        records = aligner.flush_missing(record_timestamp_ns=4)
        self.assertEqual(len(records), 1)
        self.assertFalse(records[0].observation_missing)
        self.assertTrue(records[0].action_missing)
        self.assertEqual(records[0].action_timestamp_ns, 0)
        self.assertEqual(records[0].failure_reason, "unaligned_at_flush")

    def test_rejects_duplicate_sequence(self) -> None:
        observation, _ = fixture_pair()
        aligner = EpisodeAligner(episode_id="episode-001", task="follow_hand")
        aligner.add_observation(observation, record_timestamp_ns=2)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            aligner.add_observation(observation, record_timestamp_ns=3)

    def test_json_representation_keeps_full_pair_and_status(self) -> None:
        observation, action = fixture_pair()
        aligner = EpisodeAligner(
            episode_id="episode-001", task="follow_hand", expected_steps=1
        )
        aligner.add_observation(observation, record_timestamp_ns=2)
        payload = episode_record_to_dict(
            aligner.add_action(action, record_timestamp_ns=3)
        )
        self.assertEqual(payload["observation"]["sequence"], 0)
        self.assertEqual(len(payload["observation"]["joints_3d_m"]), 21)
        self.assertEqual(payload["action"]["status_code"], 0)
        self.assertEqual(len(payload["action"]["finger_joint_names"]), 5)
        self.assertTrue(payload["episode_complete"])


if __name__ == "__main__":
    unittest.main()
