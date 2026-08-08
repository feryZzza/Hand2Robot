"""Assert that a stopped source causes one fail-closed stale target."""

import time

import rclpy
from hand_msgs.msg import RobotTarget
from rclpy.node import Node

from .safe_retargeter import target_qos


class PrototypeWatchdogCheck(Node):
    def __init__(self) -> None:
        super().__init__("prototype_watchdog_check")
        self.declare_parameter("required_valid", 3)
        self.declare_parameter("timeout_s", 8.0)
        self._required_valid = int(self.get_parameter("required_valid").value)
        self._timeout_s = float(self.get_parameter("timeout_s").value)
        self._valid_sequences: set[int] = set()
        self._stale_count = 0
        self._unexpected_invalid: list[int] = []
        self._started_at = time.monotonic()
        self.done = False
        self.success = False
        self._subscription = self.create_subscription(
            RobotTarget, "/robot/target", self._on_target, target_qos()
        )
        self._timer = self.create_timer(0.05, self._check)

    def _on_target(self, target: RobotTarget) -> None:
        if target.valid:
            self._valid_sequences.add(target.sequence)
        elif target.status_code == RobotTarget.STATUS_STALE_INPUT:
            self._stale_count += 1
        else:
            self._unexpected_invalid.append(target.status_code)

    def _check(self) -> None:
        if self._unexpected_invalid:
            self.get_logger().error(
                f"unexpected invalid statuses {self._unexpected_invalid}"
            )
            self.done = True
            return
        if len(self._valid_sequences) >= self._required_valid and self._stale_count == 1:
            self.success = True
            self.done = True
            self.get_logger().info(
                f"watchdog smoke passed: valid={len(self._valid_sequences)}, "
                f"stale_invalid={self._stale_count}"
            )
            return
        if self._stale_count > 1:
            self.get_logger().error("watchdog published more than one stale invalid target")
            self.done = True
            return
        if time.monotonic() - self._started_at >= self._timeout_s:
            self.get_logger().error(
                f"watchdog smoke timed out: valid={len(self._valid_sequences)}, "
                f"stale_invalid={self._stale_count}"
            )
            self.done = True


def main(args=None) -> int:
    rclpy.init(args=args)
    node = PrototypeWatchdogCheck()
    try:
        while rclpy.ok() and not node.done:
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        success = node.success
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0 if success else 1
