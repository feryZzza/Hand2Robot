"""Palm-local coordinates and explicit anatomical handedness mapping."""

from dataclasses import dataclass
from math import isfinite, sqrt
from typing import Iterable

from .geometry import Vector3


WRIST = 0
INDEX_MCP = 5
MIDDLE_MCP = 9
LITTLE_MCP = 17
HAND_JOINT_COUNT = 21
SUPPORTED_HANDEDNESS = ("left", "right")


def _vector(values: Iterable[float], label: str) -> Vector3:
    vector = tuple(float(value) for value in values)
    if len(vector) != 3:
        raise ValueError(f"{label} must contain 3 values")
    if not all(isfinite(value) for value in vector):
        raise ValueError(f"{label} must be finite")
    return vector


def _subtract(left: Vector3, right: Vector3) -> Vector3:
    return tuple(left[index] - right[index] for index in range(3))


def _dot(left: Vector3, right: Vector3) -> float:
    return sum(left[index] * right[index] for index in range(3))


def _cross(left: Vector3, right: Vector3) -> Vector3:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def _norm(vector: Vector3) -> float:
    return sqrt(_dot(vector, vector))


def _unit(vector: Vector3, label: str, minimum_norm: float) -> Vector3:
    norm = _norm(vector)
    if norm < minimum_norm:
        raise ValueError(f"{label} is degenerate; norm={norm:.6g}")
    return tuple(value / norm for value in vector)


@dataclass(frozen=True)
class PalmFrame:
    """Right-handed anatomical frame expressed in the observation frame.

    ``x_axis`` points from little MCP toward index MCP, ``y_axis`` points from
    wrist toward middle MCP after orthogonalization, and ``z_axis = x cross y``.
    """

    origin_m: Vector3
    x_axis: Vector3
    y_axis: Vector3
    z_axis: Vector3
    palm_width_m: float
    handedness: str


@dataclass(frozen=True)
class PalmNormalizedHand:
    frame: PalmFrame
    points_palm_widths: tuple[Vector3, ...]
    target_handedness: str
    mapping: str

    def points_at_scale(self, target_palm_width_m: float) -> tuple[Vector3, ...]:
        width = float(target_palm_width_m)
        if not isfinite(width) or width <= 0.0:
            raise ValueError("target_palm_width_m must be finite and positive")
        return tuple(
            tuple(component * width for component in point)
            for point in self.points_palm_widths
        )


def build_palm_frame(
    points_m: Iterable[Iterable[float]],
    *,
    handedness: str,
    minimum_palm_width_m: float = 0.02,
) -> PalmFrame:
    """Build an orthonormal palm basis from the fixed 21-joint contract."""

    points = tuple(_vector(point, "hand point") for point in points_m)
    if len(points) != HAND_JOINT_COUNT:
        raise ValueError(f"points_m must contain {HAND_JOINT_COUNT} points")
    source_handedness = str(handedness).strip().lower()
    if source_handedness not in SUPPORTED_HANDEDNESS:
        raise ValueError("handedness must be left or right")
    minimum_width = float(minimum_palm_width_m)
    if not isfinite(minimum_width) or minimum_width <= 0.0:
        raise ValueError("minimum_palm_width_m must be finite and positive")

    origin = points[WRIST]
    lateral = _subtract(points[INDEX_MCP], points[LITTLE_MCP])
    palm_width = _norm(lateral)
    if palm_width < minimum_width:
        raise ValueError(
            f"palm width {palm_width:.6g} m is below {minimum_width:.6g} m"
        )
    x_axis = _unit(lateral, "palm lateral axis", minimum_width)
    longitudinal = _subtract(points[MIDDLE_MCP], origin)
    z_axis = _unit(_cross(x_axis, longitudinal), "palm normal axis", 1e-6)
    y_axis = _unit(_cross(z_axis, x_axis), "palm longitudinal axis", 1e-6)

    return PalmFrame(
        origin_m=origin,
        x_axis=x_axis,
        y_axis=y_axis,
        z_axis=z_axis,
        palm_width_m=palm_width,
        handedness=source_handedness,
    )


def normalize_hand(
    points_m: Iterable[Iterable[float]],
    *,
    handedness: str,
    target_handedness: str = "right",
    minimum_palm_width_m: float = 0.02,
) -> PalmNormalizedHand:
    """Remove wrist pose and scale while naming any cross-hand mapping.

    The anatomical joint order and palm basis make local coordinates comparable
    between left and right hands. A cross-hand mapping is nevertheless recorded
    explicitly so downstream diagnostics never hide that policy choice.
    """

    points = tuple(_vector(point, "hand point") for point in points_m)
    target = str(target_handedness).strip().lower()
    if target not in SUPPORTED_HANDEDNESS:
        raise ValueError("target_handedness must be left or right")
    frame = build_palm_frame(
        points,
        handedness=handedness,
        minimum_palm_width_m=minimum_palm_width_m,
    )
    local_points = []
    normal_sign = 1.0 if frame.handedness == target else -1.0
    for point in points:
        relative = _subtract(point, frame.origin_m)
        local_points.append(
            (
                _dot(relative, frame.x_axis) / frame.palm_width_m,
                _dot(relative, frame.y_axis) / frame.palm_width_m,
                normal_sign * _dot(relative, frame.z_axis) / frame.palm_width_m,
            )
        )
    mapping = (
        "identity_anatomical"
        if frame.handedness == target
        else f"{frame.handedness}_to_{target}_anatomical"
    )
    return PalmNormalizedHand(
        frame=frame,
        points_palm_widths=tuple(local_points),
        target_handedness=target,
        mapping=mapping,
    )
