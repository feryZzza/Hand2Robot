.PHONY: build-ros doctor git-status test-contract

ROS_SETUP ?= /opt/ros/humble/setup.bash

build-ros:
	@bash -c 'source "$(ROS_SETUP)" && cd ros2_ws && colcon build --symlink-install'

doctor:
	@./scripts/doctor.sh

git-status:
	@git status --short --branch

test-contract:
	@python3 -m unittest discover -s tests/unit -p 'test_contract_definition.py' -v
