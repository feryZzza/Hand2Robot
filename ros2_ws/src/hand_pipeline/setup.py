from glob import glob
from setuptools import find_packages, setup


package_name = "hand_pipeline"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=("test",)),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/config", glob("config/*.yaml")),
        (
            f"share/{package_name}/config/calibration",
            glob("config/calibration/*.json"),
        ),
        (
            f"share/{package_name}/config/retargeting",
            glob("config/retargeting/*.json"),
        ),
        (
            f"share/{package_name}/examples",
            glob("examples/*.json") + glob("examples/*.yaml"),
        ),
        (f"share/{package_name}/launch", glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="fery",
    maintainer_email="3319676168@qq.com",
    description="ROS2 input, validation, safe targeting, and episode nodes for Hand2Robot.",
    license="TODO",
    entry_points={
        "console_scripts": [
            "synthetic_hand_publisher = hand_pipeline.synthetic_publisher:main",
            "hand_observation_validator = hand_pipeline.observation_validator:main",
            "hand_smoke_check = hand_pipeline.smoke_check:main",
            "hand_fault_smoke_check = hand_pipeline.fault_smoke_check:main",
            "recorded_sequence_player = hand_pipeline.recorded_sequence_player:main",
            "recorded_smoke_check = hand_pipeline.recorded_smoke_check:main",
            "bag_replay_check = hand_pipeline.bag_replay_check:main",
            "safe_retargeter = hand_pipeline.safe_retargeter:main",
            "episode_recorder = hand_pipeline.episode_recorder:main",
            "prototype_smoke_check = hand_pipeline.prototype_smoke_check:main",
            "prototype_watchdog_check = hand_pipeline.prototype_watchdog_check:main",
            "visual_input_publisher = hand_pipeline.visual_input_publisher:main",
            "visual_input_smoke_check = hand_pipeline.visual_input_smoke_check:main",
        ],
    },
)
