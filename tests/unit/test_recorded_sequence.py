import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from hand2robot_core.recorded_sequence import load_recorded_sequence


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = (
    PROJECT_ROOT
    / "ros2_ws"
    / "src"
    / "hand_pipeline"
    / "examples"
    / "recorded_hand_static_v0.1.json"
)


class RecordedSequenceTest(unittest.TestCase):
    def test_committed_fixture_is_stable_and_valid(self) -> None:
        digest = hashlib.sha256(FIXTURE_PATH.read_bytes()).hexdigest()
        self.assertEqual(
            digest,
            "73dac677df09df1ab6d82b78710911025cf8b34d0c4e84bc34f42c185802c725",
        )
        sequence = load_recorded_sequence(FIXTURE_PATH)
        self.assertEqual(len(sequence.poses), 1)
        self.assertEqual(len(sequence.frames), 5)
        self.assertEqual([frame.sequence for frame in sequence.frames], list(range(5)))
        self.assertEqual(sequence.source, "recorded_fixture")

    def test_rejects_non_monotonic_timestamp(self) -> None:
        payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        payload["frames"][2]["capture_timestamp_ns"] = payload["frames"][1][
            "capture_timestamp_ns"
        ]
        with self.assertRaisesRegex(ValueError, "timestamp"):
            self._load_modified(payload)

    def test_rejects_pose_index_out_of_range(self) -> None:
        payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        payload["frames"][0]["pose_index"] = 9
        with self.assertRaisesRegex(ValueError, "pose_index"):
            self._load_modified(payload)

    def test_rejects_session_that_does_not_start_at_zero(self) -> None:
        payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        payload["frames"][0]["sequence"] = 7
        with self.assertRaisesRegex(ValueError, "start at sequence 0"):
            self._load_modified(payload)

    def test_allows_explicitly_invalid_frame_for_fault_replay(self) -> None:
        payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        payload["frames"][3]["valid"] = False
        sequence = self._load_modified(payload)
        self.assertFalse(sequence.frames[3].valid)

    def _load_modified(self, payload):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sequence.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return load_recorded_sequence(path)


if __name__ == "__main__":
    unittest.main()
