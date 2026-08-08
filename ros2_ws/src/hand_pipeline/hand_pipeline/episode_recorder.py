"""Align, publish, and optionally persist versioned EpisodeRecord messages."""

import json
from pathlib import Path

import rclpy
from hand2robot_core.episode import EpisodeAligner, episode_record_to_dict
from hand_msgs.msg import EpisodeRecord, HandObservation, RobotTarget
from rclpy.node import Node
from rclpy.qos import (
    DurabilityPolicy,
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
    qos_profile_sensor_data,
)

from .conversion import (
    episode_record_to_ros,
    hand_observation_from_ros,
    robot_target_from_ros,
)
from .safe_retargeter import target_qos


def episode_qos() -> QoSProfile:
    return QoSProfile(
        reliability=ReliabilityPolicy.RELIABLE,
        durability=DurabilityPolicy.VOLATILE,
        history=HistoryPolicy.KEEP_LAST,
        depth=10,
    )


class EpisodeRecorderNode(Node):
    def __init__(self) -> None:
        super().__init__("episode_recorder")
        self.declare_parameter("episode_id", "local-cpu-prototype")
        self.declare_parameter("task", "follow_hand")
        self.declare_parameter("expected_steps", 0)
        self.declare_parameter("maximum_pending", 256)
        self.declare_parameter("output_path", "")
        self._aligner = EpisodeAligner(
            episode_id=str(self.get_parameter("episode_id").value),
            task=str(self.get_parameter("task").value),
            expected_steps=int(self.get_parameter("expected_steps").value),
            maximum_pending=int(self.get_parameter("maximum_pending").value),
        )
        output_path = str(self.get_parameter("output_path").value)
        self._output = None
        if output_path:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            self._output = path.open("x", encoding="utf-8")
            self.get_logger().info(f"writing episode JSONL to {path}")
        self._publisher = self.create_publisher(
            EpisodeRecord, "/episode/record", episode_qos()
        )
        self._observation_subscription = self.create_subscription(
            HandObservation,
            "/hand/observation",
            self._on_observation,
            qos_profile_sensor_data,
        )
        self._action_subscription = self.create_subscription(
            RobotTarget,
            "/robot/target",
            self._on_action,
            target_qos(),
        )
        self._closed = False

    def _on_observation(self, message: HandObservation) -> None:
        if self._aligner.complete:
            return
        try:
            record = self._aligner.add_observation(
                hand_observation_from_ros(message),
                record_timestamp_ns=self.get_clock().now().nanoseconds,
            )
        except ValueError as error:
            self.get_logger().error(str(error))
            return
        self._publish_record(record)

    def _on_action(self, message: RobotTarget) -> None:
        if self._aligner.complete:
            return
        try:
            record = self._aligner.add_action(
                robot_target_from_ros(message),
                record_timestamp_ns=self.get_clock().now().nanoseconds,
            )
        except (ValueError, KeyError) as error:
            self.get_logger().error(str(error))
            return
        self._publish_record(record)

    def _publish_record(self, record) -> None:
        if record is None:
            return
        self._publisher.publish(episode_record_to_ros(record))
        if self._output is not None:
            self._output.write(json.dumps(episode_record_to_dict(record), sort_keys=True))
            self._output.write("\n")
            self._output.flush()
        if record.episode_complete:
            self.get_logger().info(
                f"episode {record.episode_id} complete at {record.step_index + 1} steps"
            )

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for record in self._aligner.flush_missing(
            record_timestamp_ns=self.get_clock().now().nanoseconds
        ):
            self._publish_record(record)
        if self._output is not None:
            self._output.close()

    def destroy_node(self):
        self.close()
        return super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = EpisodeRecorderNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
