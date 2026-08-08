"""Run a fresh validator and verify one deterministic raw-bag replay."""

import time

import rclpy
from hand_msgs.msg import HandObservation
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from .observation_validator import ObservationValidatorNode


class BagReplayProbe(Node):
    def __init__(self) -> None:
        super().__init__("bag_replay_probe")
        self.declare_parameter("expected_count", 5)
        self.declare_parameter("expected_source", "recorded_fixture")
        self.declare_parameter("timeout_s", 8.0)
        self._expected_count = int(self.get_parameter("expected_count").value)
        self._expected_source = str(self.get_parameter("expected_source").value)
        self._timeout_s = float(self.get_parameter("timeout_s").value)
        self._started_at = time.monotonic()
        self._sequences: list[int] = []
        self._sources: list[str] = []
        self.done = False
        self.success = False
        self._subscription = self.create_subscription(
            HandObservation,
            "/hand/observation",
            self._on_observation,
            qos_profile_sensor_data,
        )
        self._timer = self.create_timer(0.05, self._check)

    def _on_observation(self, observation: HandObservation) -> None:
        self._sequences.append(observation.sequence)
        self._sources.append(observation.source)

    def _check(self) -> None:
        expected_sequences = list(range(self._expected_count))
        if len(self._sequences) == self._expected_count:
            self.success = (
                self._sequences == expected_sequences
                and set(self._sources) == {self._expected_source}
            )
            self.done = True
            if self.success:
                self.get_logger().info(
                    "bag replay passed: "
                    f"count={len(self._sequences)}, sequences={self._sequences}, "
                    f"source={self._expected_source}"
                )
            else:
                self.get_logger().error(
                    f"bag replay mismatch: sequences={self._sequences}, "
                    f"sources={self._sources}"
                )
            return
        if len(self._sequences) > self._expected_count:
            self.done = True
            self.get_logger().error(f"bag replay emitted duplicates: {self._sequences}")
            return
        if time.monotonic() - self._started_at >= self._timeout_s:
            self.done = True
            self.get_logger().error(
                f"bag replay timed out after receiving {self._sequences}"
            )


def main(args=None) -> int:
    rclpy.init(args=args)
    validator = ObservationValidatorNode()
    probe = BagReplayProbe()
    executor = SingleThreadedExecutor()
    executor.add_node(validator)
    executor.add_node(probe)
    try:
        while rclpy.ok() and not probe.done:
            executor.spin_once(timeout_sec=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        success = probe.success
        executor.remove_node(probe)
        executor.remove_node(validator)
        probe.destroy_node()
        validator.destroy_node()
        executor.shutdown()
        if rclpy.ok():
            rclpy.shutdown()
    return 0 if success else 1
