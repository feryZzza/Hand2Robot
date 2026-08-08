"""ROS-independent configuration rules for camera and video frame input."""

from dataclasses import dataclass
import math
from pathlib import Path


VISUAL_INPUT_MODES = ("camera", "video")


@dataclass(frozen=True)
class VisualInputSettings:
    """Validated settings shared by the ROS frame-source adapter and unit tests."""

    mode: str
    camera_device: int = 0
    video_path: str = ""
    loop_video: bool = False
    playback_rate: float = 1.0
    fallback_frequency_hz: float = 30.0

    def __post_init__(self) -> None:
        normalized_mode = self.mode.strip().lower()
        object.__setattr__(self, "mode", normalized_mode)
        if normalized_mode not in VISUAL_INPUT_MODES:
            raise ValueError(
                f"input_mode must be one of {VISUAL_INPUT_MODES}, got {self.mode!r}"
            )
        if self.camera_device < 0:
            raise ValueError("camera_device must be non-negative")
        if not math.isfinite(self.playback_rate) or self.playback_rate <= 0.0:
            raise ValueError("playback_rate must be finite and positive")
        if (
            not math.isfinite(self.fallback_frequency_hz)
            or self.fallback_frequency_hz <= 0.0
        ):
            raise ValueError("fallback_frequency_hz must be finite and positive")
        if normalized_mode == "video":
            path = Path(self.video_path).expanduser()
            if not self.video_path.strip():
                raise ValueError("video_path must be provided when input_mode=video")
            if not path.is_file():
                raise ValueError(f"video_path is not a readable file: {path}")
            object.__setattr__(self, "video_path", str(path.resolve()))
        elif self.loop_video:
            raise ValueError("loop_video is only valid when input_mode=video")

    @property
    def capture_source(self) -> int | str:
        """Return the value expected by OpenCV's ``VideoCapture`` constructor."""

        if self.mode == "camera":
            return self.camera_device
        return self.video_path

    @property
    def source_label(self) -> str:
        if self.mode == "camera":
            return f"camera:{self.camera_device}"
        return f"video:{self.video_path}"

    def output_frequency_hz(self, native_frequency_hz: float) -> float:
        """Choose a safe publication rate, scaling file playback only."""

        if math.isfinite(native_frequency_hz) and native_frequency_hz > 0.0:
            base_frequency_hz = native_frequency_hz
        else:
            base_frequency_hz = self.fallback_frequency_hz
        if self.mode == "video":
            return base_frequency_hz * self.playback_rate
        return base_frequency_hz
