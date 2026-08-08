#!/usr/bin/env bash

set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
workspace_setup="$project_root/ros2_ws/install/setup.bash"
artifact_parent="$project_root/local_data/tmp"

if [ ! -f "$workspace_setup" ]; then
  printf 'ERROR: ROS2 workspace is not built; run make build-ros first.\n'
  exit 1
fi

set +u
source /opt/ros/humble/setup.bash
source "$workspace_setup"
set -u

export ROS_DOMAIN_ID="${HAND2ROBOT_ROS_DOMAIN_ID:-76}"
export ROS_LOCALHOST_ONLY=1
mkdir -p "$artifact_parent"
run_dir="$(mktemp -d "$artifact_parent/prototype_watchdog.XXXXXX")"
export ROS_LOG_DIR="$run_dir/ros_logs"
mkdir -p "$ROS_LOG_DIR"
launch_log="$run_dir/launch.log"
check_log="$run_dir/check.log"

setsid ros2 run hand_pipeline prototype_watchdog_check --ros-args \
  -p required_valid:=3 -p timeout_s:=10.0 >"$check_log" 2>&1 &
check_pid=$!
sleep 0.5

setsid ros2 launch hand_pipeline prototype_pipeline.launch.py \
  input_mode:=synthetic maximum_messages:=30 enable_recorder:=false \
  >"$launch_log" 2>&1 &
launch_pid=$!

cleanup() {
  for process_group in "$launch_pid" "$check_pid"; do
    if kill -0 "$process_group" 2>/dev/null; then
      kill -INT -- "-$process_group" 2>/dev/null || true
    fi
  done
  for _ in $(seq 1 30); do
    if ! kill -0 "$launch_pid" 2>/dev/null && ! kill -0 "$check_pid" 2>/dev/null; then
      break
    fi
    sleep 0.1
  done
  for process_group in "$launch_pid" "$check_pid"; do
    if kill -0 "$process_group" 2>/dev/null; then
      kill -TERM -- "-$process_group" 2>/dev/null || true
    fi
  done
  wait "$launch_pid" 2>/dev/null || true
  wait "$check_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

set +e
wait "$check_pid"
check_status=$?
set -e
if [ "$check_status" -ne 0 ]; then
  printf 'Watchdog check log:\n'
  tail -n 100 "$check_log"
  printf 'Watchdog launch log:\n'
  tail -n 120 "$launch_log"
  exit "$check_status"
fi

cleanup
trap - EXIT INT TERM
printf 'CPU prototype watchdog smoke passed. Logs: %s\n' "$run_dir"
