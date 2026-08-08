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
        (f"share/{package_name}/launch", glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="fery",
    maintainer_email="3319676168@qq.com",
    description="ROS2 input, validation, and diagnostics nodes for Hand2Robot.",
    license="TODO",
    entry_points={
        "console_scripts": [
            "synthetic_hand_publisher = hand_pipeline.synthetic_publisher:main",
            "hand_observation_validator = hand_pipeline.observation_validator:main",
            "hand_smoke_check = hand_pipeline.smoke_check:main",
            "hand_fault_smoke_check = hand_pipeline.fault_smoke_check:main",
        ],
    },
)
