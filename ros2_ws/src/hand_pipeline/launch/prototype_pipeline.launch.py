from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def mode_is(expected: str) -> IfCondition:
    return IfCondition(
        PythonExpression(["'", LaunchConfiguration("input_mode"), "' == '", expected, "'"])
    )


def generate_launch_description() -> LaunchDescription:
    package_share = FindPackageShare("hand_pipeline")
    input_config = PathJoinSubstitution([package_share, "config", "input_pipeline.yaml"])
    default_sequence = PathJoinSubstitution(
        [package_share, "examples", "recorded_hand_static_v0.1.json"]
    )
    default_calibration = PathJoinSubstitution(
        [
            package_share,
            "config",
            "calibration",
            "synthetic_camera_to_robot_v0.1.json",
        ]
    )
    default_retargeting = PathJoinSubstitution(
        [package_share, "config", "retargeting", "cpu_prototype_v0.1.json"]
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "input_mode",
                default_value="synthetic",
                choices=["synthetic", "recorded"],
            ),
            DeclareLaunchArgument("sequence_path", default_value=default_sequence),
            DeclareLaunchArgument("calibration_path", default_value=default_calibration),
            DeclareLaunchArgument("retargeting_config_path", default_value=default_retargeting),
            DeclareLaunchArgument("maximum_messages", default_value="0"),
            DeclareLaunchArgument("enforce_capture_age", default_value="true"),
            DeclareLaunchArgument("enable_recorder", default_value="true"),
            DeclareLaunchArgument("episode_id", default_value="local-cpu-prototype"),
            DeclareLaunchArgument("episode_task", default_value="follow_hand"),
            DeclareLaunchArgument("expected_steps", default_value="0"),
            DeclareLaunchArgument("episode_output_path", default_value=""),
            Node(
                package="hand_pipeline",
                executable="synthetic_hand_publisher",
                name="synthetic_hand_publisher",
                parameters=[
                    input_config,
                    {
                        "maximum_messages": ParameterValue(
                            LaunchConfiguration("maximum_messages"), value_type=int
                        )
                    },
                ],
                condition=mode_is("synthetic"),
                output="screen",
            ),
            Node(
                package="hand_pipeline",
                executable="recorded_sequence_player",
                name="recorded_sequence_player",
                parameters=[
                    input_config,
                    {"sequence_path": LaunchConfiguration("sequence_path")},
                ],
                condition=mode_is("recorded"),
                output="screen",
            ),
            Node(
                package="hand_pipeline",
                executable="hand_observation_validator",
                name="hand_observation_validator",
                parameters=[input_config],
                output="screen",
            ),
            Node(
                package="hand_pipeline",
                executable="safe_retargeter",
                name="safe_retargeter",
                parameters=[
                    {
                        "calibration_path": LaunchConfiguration("calibration_path"),
                        "retargeting_config_path": LaunchConfiguration(
                            "retargeting_config_path"
                        ),
                        "enforce_capture_age": ParameterValue(
                            LaunchConfiguration("enforce_capture_age"), value_type=bool
                        ),
                    }
                ],
                output="screen",
            ),
            Node(
                package="hand_pipeline",
                executable="episode_recorder",
                name="episode_recorder",
                parameters=[
                    {
                        "episode_id": LaunchConfiguration("episode_id"),
                        "task": LaunchConfiguration("episode_task"),
                        "expected_steps": ParameterValue(
                            LaunchConfiguration("expected_steps"), value_type=int
                        ),
                        "output_path": LaunchConfiguration("episode_output_path"),
                    }
                ],
                condition=IfCondition(LaunchConfiguration("enable_recorder")),
                output="screen",
            ),
        ]
    )
