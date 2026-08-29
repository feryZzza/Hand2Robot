[English](server_bootstrap.md) | [简体中文](server_bootstrap.zh-CN.md)

# GPU server bootstrap boundary

The read-only audit has run on the RTX 4090 instance. Measured values are in
[`docs/server_environment.md`](server_environment.md); layers L0 through L2 are verified there.
This file remains the gate for anything larger. Do not install HaMeR/MANO, datasets, or training
environments until their versions are frozen against the measured driver and the **50 GB**
persistent volume.

To re-audit, or to bring up another server, run:

```bash
./scripts/server_audit_readonly.sh | tee local_data/server_audit.txt
```

Review the output and populate `docs/handoff/server_latest.md` with measured values. Then source
the ROS2 entry point before any ROS2 or colcon work; the Miniconda base `python3` otherwise hides
`cv2`, `cv_bridge`, and `rclpy` from ROS2:

```bash
source scripts/server_ros2_env.sh
```

Before any large install, freeze:

1. the persistent project/data/cache paths and minimum free-space policy;
2. NVIDIA driver, GPU, container runtime, and container GPU access;
3. Isaac Sim version and robot/hand asset names plus licenses;
4. ROS2/bridge compatibility with schema `0.1.0`;
5. snapshot, shutdown persistence, remote access, and artifact transfer behavior.

## Camera/video input switch

The server no longer requires a physically attached camera to begin reconstruction integration.
Both visual sources publish the same raw image topic:

```bash
# Attached camera
ros2 launch hand_pipeline visual_input.launch.py \
  visual_input_mode:=camera camera_device:=0

# Server-resident test video
ros2 launch hand_pipeline visual_input.launch.py \
  visual_input_mode:=video \
  video_path:=/persistent/data/hand_input.mp4 \
  loop_video:=true
```

Run `make smoke-video-input` before connecting MediaPipe or HaMeR. Then make the reconstruction
adapter subscribe to `/visual/input/image_raw` and publish `/hand/observation/raw` for both modes.
Keep videos on the persistent data disk and record their SHA256 in run manifests; never add them
to Git. The video's source camera and matching calibration must be recorded together.

The first server acceptance target is not training. It is a headless scene that consumes the
committed recorded sequences, replaces the CPU prototype actuator manifest with checked robot
joint names and IK, runs 1000 bounded steps, records state, and survives a five-minute smoke.
