"""Small dependency-free SE(3) primitives with explicit frame direction."""

from dataclasses import dataclass
from math import isfinite, sqrt
from typing import Iterable


Vector3 = tuple[float, float, float]
QuaternionXyzw = tuple[float, float, float, float]


def _finite_tuple(values: Iterable[float], expected_length: int, label: str) -> tuple[float, ...]:
    converted = tuple(float(value) for value in values)
    if len(converted) != expected_length:
        raise ValueError(f"{label} must contain {expected_length} values")
    if not all(isfinite(value) for value in converted):
        raise ValueError(f"{label} must be finite")
    return converted


def quaternion_norm(quaternion: QuaternionXyzw) -> float:
    return sqrt(sum(value * value for value in quaternion))


def quaternion_conjugate(quaternion: QuaternionXyzw) -> QuaternionXyzw:
    x, y, z, w = quaternion
    return (-x, -y, -z, w)


def quaternion_multiply(
    left: QuaternionXyzw,
    right: QuaternionXyzw,
) -> QuaternionXyzw:
    lx, ly, lz, lw = left
    rx, ry, rz, rw = right
    return (
        lw * rx + lx * rw + ly * rz - lz * ry,
        lw * ry - lx * rz + ly * rw + lz * rx,
        lw * rz + lx * ry - ly * rx + lz * rw,
        lw * rw - lx * rx - ly * ry - lz * rz,
    )


def rotate_vector(quaternion: QuaternionXyzw, vector: Vector3) -> Vector3:
    vector_quaternion = (vector[0], vector[1], vector[2], 0.0)
    rotated = quaternion_multiply(
        quaternion_multiply(quaternion, vector_quaternion),
        quaternion_conjugate(quaternion),
    )
    return (rotated[0], rotated[1], rotated[2])


def quaternion_from_basis(
    x_axis: Vector3,
    y_axis: Vector3,
    z_axis: Vector3,
) -> QuaternionXyzw:
    """Convert an orthonormal right-handed basis (matrix columns) to xyzw."""

    x = _finite_tuple(x_axis, 3, "x_axis")
    y = _finite_tuple(y_axis, 3, "y_axis")
    z = _finite_tuple(z_axis, 3, "z_axis")
    columns = (x, y, z)
    for column in columns:
        if abs(sum(value * value for value in column) - 1.0) > 1e-6:
            raise ValueError("basis axes must be unit length")
    if any(
        abs(sum(columns[a][index] * columns[b][index] for index in range(3)))
        > 1e-6
        for a, b in ((0, 1), (0, 2), (1, 2))
    ):
        raise ValueError("basis axes must be orthogonal")
    handedness = (
        x[0] * (y[1] * z[2] - y[2] * z[1])
        - y[0] * (x[1] * z[2] - x[2] * z[1])
        + z[0] * (x[1] * y[2] - x[2] * y[1])
    )
    if abs(handedness - 1.0) > 1e-6:
        raise ValueError("basis must be right-handed")

    # Matrix rows for a column-basis rotation.
    m00, m01, m02 = x[0], y[0], z[0]
    m10, m11, m12 = x[1], y[1], z[1]
    m20, m21, m22 = x[2], y[2], z[2]
    trace = m00 + m11 + m22
    if trace > 0.0:
        scale = sqrt(trace + 1.0) * 2.0
        quaternion = (
            (m21 - m12) / scale,
            (m02 - m20) / scale,
            (m10 - m01) / scale,
            0.25 * scale,
        )
    elif m00 > m11 and m00 > m22:
        scale = sqrt(1.0 + m00 - m11 - m22) * 2.0
        quaternion = (
            0.25 * scale,
            (m01 + m10) / scale,
            (m02 + m20) / scale,
            (m21 - m12) / scale,
        )
    elif m11 > m22:
        scale = sqrt(1.0 + m11 - m00 - m22) * 2.0
        quaternion = (
            (m01 + m10) / scale,
            0.25 * scale,
            (m12 + m21) / scale,
            (m02 - m20) / scale,
        )
    else:
        scale = sqrt(1.0 + m22 - m00 - m11) * 2.0
        quaternion = (
            (m02 + m20) / scale,
            (m12 + m21) / scale,
            0.25 * scale,
            (m10 - m01) / scale,
        )
    norm = quaternion_norm(quaternion)
    return tuple(value / norm for value in quaternion)


@dataclass(frozen=True)
class RigidTransform:
    """`T_parent_child`: map child-frame points into the parent frame."""

    parent_frame: str
    child_frame: str
    translation_m: Vector3
    quaternion_xyzw: QuaternionXyzw

    def __post_init__(self) -> None:
        parent = self.parent_frame.strip()
        child = self.child_frame.strip()
        if not parent or not child:
            raise ValueError("parent_frame and child_frame must be non-empty")
        translation = _finite_tuple(self.translation_m, 3, "translation_m")
        quaternion = _finite_tuple(self.quaternion_xyzw, 4, "quaternion_xyzw")
        norm = quaternion_norm(quaternion)
        if abs(norm - 1.0) > 1e-6:
            raise ValueError(f"quaternion must be unit length; norm={norm}")
        object.__setattr__(self, "parent_frame", parent)
        object.__setattr__(self, "child_frame", child)
        object.__setattr__(self, "translation_m", translation)
        object.__setattr__(self, "quaternion_xyzw", quaternion)

    @classmethod
    def identity(cls, frame: str) -> "RigidTransform":
        return cls(frame, frame, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0))

    def apply(self, point_child: Vector3) -> Vector3:
        point = _finite_tuple(point_child, 3, "point")
        rotated = rotate_vector(self.quaternion_xyzw, point)
        return tuple(
            rotated[index] + self.translation_m[index] for index in range(3)
        )

    def inverse(self) -> "RigidTransform":
        inverse_quaternion = quaternion_conjugate(self.quaternion_xyzw)
        negative_translation = tuple(-value for value in self.translation_m)
        inverse_translation = rotate_vector(inverse_quaternion, negative_translation)
        return RigidTransform(
            parent_frame=self.child_frame,
            child_frame=self.parent_frame,
            translation_m=inverse_translation,
            quaternion_xyzw=inverse_quaternion,
        )

    def compose(self, child_transform: "RigidTransform") -> "RigidTransform":
        """Return `self * child_transform`, or `T_A_B * T_B_C = T_A_C`."""

        if self.child_frame != child_transform.parent_frame:
            raise ValueError(
                "transform frame mismatch: "
                f"{self.parent_frame}<-{self.child_frame} cannot compose with "
                f"{child_transform.parent_frame}<-{child_transform.child_frame}"
            )
        return RigidTransform(
            parent_frame=self.parent_frame,
            child_frame=child_transform.child_frame,
            translation_m=self.apply(child_transform.translation_m),
            quaternion_xyzw=quaternion_multiply(
                self.quaternion_xyzw,
                child_transform.quaternion_xyzw,
            ),
        )
