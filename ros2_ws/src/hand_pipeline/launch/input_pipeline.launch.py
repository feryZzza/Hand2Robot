from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def mode_is(expected: str) -> IfCondition:
    return IfCondition(
        PythonExpression(["'", LaunchConfiguration("input_mode"), "' == '", expected, "'"])
    )


def generate_launch_description() -> LaunchDescription:
    package_share = FindPackageShare("hand_pipeline")
    config = PathJoinSubstitution([package_share, "config", "input_pipeline.yaml"])
    default_sequence = PathJoinSubstitution(
        [package_share, "examples", "recorded_hand_static_v0.1.json"]
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "input_mode",
                default_value="synthetic",
                description="Input adapter: synthetic or recorded",
                choices=["synthetic", "recorded"],
            ),
            DeclareLaunchArgument(
                "sequence_path",
                default_value=default_sequence,
                description="Recorded JSON path used when input_mode=recorded",
            ),
            Node(
                package="hand_pipeline",
                executable="synthetic_hand_publisher",
                name="synthetic_hand_publisher",
                parameters=[config],
                condition=mode_is("synthetic"),
                output="screen",
            ),
            Node(
                package="hand_pipeline",
                executable="recorded_sequence_player",
                name="recorded_sequence_player",
                parameters=[
                    config,
                    {"sequence_path": LaunchConfiguration("sequence_path")},
                ],
                condition=mode_is("recorded"),
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
