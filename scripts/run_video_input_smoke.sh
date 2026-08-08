#!/usr/bin/env bash

set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
workspace_setup="$project_root/ros2_ws/install/setup.bash"
smoke_root="$project_root/local_data/tmp/video_input_smoke"

if [ ! -f "$workspace_setup" ]; then
  printf 'ERROR: ROS2 workspace is not built; run make build-ros first.\n'
  exit 1
fi
if ! command -v ffmpeg >/dev/null 2>&1; then
  printf 'ERROR: ffmpeg is required to generate the temporary smoke video.\n'
  exit 1
fi

mkdir -p "$smoke_root"
run_dir="$(mktemp -d "$smoke_root/run.XXXXXX")"
video_path="$run_dir/input.mp4"
launch_log="$run_dir/launch.log"

ffmpeg -hide_banner -loglevel error \
  -f lavfi -i "testsrc=size=160x120:rate=10" \
  -frames:v 8 -c:v mpeg4 -pix_fmt yuv420p "$video_path"

set +u
source /opt/ros/humble/setup.bash
source "$workspace_setup"
set -u

export ROS_DOMAIN_ID="${HAND2ROBOT_ROS_DOMAIN_ID:-79}"
export ROS_LOCALHOST_ONLY=1
export ROS_LOG_DIR="$run_dir/ros_logs"
mkdir -p "$ROS_LOG_DIR"

setsid ros2 launch hand_pipeline visual_input.launch.py \
  visual_input_mode:=video \
  video_path:="$video_path" \
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
  fi
  wait "$launch_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

set +e
ros2 run hand_pipeline visual_input_smoke_check --ros-args \
  -p expected_frames:=5 \
  -p expected_width:=160 \
  -p expected_height:=120 \
  -p timeout_s:=8.0
smoke_status=$?
set -e

if [ "$smoke_status" -ne 0 ]; then
  printf 'ROS2 visual-input launch log:\n'
  tail -n 100 "$launch_log"
  exit "$smoke_status"
fi

printf 'Video-input smoke passed. Artifacts: %s\n' "$run_dir"
