#!/usr/bin/env bash

# Source this file before any ROS2 or colcon work on the GPU server.
#
# ROS2 Humble is built against the Ubuntu 22.04 system Python 3.10 ABI. The
# Miniconda base environment puts its own python3 ahead of /usr/bin on PATH,
# which hides cv2, cv_bridge and the rclpy extension modules from ROS2. This
# file puts the system interpreter first and leaves the Conda environments for
# reconstruction, policy and Isaac Sim work untouched.
#
# Measured server values live in docs/server_environment.md.

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  echo "Usage: source $0" >&2
  exit 2
fi

HAND2ROBOT_PROJECT_ROOT="${HAND2ROBOT_PROJECT_ROOT:-/root/autodl-tmp/embodied}"
export HAND2ROBOT_PROJECT_ROOT

export PATH="/usr/bin:$PATH"
export TMPDIR="$HAND2ROBOT_PROJECT_ROOT/cache/tmp"

ros_setup="${ROS_SETUP:-/opt/ros/humble/setup.bash}"
if [ ! -r "$ros_setup" ]; then
  echo "ERROR: ROS2 setup not readable at $ros_setup" >&2
  return 1
fi
# shellcheck disable=SC1090
source "$ros_setup"

# Host-local DDS only. Never expose raw ROS2 DDS to the public network.
export ROS_LOCALHOST_ONLY=1
export HAND2ROBOT_ROS_DOMAIN_ID="${HAND2ROBOT_ROS_DOMAIN_ID:-72}"
export ROS_DOMAIN_ID="$HAND2ROBOT_ROS_DOMAIN_ID"

# Resolve through symlinks so a data-disk entry point still finds the workspace.
script_path="$(readlink -f "${BASH_SOURCE[0]}")"
workspace_setup="$(cd "$(dirname "$script_path")/.." && pwd)/ros2_ws/install/setup.bash"
if [ -r "$workspace_setup" ]; then
  # shellcheck disable=SC1090
  source "$workspace_setup"
fi
