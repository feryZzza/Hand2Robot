.PHONY: build-ros doctor git-status smoke-bag smoke-local smoke-prototype smoke-prototype-recorded smoke-prototype-watchdog smoke-recorded test-contract test-unit

ROS_SETUP ?= /opt/ros/humble/setup.bash

build-ros:
	@bash -c 'source "$(ROS_SETUP)" && cd ros2_ws && colcon build --symlink-install'

doctor:
	@./scripts/doctor.sh

git-status:
	@git status --short --branch

smoke-local: build-ros
	@./scripts/run_local_smoke.sh

smoke-recorded: build-ros
	@./scripts/run_recorded_smoke.sh

smoke-bag: build-ros
	@./scripts/run_bag_replay_check.sh

smoke-prototype: build-ros
	@./scripts/run_prototype_smoke.sh

smoke-prototype-recorded: build-ros
	@./scripts/run_prototype_recorded_smoke.sh

smoke-prototype-watchdog: build-ros
	@./scripts/run_prototype_watchdog_smoke.sh

test-contract:
	@python3 -m unittest discover -s tests/unit -p 'test_contract_definition.py' -v

test-unit:
	@PYTHONPATH=ros2_ws/src/hand2robot_core \
		python3 -m unittest discover -s tests/unit -p 'test_*.py' -v
