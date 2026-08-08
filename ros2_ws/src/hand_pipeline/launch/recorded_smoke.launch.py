from launch import LaunchDescription
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import PathJoinSubstitution


def generate_launch_description() -> LaunchDescription:
    package_share = FindPackageShare("hand_pipeline")
    config = PathJoinSubstitution([package_share, "config", "recorded_smoke.yaml"])
    sequence_path = PathJoinSubstitution(
        [package_share, "examples", "recorded_hand_static_v0.1.json"]
    )
    return LaunchDescription(
        [
            Node(
                package="hand_pipeline",
                executable="recorded_sequence_player",
                name="recorded_sequence_player",
                parameters=[config, {"sequence_path": sequence_path}],
                output="screen",
            ),
            Node(
                package="hand_pipeline",
                executable="hand_observation_validator",
                name="hand_observation_validator",
                parameters=[config],
                output="screen",
            ),
        ]
    )
