from math import sqrt
import unittest

from hand2robot_core.filtering import LowPassVectorFilter, OneEuroVectorFilter
from hand2robot_core.palm import build_palm_frame, normalize_hand


RIGHT_HAND = (
    (0.000, 0.060, 0.450),
    (-0.025, 0.030, 0.448), (-0.045, 0.005, 0.446),
    (-0.060, -0.020, 0.444), (-0.072, -0.043, 0.442),
    (-0.025, 0.000, 0.450), (-0.027, -0.040, 0.447),
    (-0.028, -0.072, 0.445), (-0.029, -0.100, 0.443),
    (0.000, -0.005, 0.450), (0.000, -0.050, 0.447),
    (0.000, -0.085, 0.445), (0.000, -0.115, 0.443),
    (0.025, 0.000, 0.450), (0.027, -0.045, 0.447),
    (0.028, -0.078, 0.445), (0.029, -0.106, 0.443),
    (0.047, 0.010, 0.450), (0.052, -0.030, 0.447),
    (0.055, -0.060, 0.445), (0.058, -0.085, 0.443),
)


def mirrored_left(points):
    return tuple((-x, y, z) for x, y, z in points)


def rms(values):
    return sqrt(sum(value * value for value in values) / len(values))


class PalmNormalizationTest(unittest.TestCase):
    def test_frame_is_right_handed_and_orthonormal(self) -> None:
        frame = build_palm_frame(RIGHT_HAND, handedness="right")
        axes = (frame.x_axis, frame.y_axis, frame.z_axis)
        for axis in axes:
            self.assertAlmostEqual(sum(value * value for value in axis), 1.0)
        for first, second in ((0, 1), (0, 2), (1, 2)):
            self.assertAlmostEqual(
                sum(axes[first][index] * axes[second][index] for index in range(3)),
                0.0,
            )

    def test_translation_rotation_independent_scale_normalization(self) -> None:
        base = normalize_hand(RIGHT_HAND, handedness="right")
        transformed = tuple(
            (1.0 - 2.0 * y, -0.5 + 2.0 * x, 0.2 + 2.0 * z)
            for x, y, z in RIGHT_HAND
        )
        changed = normalize_hand(transformed, handedness="right")
        for base_point, changed_point in zip(
            base.points_palm_widths, changed.points_palm_widths
        ):
            for base_value, changed_value in zip(base_point, changed_point):
                self.assertAlmostEqual(base_value, changed_value, places=9)

    def test_left_to_right_mapping_is_explicit_and_anatomically_equal(self) -> None:
        right = normalize_hand(RIGHT_HAND, handedness="right")
        left = normalize_hand(
            mirrored_left(RIGHT_HAND),
            handedness="left",
            target_handedness="right",
        )
        self.assertEqual(right.mapping, "identity_anatomical")
        self.assertEqual(left.mapping, "left_to_right_anatomical")
        for right_point, left_point in zip(
            right.points_palm_widths, left.points_palm_widths
        ):
            for right_value, left_value in zip(right_point, left_point):
                self.assertAlmostEqual(right_value, left_value, places=9)

    def test_rejects_degenerate_palm(self) -> None:
        points = list(RIGHT_HAND)
        points[17] = points[5]
        with self.assertRaisesRegex(ValueError, "palm width"):
            normalize_hand(points, handedness="right")


class TimestampFilterTest(unittest.TestCase):
    def test_low_pass_reduces_deterministic_alternating_jitter(self) -> None:
        filter_ = LowPassVectorFilter(cutoff_hz=2.0)
        raw = [0.01 if index % 2 else -0.01 for index in range(60)]
        filtered = [
            filter_.update((value, 0.0, 0.0), index * 33_333_333)[0]
            for index, value in enumerate(raw)
        ]
        self.assertLess(rms(filtered[10:]), rms(raw[10:]) * 0.35)

    def test_one_euro_reduces_jitter_and_tracks_step(self) -> None:
        filter_ = OneEuroVectorFilter(
            min_cutoff_hz=1.0,
            beta=5.0,
            derivative_cutoff_hz=1.0,
        )
        raw = []
        filtered = []
        for index in range(90):
            base = 0.0 if index < 45 else 0.1
            value = base + (0.004 if index % 2 else -0.004)
            raw.append(value)
            filtered.append(
                filter_.update((value, 0.0, 0.0), index * 33_333_333)[0]
            )
        self.assertLess(rms(filtered[10:40]), rms(raw[10:40]) * 0.55)
        self.assertGreater(filtered[50], 0.07)

    def test_rejects_non_monotonic_timestamp(self) -> None:
        filter_ = OneEuroVectorFilter()
        filter_.update((0.0, 0.0, 0.0), 10)
        with self.assertRaisesRegex(ValueError, "strictly"):
            filter_.update((1.0, 0.0, 0.0), 10)

    def test_reset_accepts_new_timestamp_domain(self) -> None:
        filter_ = LowPassVectorFilter(cutoff_hz=2.0)
        filter_.update((0.0, 0.0, 0.0), 100)
        filter_.reset()
        self.assertEqual(filter_.update((1.0, 2.0, 3.0), 1), (1.0, 2.0, 3.0))


if __name__ == "__main__":
    unittest.main()
