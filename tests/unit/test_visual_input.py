from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from hand2robot_core.visual_input import VisualInputSettings


class VisualInputSettingsTest(unittest.TestCase):
    def test_camera_mode_resolves_integer_device(self) -> None:
        settings = VisualInputSettings(mode=" CAMERA ", camera_device=2)
        self.assertEqual(settings.mode, "camera")
        self.assertEqual(settings.capture_source, 2)
        self.assertEqual(settings.source_label, "camera:2")

    def test_video_mode_requires_existing_file_and_resolves_path(self) -> None:
        with TemporaryDirectory() as directory:
            video_path = Path(directory) / "input.mp4"
            video_path.touch()
            settings = VisualInputSettings(mode="video", video_path=str(video_path))
        self.assertEqual(settings.capture_source, str(video_path.resolve()))
        self.assertTrue(settings.source_label.startswith("video:"))

    def test_video_mode_rejects_missing_file(self) -> None:
        with self.assertRaisesRegex(ValueError, "not a readable file"):
            VisualInputSettings(mode="video", video_path="missing.mp4")

    def test_mode_specific_options_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "loop_video"):
            VisualInputSettings(mode="camera", loop_video=True)
        with self.assertRaisesRegex(ValueError, "input_mode"):
            VisualInputSettings(mode="network")

    def test_video_rate_scales_native_or_fallback_frequency(self) -> None:
        with TemporaryDirectory() as directory:
            video_path = Path(directory) / "input.mp4"
            video_path.touch()
            settings = VisualInputSettings(
                mode="video",
                video_path=str(video_path),
                playback_rate=0.5,
                fallback_frequency_hz=24.0,
            )
            self.assertEqual(settings.output_frequency_hz(60.0), 30.0)
            self.assertEqual(settings.output_frequency_hz(0.0), 12.0)

    def test_invalid_rates_and_camera_device_are_rejected(self) -> None:
        for kwargs in (
            {"camera_device": -1},
            {"playback_rate": 0.0},
            {"fallback_frequency_hz": float("nan")},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                VisualInputSettings(mode="camera", **kwargs)


if __name__ == "__main__":
    unittest.main()
