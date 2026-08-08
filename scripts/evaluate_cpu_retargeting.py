#!/usr/bin/env python3
"""Print deterministic JSON metrics for the dependency-free CPU retargeter."""

import json
from math import sqrt
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "ros2_ws/src/hand2robot_core"))

from hand2robot_core.calibration import load_calibration  # noqa: E402
from hand2robot_core.filtering import OneEuroVectorFilter  # noqa: E402
from hand2robot_core.palm import normalize_hand  # noqa: E402
from hand2robot_core.recorded_sequence import load_recorded_sequence  # noqa: E402
from hand2robot_core.retargeting import SafeRetargeter, load_retargeting_config  # noqa: E402


def rms(values: list[float]) -> float:
    return sqrt(sum(value * value for value in values) / len(values))


def main() -> int:
    calibration = load_calibration(
        PROJECT_ROOT / "configs/calibration/synthetic_camera_to_robot_v0.1.json"
    )
    config = load_retargeting_config(
        PROJECT_ROOT / "configs/retargeting/cpu_prototype_v0.1.json"
    )
    observation = load_recorded_sequence(
        PROJECT_ROOT
        / "ros2_ws/src/hand_pipeline/examples/recorded_hand_static_v0.1.json"
    ).observation_at(0)

    filter_ = OneEuroVectorFilter(
        min_cutoff_hz=config.one_euro_min_cutoff_hz,
        beta=config.one_euro_beta,
        derivative_cutoff_hz=config.one_euro_derivative_cutoff_hz,
    )
    raw = [0.004 if index % 2 else -0.004 for index in range(90)]
    filtered = [
        filter_.update((value, 0.0, 0.0), index * 33_333_333)[0]
        for index, value in enumerate(raw)
    ]

    normalized = normalize_hand(
        observation.joints_3d_m,
        handedness="right",
        target_handedness=config.target_handedness,
        minimum_palm_width_m=config.minimum_palm_width_m,
    )
    retargeter = SafeRetargeter(calibration, config)
    target = retargeter.retarget(
        observation,
        target_timestamp_ns=observation.timestamp_ns + 1_000_000,
        monotonic_timestamp_ns=1_000_000_000,
    )
    stale = retargeter.watchdog_target(
        target_timestamp_ns=observation.timestamp_ns + 600_000_000,
        monotonic_timestamp_ns=1_600_000_000,
    )
    metrics = {
        "schema_version": config.schema_version,
        "input_sequence": observation.sequence,
        "mapping": normalized.mapping,
        "source_palm_width_m": round(normalized.frame.palm_width_m, 9),
        "target_palm_width_m": config.target_palm_width_m,
        "raw_jitter_rms_m": round(rms(raw[10:]), 9),
        "filtered_jitter_rms_m": round(rms(filtered[10:]), 9),
        "jitter_reduction_ratio": round(rms(filtered[10:]) / rms(raw[10:]), 6),
        "target_valid": target.valid,
        "target_status": target.status_code.name,
        "target_position_m": [round(value, 9) for value in target.position_m],
        "finger_joint_count": len(target.finger_joint_names),
        "watchdog_valid": stale.valid if stale else None,
        "watchdog_status": stale.status_code.name if stale else None,
    }
    print(json.dumps(metrics, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
