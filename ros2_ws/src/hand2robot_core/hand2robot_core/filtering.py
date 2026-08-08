"""Timestamp-aware dependency-free filters for deterministic retargeting."""

from dataclasses import dataclass
from math import isfinite, pi
from typing import Iterable

from .geometry import Vector3


def _finite_vector(values: Iterable[float]) -> Vector3:
    vector = tuple(float(value) for value in values)
    if len(vector) != 3:
        raise ValueError("value must contain 3 components")
    if not all(isfinite(value) for value in vector):
        raise ValueError("value must be finite")
    return vector


def _validate_cutoff(value: float, label: str) -> float:
    cutoff = float(value)
    if not isfinite(cutoff) or cutoff <= 0.0:
        raise ValueError(f"{label} must be finite and positive")
    return cutoff


def smoothing_alpha(cutoff_hz: float, dt_s: float) -> float:
    cutoff = _validate_cutoff(cutoff_hz, "cutoff_hz")
    dt = float(dt_s)
    if not isfinite(dt) or dt <= 0.0:
        raise ValueError("dt_s must be finite and positive")
    tau = 1.0 / (2.0 * pi * cutoff)
    return 1.0 / (1.0 + tau / dt)


@dataclass
class LowPassVectorFilter:
    cutoff_hz: float
    _last_timestamp_ns: int | None = None
    _last_value: Vector3 | None = None

    def __post_init__(self) -> None:
        self.cutoff_hz = _validate_cutoff(self.cutoff_hz, "cutoff_hz")

    def reset(self) -> None:
        self._last_timestamp_ns = None
        self._last_value = None

    def update(self, value: Iterable[float], timestamp_ns: int) -> Vector3:
        sample = _finite_vector(value)
        timestamp = int(timestamp_ns)
        if timestamp < 0:
            raise ValueError("timestamp_ns must be non-negative")
        if self._last_timestamp_ns is None:
            self._last_timestamp_ns = timestamp
            self._last_value = sample
            return sample
        if timestamp <= self._last_timestamp_ns:
            raise ValueError("timestamp_ns must increase strictly")
        dt_s = (timestamp - self._last_timestamp_ns) / 1_000_000_000.0
        alpha = smoothing_alpha(self.cutoff_hz, dt_s)
        assert self._last_value is not None
        filtered = tuple(
            alpha * sample[index] + (1.0 - alpha) * self._last_value[index]
            for index in range(3)
        )
        self._last_timestamp_ns = timestamp
        self._last_value = filtered
        return filtered


@dataclass
class OneEuroVectorFilter:
    min_cutoff_hz: float = 1.0
    beta: float = 0.05
    derivative_cutoff_hz: float = 1.0
    _last_timestamp_ns: int | None = None
    _last_raw: Vector3 | None = None
    _last_filtered: Vector3 | None = None
    _last_derivative: Vector3 = (0.0, 0.0, 0.0)

    def __post_init__(self) -> None:
        self.min_cutoff_hz = _validate_cutoff(
            self.min_cutoff_hz, "min_cutoff_hz"
        )
        self.derivative_cutoff_hz = _validate_cutoff(
            self.derivative_cutoff_hz, "derivative_cutoff_hz"
        )
        self.beta = float(self.beta)
        if not isfinite(self.beta) or self.beta < 0.0:
            raise ValueError("beta must be finite and non-negative")

    def reset(self) -> None:
        self._last_timestamp_ns = None
        self._last_raw = None
        self._last_filtered = None
        self._last_derivative = (0.0, 0.0, 0.0)

    def update(self, value: Iterable[float], timestamp_ns: int) -> Vector3:
        sample = _finite_vector(value)
        timestamp = int(timestamp_ns)
        if timestamp < 0:
            raise ValueError("timestamp_ns must be non-negative")
        if self._last_timestamp_ns is None:
            self._last_timestamp_ns = timestamp
            self._last_raw = sample
            self._last_filtered = sample
            return sample
        if timestamp <= self._last_timestamp_ns:
            raise ValueError("timestamp_ns must increase strictly")

        dt_s = (timestamp - self._last_timestamp_ns) / 1_000_000_000.0
        assert self._last_raw is not None
        assert self._last_filtered is not None
        raw_derivative = tuple(
            (sample[index] - self._last_raw[index]) / dt_s for index in range(3)
        )
        derivative_alpha = smoothing_alpha(self.derivative_cutoff_hz, dt_s)
        filtered_derivative = tuple(
            derivative_alpha * raw_derivative[index]
            + (1.0 - derivative_alpha) * self._last_derivative[index]
            for index in range(3)
        )
        filtered = []
        for index in range(3):
            cutoff = self.min_cutoff_hz + self.beta * abs(filtered_derivative[index])
            alpha = smoothing_alpha(cutoff, dt_s)
            filtered.append(
                alpha * sample[index]
                + (1.0 - alpha) * self._last_filtered[index]
            )

        result = tuple(filtered)
        self._last_timestamp_ns = timestamp
        self._last_raw = sample
        self._last_filtered = result
        self._last_derivative = filtered_derivative
        return result
