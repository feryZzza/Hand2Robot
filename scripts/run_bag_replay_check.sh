#!/usr/bin/env bash

set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
workspace_setup="$project_root/ros2_ws/install/setup.bash"
base_log_dir="$project_root/local_data/tmp/bag_replay"

if [ ! -f "$workspace_setup" ]; then
  printf 'ERROR: ROS2 workspace is not built; run make build-ros first.\n'
  exit 1
fi

set +u
source /opt/ros/humble/setup.bash
source "$workspace_setup"
set -u

export ROS_DOMAIN_ID="${HAND2ROBOT_ROS_DOMAIN_ID:-74}"
export ROS_LOCALHOST_ONLY=1
mkdir -p "$base_log_dir"
run_dir="$(mktemp -d "$base_log_dir/run.XXXXXX")"
export ROS_LOG_DIR="$run_dir/ros_logs"
mkdir -p "$ROS_LOG_DIR"

bag_path="$run_dir/recorded_fixture_bag"
record_log="$run_dir/record.log"
capture_log="$run_dir/capture_launch.log"
recorder_pid=""
capture_pid=""

stop_group() {
  local process_pid="$1"
  if [ -z "$process_pid" ] || ! kill -0 "$process_pid" 2>/dev/null; then
    return
  fi
  kill -INT -- "-$process_pid" 2>/dev/null || true
  for _ in $(seq 1 50); do
    kill -0 "$process_pid" 2>/dev/null || break
    sleep 0.1
  done
  if kill -0 "$process_pid" 2>/dev/null; then
    kill -TERM -- "-$process_pid" 2>/dev/null || true
    for _ in $(seq 1 20); do
      kill -0 "$process_pid" 2>/dev/null || break
      sleep 0.1
    done
  fi
  if kill -0 "$process_pid" 2>/dev/null; then
    kill -KILL -- "-$process_pid" 2>/dev/null || true
  fi
  wait "$process_pid" 2>/dev/null || true
}

cleanup() {
  stop_group "$capture_pid"
  stop_group "$recorder_pid"
}
trap cleanup EXIT INT TERM

setsid ros2 bag record \
  --output "$bag_path" \
  --storage sqlite3 \
  --max-cache-size 0 \
  /hand/observation/raw >"$record_log" 2>&1 &
recorder_pid=$!

setsid ros2 launch hand_pipeline recorded_bag_capture.launch.py \
  >"$capture_log" 2>&1 &
capture_pid=$!

ros2 run hand_pipeline recorded_smoke_check --ros-args \
  -p expected_count:=5 \
  -p expected_source:=recorded_fixture \
  -p timeout_s:=8.0

stop_group "$capture_pid"
capture_pid=""
stop_group "$recorder_pid"
recorder_pid=""

bag_info="$run_dir/bag_info.txt"
ros2 bag info "$bag_path" >"$bag_info"
message_count="$(awk '/Messages:/ {print $2; exit}' "$bag_info")"
if [ "$message_count" != "5" ]; then
  printf 'ERROR: expected 5 bag messages, got %s\n' "${message_count:-unknown}"
  sed -n '1,120p' "$bag_info"
  exit 1
fi

replay_once() {
  local replay_name="$1"
  local checker_log="$run_dir/${replay_name}_check.log"
  local player_log="$run_dir/${replay_name}_play.log"

  ros2 run hand_pipeline bag_replay_check --ros-args \
    -p expected_count:=5 \
    -p expected_source:=recorded_fixture \
    -p timeout_s:=8.0 >"$checker_log" 2>&1 &
  local checker_pid=$!

  set +e
  ros2 bag play "$bag_path" \
    --delay 0.5 \
    --disable-keyboard-controls \
    --topics /hand/observation/raw >"$player_log" 2>&1
  local player_status=$?
  wait "$checker_pid"
  local checker_status=$?
  set -e

  sed -n '1,80p' "$checker_log"
  if [ "$player_status" -ne 0 ] || [ "$checker_status" -ne 0 ]; then
    printf 'ERROR: %s failed (player=%s checker=%s)\n' \
      "$replay_name" "$player_status" "$checker_status"
    sed -n '1,120p' "$player_log"
    exit 1
  fi
}

replay_once replay_1
replay_once replay_2

database_file="$(find "$bag_path" -maxdepth 1 -name '*.db3' -type f -print -quit)"
database_sha256="$(sha256sum "$database_file" | awk '{print $1}')"
metadata_sha256="$(sha256sum "$bag_path/metadata.yaml" | awk '{print $1}')"
bag_size_bytes="$(du -sb "$bag_path" | awk '{print $1}')"

printf 'Bag replay check passed.\n'
printf 'run_dir=%s\n' "$run_dir"
printf 'bag_messages=%s\n' "$message_count"
printf 'bag_size_bytes=%s\n' "$bag_size_bytes"
printf 'database_sha256=%s\n' "$database_sha256"
printf 'metadata_sha256=%s\n' "$metadata_sha256"
