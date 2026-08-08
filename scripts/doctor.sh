#!/usr/bin/env bash

set -u

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
hard_fail=0

gib_free() {
  df -Pk "$1" | awk 'NR == 2 { printf "%.1f", $4 / 1024 / 1024 }'
}

root_free="$(gib_free /)"
home_free="$(gib_free /home)"

printf 'Hand2Robot local doctor\n'
printf 'workspace: %s\n' "$project_root"
printf '/ free: %s GiB\n' "$root_free"
printf '/home free: %s GiB\n' "$home_free"
printf 'workspace size: '
du -sh "$project_root" | awk '{print $1}'

if awk "BEGIN { exit !($root_free < 3) }"; then
  printf 'ERROR: / has less than 3 GiB free; stop local project work.\n'
  hard_fail=1
elif awk "BEGIN { exit !($root_free < 6) }"; then
  printf 'WARN: / is below 6 GiB; do not install or download large dependencies.\n'
fi

if awk "BEGIN { exit !($home_free < 15) }"; then
  printf 'ERROR: /home has less than 15 GiB free; archive local data first.\n'
  hard_fail=1
fi

for command_name in git python3 ros2 colcon rsync ffmpeg; do
  if command -v "$command_name" >/dev/null 2>&1; then
    printf '%-8s OK (%s)\n' "$command_name" "$(command -v "$command_name")"
  else
    printf '%-8s MISSING\n' "$command_name"
    case "$command_name" in
      git|python3|ros2|colcon) hard_fail=1 ;;
    esac
  fi
done

if python3 -c 'import cv2; from cv_bridge import CvBridge; from sensor_msgs.msg import Image' \
  >/dev/null 2>&1; then
  printf 'visual input Python dependencies: OK\n'
else
  printf 'INFO: cv2, cv_bridge, or sensor_msgs Python support is missing; camera/video input is unavailable.\n'
fi

printf 'ROS_DISTRO: %s\n' "${ROS_DISTRO:-not sourced}"

if git -C "$project_root" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  printf 'git branch: %s\n' "$(git -C "$project_root" branch --show-current)"
  git -C "$project_root" status --short --branch
else
  printf 'ERROR: workspace is not a Git repository.\n'
  hard_fail=1
fi

camera_count="$(find /dev -maxdepth 1 -name 'video*' -print 2>/dev/null | wc -l)"
printf 'camera devices: %s\n' "$camera_count"
if [ "$camera_count" -eq 0 ]; then
  printf 'INFO: no camera detected; video-file, recorded, or synthetic input remains available.\n'
fi

exit "$hard_fail"
