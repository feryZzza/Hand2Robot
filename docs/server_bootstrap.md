[English](server_bootstrap.md) | [简体中文](server_bootstrap.zh-CN.md)

# GPU server bootstrap boundary

No server facts have been verified yet. Do not install Isaac Sim, HaMeR/MANO, datasets, or
training environments until the read-only audit proves the GPU, persistent data disk, free
space, container runtime, and recovery model.

On the server, check out the same repository and run:

```bash
git switch work/server
./scripts/server_audit_readonly.sh | tee local_data/server_audit.txt
```

Review the output and populate `docs/handoff/server_latest.md` with measured values. Before any
large install, freeze:

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
