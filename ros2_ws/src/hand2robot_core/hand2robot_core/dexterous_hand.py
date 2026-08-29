"""Fail-closed mapping from a 21-joint human hand to a dexterous hand's joints.

The CPU prototype in `retargeting` collapses each finger to one flexion value,
which ADR-0003 scopes to a test sink. A real dexterous hand such as the Allegro
exposes four joints per finger: one abduction and three flexion stages. This
module produces those per-joint angles from the palm-normalized human points,
using the same fail-closed style as the rest of the core: no ROS dependency,
explicit units, and a raised error rather than a clamped guess when the input
geometry is degenerate.

Mapping decisions, recorded because they are choices rather than derivations:

- Flexion comes from the anatomical joint angle at each of the human finger's
  three internal joints, so the hand's MCP, PIP and DIP stages each track a
  distinct human angle instead of sharing one curl scalar.
- Abduction comes from the signed angle between the finger's proximal segment
  and the palm's forward axis, measured in the palm plane. The sign convention
  follows the palm frame's lateral axis, so a right hand spreading its fingers
  apart produces increasing magnitudes.
- The human hand has no joint corresponding to the Allegro thumb's rotation
  joint, whose range is strictly positive. Its neutral value is the midpoint of
  its own limits, adjusted by thumb opposition, never zero.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import acos, atan2, isfinite, pi
from typing import Iterable, Sequence

from .geometry import Vector3
from .palm import PalmFrame

# Human joint indices from docs/interfaces.md, per finger, ordered from the
# knuckle outward. Each chain gives three internal angles: at MCP, PIP and DIP.
HUMAN_FINGER_CHAINS: dict[str, tuple[int, int, int, int, int]] = {
    "thumb": (0, 1, 2, 3, 4),
    "index": (0, 5, 6, 7, 8),
    "middle": (0, 9, 10, 11, 12),
    "ring": (0, 13, 14, 15, 16),
    "little": (0, 17, 18, 19, 20),
}

MINIMUM_SEGMENT_M = 1e-9
FLEXION_STAGES = 3


@dataclass(frozen=True)
class FingerAngles:
    """Human-derived angles for one finger, in radians."""

    abduction_rad: float
    flexion_rad: tuple[float, float, float]


def _subtract(left: Vector3, right: Vector3) -> Vector3:
    return tuple(left[axis] - right[axis] for axis in range(3))


def _dot(left: Vector3, right: Vector3) -> float:
    return sum(left[axis] * right[axis] for axis in range(3))


def _norm(vector: Vector3) -> float:
    return _dot(vector, vector) ** 0.5


def _unit(vector: Vector3, label: str) -> Vector3:
    magnitude = _norm(vector)
    if magnitude < MINIMUM_SEGMENT_M:
        raise ValueError(f"{label} is degenerate")
    return tuple(component / magnitude for component in vector)


def _interior_bend_rad(points: Sequence[Vector3], a: int, b: int, c: int) -> float:
    """Return the bend away from straight at joint ``b``, in ``[0, pi]``."""

    first = _unit(_subtract(points[a], points[b]), f"segment {a}-{b}")
    second = _unit(_subtract(points[c], points[b]), f"segment {c}-{b}")
    cosine = max(-1.0, min(1.0, _dot(first, second)))
    return pi - acos(cosine)


def finger_angles(
    points: Sequence[Vector3],
    frame: PalmFrame,
    finger: str,
) -> FingerAngles:
    """Return abduction and three flexion angles for one named human finger."""

    if finger not in HUMAN_FINGER_CHAINS:
        raise ValueError(f"unknown finger {finger!r}")
    chain = HUMAN_FINGER_CHAINS[finger]
    if len(points) != 21:
        raise ValueError("a human hand must have exactly 21 points")

    knuckle, proximal = chain[1], chain[2]
    segment = _unit(
        _subtract(points[proximal], points[knuckle]), f"{finger} proximal segment"
    )
    # Project the proximal segment into the palm plane, then measure its signed
    # deviation from the palm's forward axis. The palm normal is discarded here
    # because that component is flexion, already covered below.
    forward = _dot(segment, frame.y_axis)
    lateral = _dot(segment, frame.x_axis)
    abduction = atan2(lateral, forward)

    flexion = tuple(
        _interior_bend_rad(points, chain[index], chain[index + 1], chain[index + 2])
        for index in range(FLEXION_STAGES)
    )
    return FingerAngles(abduction_rad=abduction, flexion_rad=flexion)


def _scale_into(value: float, source_span: tuple[float, float], lower: float, upper: float) -> float:
    """Map ``value`` from ``source_span`` into ``[lower, upper]``, clamping ends."""

    source_low, source_high = source_span
    if not source_high > source_low:
        raise ValueError("source span must be increasing")
    ratio = (value - source_low) / (source_high - source_low)
    ratio = max(0.0, min(1.0, ratio))
    return lower + ratio * (upper - lower)


@dataclass(frozen=True)
class DexterousHandMapping:
    """Per-joint limits and human-angle spans for one dexterous hand."""

    joint_names: tuple[str, ...]
    position_min_rad: tuple[float, ...]
    position_max_rad: tuple[float, ...]
    max_velocity_rad_s: tuple[float, ...]
    finger_order: tuple[str, ...]
    human_finger_for_hand_finger: dict[str, str]
    abduction_span_rad: tuple[float, float]
    flexion_span_rad: tuple[float, float]
    rotation_joint_names: tuple[str, ...]

    def __post_init__(self) -> None:
        count = len(self.joint_names)
        if count == 0:
            raise ValueError("a mapping needs at least one joint")
        for label, values in (
            ("position_min_rad", self.position_min_rad),
            ("position_max_rad", self.position_max_rad),
            ("max_velocity_rad_s", self.max_velocity_rad_s),
        ):
            if len(values) != count or not all(isfinite(value) for value in values):
                raise ValueError(f"{label} must hold {count} finite values")
        for index, (lower, upper) in enumerate(
            zip(self.position_min_rad, self.position_max_rad)
        ):
            if not upper > lower:
                raise ValueError(
                    f"joint {self.joint_names[index]} has a non-increasing limit range"
                )
        if len(set(self.joint_names)) != count:
            raise ValueError("joint names must be unique")
        expected = len(self.finger_order) * 4
        if count != expected:
            raise ValueError(
                f"expected {expected} joints for {len(self.finger_order)} fingers, got {count}"
            )
        for hand_finger in self.finger_order:
            human = self.human_finger_for_hand_finger.get(hand_finger)
            if human not in HUMAN_FINGER_CHAINS:
                raise ValueError(
                    f"hand finger {hand_finger!r} maps to unknown human finger {human!r}"
                )
        for span_label, span in (
            ("abduction_span_rad", self.abduction_span_rad),
            ("flexion_span_rad", self.flexion_span_rad),
        ):
            if len(span) != 2 or not all(isfinite(value) for value in span):
                raise ValueError(f"{span_label} must hold two finite values")
            if not span[1] > span[0]:
                raise ValueError(f"{span_label} must be increasing")
        unknown = set(self.rotation_joint_names) - set(self.joint_names)
        if unknown:
            raise ValueError(f"rotation joints not in this hand: {sorted(unknown)}")

    def joint_index(self, name: str) -> int:
        return self.joint_names.index(name)

    def neutral_positions_rad(self) -> tuple[float, ...]:
        """Return the in-range neutral pose.

        Zero is not a safe default: the Allegro thumb rotation joint has a
        strictly positive lower bound, so a zero command is out of range. Each
        joint falls back to zero only when zero lies inside its own limits.
        """

        neutral = []
        for lower, upper in zip(self.position_min_rad, self.position_max_rad):
            neutral.append(0.0 if lower <= 0.0 <= upper else (lower + upper) / 2.0)
        return tuple(neutral)

    def positions_from_human(
        self,
        points: Sequence[Vector3],
        frame: PalmFrame,
    ) -> tuple[float, ...]:
        """Map palm-normalized human points onto every hand joint, in radians."""

        positions = list(self.neutral_positions_rad())
        for finger_index, hand_finger in enumerate(self.finger_order):
            human_finger = self.human_finger_for_hand_finger[hand_finger]
            angles = finger_angles(points, frame, human_finger)
            base = finger_index * 4
            slots = (
                (base + 0, angles.abduction_rad, self.abduction_span_rad),
                (base + 1, angles.flexion_rad[0], self.flexion_span_rad),
                (base + 2, angles.flexion_rad[1], self.flexion_span_rad),
                (base + 3, angles.flexion_rad[2], self.flexion_span_rad),
            )
            for joint_index, value, span in slots:
                name = self.joint_names[joint_index]
                if name in self.rotation_joint_names:
                    # No human joint corresponds to this one; hold its neutral.
                    continue
                positions[joint_index] = _scale_into(
                    value,
                    span,
                    self.position_min_rad[joint_index],
                    self.position_max_rad[joint_index],
                )
        return tuple(positions)

    def clamp(self, positions: Iterable[float]) -> tuple[tuple[float, ...], bool]:
        """Clamp positions into limits, reporting whether any joint was clamped."""

        values = tuple(float(value) for value in positions)
        if len(values) != len(self.joint_names):
            raise ValueError(
                f"expected {len(self.joint_names)} positions, got {len(values)}"
            )
        if not all(isfinite(value) for value in values):
            raise ValueError("joint positions must all be finite")
        clamped = []
        touched = False
        for value, lower, upper in zip(values, self.position_min_rad, self.position_max_rad):
            bounded = max(lower, min(upper, value))
            touched = touched or bounded != value
            clamped.append(bounded)
        return tuple(clamped), touched


# Human angle spans the mapping scales from. These are the assumed working ranges
# of a human hand, not measured per subject: a finger joint bends from straight to
# roughly a right angle, and abduction stays within about 30 degrees of the palm's
# forward axis. Both are clamped, so an unusual hand saturates rather than
# producing an out-of-limit command.
DEFAULT_FLEXION_SPAN_RAD = (0.0, pi / 2.0)
DEFAULT_ABDUCTION_SPAN_RAD = (-pi / 6.0, pi / 6.0)

# The Allegro's fourth chain is the thumb, and its first joint rotates the whole
# thumb rather than abducting it. No human joint corresponds, so it holds neutral.
ALLEGRO_FINGER_ORDER = ("index", "middle", "little", "thumb")
ALLEGRO_HUMAN_FINGER = {
    "index": "index",
    "middle": "middle",
    "little": "little",
    "thumb": "thumb",
}
ALLEGRO_ROTATION_JOINTS = ("joint_12_0",)


def load_hand_mapping(
    manifest_path,
    *,
    flexion_span_rad: tuple[float, float] = DEFAULT_FLEXION_SPAN_RAD,
    abduction_span_rad: tuple[float, float] = DEFAULT_ABDUCTION_SPAN_RAD,
) -> DexterousHandMapping:
    """Build a mapping from the committed asset manifest's ``hand`` section.

    Limits come from the manifest so they are stated once, in the contract that
    `scripts/audit_sim_assets.py` checks against the simulated articulation.
    """

    import json
    from pathlib import Path

    manifest = json.loads(Path(manifest_path).read_text())
    if manifest.get("schema_version") != "0.1.0":
        raise ValueError(
            f"unsupported manifest schema_version {manifest.get('schema_version')!r}"
        )
    hand = manifest["hand"]
    groups = hand.get("finger_groups") or {}
    names = tuple(hand["joint_names"])

    finger_order = tuple(name for name in ALLEGRO_FINGER_ORDER if name in groups)
    if len(finger_order) != len(ALLEGRO_FINGER_ORDER):
        raise ValueError(
            f"manifest finger_groups {sorted(groups)} do not cover {ALLEGRO_FINGER_ORDER}"
        )
    # The joint order used for mapping is the finger-group order, which need not
    # match the manifest's flat listing. Rebuild both together so an index into
    # one always means the same joint in the other.
    ordered_names: list[str] = []
    for hand_finger in finger_order:
        group = tuple(groups[hand_finger])
        if len(group) != 4:
            raise ValueError(f"finger {hand_finger!r} must list exactly 4 joints")
        ordered_names.extend(group)
    unknown = set(ordered_names) - set(names)
    if unknown:
        raise ValueError(f"finger_groups reference unknown joints: {sorted(unknown)}")

    def reorder(key: str) -> tuple[float, ...]:
        values = list(hand[key])
        if len(values) != len(names):
            raise ValueError(f"{key} must hold {len(names)} values")
        lookup = dict(zip(names, values))
        return tuple(float(lookup[name]) for name in ordered_names)

    return DexterousHandMapping(
        joint_names=tuple(ordered_names),
        position_min_rad=reorder("joint_position_min_rad"),
        position_max_rad=reorder("joint_position_max_rad"),
        max_velocity_rad_s=reorder("joint_max_velocity_rad_s"),
        finger_order=finger_order,
        human_finger_for_hand_finger=dict(ALLEGRO_HUMAN_FINGER),
        abduction_span_rad=abduction_span_rad,
        flexion_span_rad=flexion_span_rad,
        rotation_joint_names=tuple(
            name for name in ALLEGRO_ROTATION_JOINTS if name in ordered_names
        ),
    )
