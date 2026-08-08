from launch import LaunchDescription
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import PathJoinSubstitution


def generate_launch_description() -> LaunchDescription:
    config = PathJoinSubstitution(
        [FindPackageShare("hand_pipeline"), "config", "synthetic_smoke.yaml"]
    )
    return LaunchDescription(
        [
            Node(
                package="hand_pipeline",
                executable="synthetic_hand_publisher",
                name="synthetic_hand_publisher",
                parameters=[config],
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
