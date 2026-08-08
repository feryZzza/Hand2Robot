"""Finite end-to-end assertion for observation, target, status, and episode."""

import time

import rclpy
from hand_msgs.msg import EpisodeRecord, RobotTarget, SystemStatus
from rclpy.node import Node

from .episode_recorder import episode_qos
from .observation_validator import status_qos
from .safe_retargeter import target_qos


class PrototypeSmokeCheck(Node):
    def __init__(self) -> None:
        super().__init__("prototype_smoke_check")
        self.declare_parameter("required_records", 20)
        self.declare_parameter("timeout_s", 10.0)
        self._required_records = int(self.get_parameter("required_records").value)
        self._timeout_s = float(self.get_parameter("timeout_s").value)
        if self._required_records <= 0 or self._timeout_s <= 0.0:
            raise ValueError("required_records and timeout_s must be positive")
        self._targets: dict[int, RobotTarget] = {}
        self._records: list[EpisodeRecord] = []
        self._errors: list[str] = []
        self._running_status = False
        self._started_at = time.monotonic()
        self.done = False
        self.success = False
        self._target_subscription = self.create_subscription(
            RobotTarget, "/robot/target", self._on_target, target_qos()
        )
        self._episode_subscription = self.create_subscription(
            EpisodeRecord, "/episode/record", self._on_record, episode_qos()
        )
        self._status_subscription = self.create_subscription(
            SystemStatus, "/system/status", self._on_status, status_qos()
        )
        self._timer = self.create_timer(0.05, self._check)

    def _on_target(self, target: RobotTarget) -> None:
        if not target.valid or target.status_code != RobotTarget.STATUS_OK:
            self._errors.append(
                f"invalid target {target.sequence} status={target.status_code}"
            )
            return
        if target.header.frame_id != "robot_base":
            self._errors.append(f"wrong target frame {target.header.frame_id}")
        position = target.end_effector_pose.position
        if not (
            0.25 <= position.x <= 0.85
            and -0.40 <= position.y <= 0.40
            and 0.75 <= position.z <= 1.50
        ):
            self._errors.append(f"target {target.sequence} outside workspace")
        lengths = {
            len(target.finger_joint_names),
            len(target.finger_joint_positions_rad),
            len(target.max_finger_velocity_rad_s),
        }
        if lengths != {5}:
            self._errors.append(f"target {target.sequence} finger arrays mismatch")
        self._targets[target.sequence] = target

    def _on_record(self, record: EpisodeRecord) -> None:
        if record.observation_missing or record.action_missing:
            self._errors.append(f"record {record.step_index} has missing data")
        if record.observation.sequence != record.action.sequence:
            self._errors.append(f"record {record.step_index} sequence mismatch")
        if not record.action.valid or record.action.status_code != RobotTarget.STATUS_OK:
            self._errors.append(f"record {record.step_index} contains invalid action")
        if record.step_index != len(self._records):
            self._errors.append(
                f"record step {record.step_index} expected {len(self._records)}"
            )
        self._records.append(record)

    def _on_status(self, status: SystemStatus) -> None:
        self._running_status = self._running_status or status.state == SystemStatus.STATE_RUNNING

    def _check(self) -> None:
        if self._errors:
            self.get_logger().error("; ".join(self._errors))
            self.done = True
            return
        if len(self._records) >= self._required_records:
            final = self._records[self._required_records - 1]
            sequences = [record.observation.sequence for record in self._records[: self._required_records]]
            if (
                len(set(sequences)) == self._required_records
                and len(self._targets) >= self._required_records
                and final.episode_complete
                and final.success
                and self._running_status
            ):
                self.success = True
                self.done = True
                self.get_logger().info(
                    "prototype smoke passed: "
                    f"records={self._required_records}, "
                    f"sequence_range={min(sequences)}..{max(sequences)}, "
                    f"targets={len(self._targets)}"
                )
                return
        if time.monotonic() - self._started_at >= self._timeout_s:
            self.get_logger().error(
                f"prototype smoke timed out: targets={len(self._targets)}, "
                f"records={len(self._records)}, running={self._running_status}, "
                f"final_complete={self._records[-1].episode_complete if self._records else False}, "
                f"final_success={self._records[-1].success if self._records else False}"
            )
            self.done = True


def main(args=None) -> int:
    rclpy.init(args=args)
    node = PrototypeSmokeCheck()
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
