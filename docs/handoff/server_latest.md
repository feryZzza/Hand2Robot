[English](server_latest.md) | [简体中文](server_latest.zh-CN.md)

# Server handoff

- Updated: 2026-08-29
- Git commit: `9910dbc` at audit time
- Server environment version: measured, see `docs/server_environment.md`
- Input and checksum: none received from the local machine yet

## Completed

The read-only audit ran on the actual RTX 4090 instance and its output is kept
under `/root/autodl-tmp/embodied/artifacts/audit/`. Measured platform, storage,
and layer state are recorded in `docs/server_environment.md`.

Layers L0 through L2 are installed and verified:

- L0: driver 580.105.08, one RTX 4090 with 24564 MiB visible to `nvidia-smi`.
- L1: git, cmake, tmux, ffmpeg, rsync, gcc.
- L2: ROS2 Humble desktop, colcon, rosbag2, tf2, cv_bridge, OpenCV 4.5.4,
  installed against the Ubuntu system Python 3.10.12 ABI.

`scripts/server_ros2_env.sh` is the ROS2 entry point. It is required because
Miniconda's base `python3` precedes `/usr/bin` on `PATH` and hides `cv2`,
`cv_bridge`, and `rclpy` from ROS2. It also pins DDS to `ROS_LOCALHOST_ONLY=1`
on domain 72.

A fourth Conda environment, `h2r-sim` on Python 3.12.14, was added because
Isaac Sim 6.0.1 requires Python 3.12 and cannot share the 3.10 environments
that ROS2 depends on.

## Tests and metrics

Run from `/root/Hand2Robot` after sourcing `scripts/server_ros2_env.sh`:

| Check | Result |
|---|---|
| `scripts/doctor.sh` | exit 0, visual input dependencies OK, 0 cameras |
| `make test-unit` | 66 tests, OK |
| `colcon build --symlink-install` | `hand2robot_core`, `hand_msgs`, `hand_pipeline` finished |
| `make smoke-local` | 16 observations, 15 valid, 0 invalid, 0 drops, 30.0 Hz, 2.62 ms; fault probe 0 valid / 9 invalid with `low_confidence` |
| `make smoke-recorded` | count 5, sequences `[0,1,2,3,4]`, source `recorded_fixture` |
| `make smoke-video-input` | 5 frames, 160x120, `bgr8`, strict timestamps |
| `make smoke-bag` | 5 bag messages, 33853 bytes, two independent replays each `[0,1,2,3,4]` |
| `make smoke-prototype` | 20 records, sequences 0-19, complete and successful |
| `make smoke-prototype-recorded` | 5 records, sequences 0-4 |
| `make smoke-prototype-watchdog` | passed |

All nine repository checks pass on the server with the same results the local
CPU baseline claims. No result is inherited from the local machine.

## Generated artifacts

- `/root/autodl-tmp/embodied/artifacts/audit/server_audit_20260829T134813Z.txt`
- Episode JSONL and smoke logs under the ignored `local_data/` tree.

## Known issues

1. The persistent volume is **50 GB**, not the 300 GB recorded in earlier
   notes. This is the binding constraint for Isaac Sim, datasets, and
   checkpoints.
2. Isaac Sim 6.0.1.0 install from `pypi.nvidia.com` is slow on this instance
   (roughly 170 KB/s late in the download) and was still running when this
   handoff was written. Nothing about a working Isaac Sim scene is claimed.
3. Shutdown persistence, snapshot, and recovery behavior of the AutoDL data
   volume are still unconfirmed, so no long experiment should start.
4. No Docker or Podman, so the guide's container-GPU acceptance gate cannot be
   demonstrated here. Host driver plus per-environment Python isolation is the
   substitute.
5. No `systemd`, so long jobs must run under `tmux`.
6. No `/dev/video*` device. Reconstruction integration must use the video-file,
   recorded, or synthetic input path.
7. L4 and L5 stacks are deliberately absent. PyTorch, MediaPipe, HaMeR/MANO,
   and LeRobot versions must be frozen against driver CUDA 13.0 first.
8. `assets/robot_manifest.yaml` is still a placeholder; no robot or hand asset
   has been checked.

## Local action required

None blocking. When the local machine is ready to exercise the server input
path, send a short rosbag with its SHA256, schema version, and expected frame
count so the server can replay it against the same validator.

## Next step

Finish the Isaac Sim install, then attempt the Week 1 acceptance target: a
headless scene that consumes the committed recorded sequences, replaces the CPU
prototype actuator manifest with checked robot joint names and IK, runs 1000
bounded steps, records state, and survives a five-minute smoke. Confirm data
volume persistence before starting anything long.
