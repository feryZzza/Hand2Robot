#!/usr/bin/env bash

set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
workspace_setup="$project_root/ros2_ws/install/setup.bash"
log_dir="$project_root/local_data/tmp/recorded_smoke"

if [ ! -f "$workspace_setup" ]; then
  printf 'ERROR: ROS2 workspace is not built; run make build-ros first.\n'
  exit 1
fi

set +u
source /opt/ros/humble/setup.bash
source "$workspace_setup"
set -u

export ROS_DOMAIN_ID="${HAND2ROBOT_ROS_DOMAIN_ID:-73}"
export ROS_LOCALHOST_ONLY=1
export ROS_LOG_DIR="$log_dir/ros_logs"
mkdir -p "$log_dir" "$ROS_LOG_DIR"

launch_log="$log_dir/launch.log"
setsid ros2 launch hand_pipeline input_pipeline.launch.py input_mode:=recorded \
  >"$launch_log" 2>&1 &
launch_pid=$!

cleanup() {
  if kill -0 "$launch_pid" 2>/dev/null; then
    kill -INT -- "-$launch_pid" 2>/dev/null || true
    for _ in $(seq 1 30); do
      kill -0 "$launch_pid" 2>/dev/null || break
      sleep 0.1
    done
  fi
  if kill -0 "$launch_pid" 2>/dev/null; then
    kill -TERM -- "-$launch_pid" 2>/dev/null || true
    for _ in $(seq 1 20); do
      kill -0 "$launch_pid" 2>/dev/null || break
      sleep 0.1
    done
  fi
  if kill -0 "$launch_pid" 2>/dev/null; then
    kill -KILL -- "-$launch_pid" 2>/dev/null || true
  fi
  wait "$launch_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

set +e
ros2 run hand_pipeline recorded_smoke_check --ros-args \
  -p expected_count:=5 \
  -p expected_source:=recorded_fixture \
  -p timeout_s:=8.0
smoke_status=$?
set -e

if [ "$smoke_status" -ne 0 ]; then
  printf 'ROS2 launch log:\n'
  tail -n 100 "$launch_log"
  exit "$smoke_status"
fi

printf 'Recorded-sequence smoke passed. Launch log: %s\n' "$launch_log"
