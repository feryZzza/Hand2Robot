from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    config = PathJoinSubstitution(
        [FindPackageShare("hand_pipeline"), "config", "visual_input.yaml"]
    )
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "visual_input_mode",
                default_value="camera",
                choices=["camera", "video"],
                description="Raw visual frame source used by the reconstruction adapter",
            ),
            DeclareLaunchArgument("camera_device", default_value="0"),
            DeclareLaunchArgument("video_path", default_value=""),
            DeclareLaunchArgument("loop_video", default_value="false"),
            DeclareLaunchArgument("playback_rate", default_value="1.0"),
            DeclareLaunchArgument("frame_id", default_value="camera_optical_frame"),
            DeclareLaunchArgument(
                "output_topic", default_value="/visual/input/image_raw"
            ),
            Node(
                package="hand_pipeline",
                executable="visual_input_publisher",
                name="visual_input_publisher",
                parameters=[
                    config,
                    {
                        "input_mode": LaunchConfiguration("visual_input_mode"),
                        "camera_device": ParameterValue(
                            LaunchConfiguration("camera_device"), value_type=int
                        ),
                        "video_path": LaunchConfiguration("video_path"),
                        "loop_video": ParameterValue(
                            LaunchConfiguration("loop_video"), value_type=bool
                        ),
                        "playback_rate": ParameterValue(
                            LaunchConfiguration("playback_rate"), value_type=float
                        ),
                        "frame_id": LaunchConfiguration("frame_id"),
                        "output_topic": LaunchConfiguration("output_topic"),
                    },
                ],
                output="screen",
            ),
        ]
    )
