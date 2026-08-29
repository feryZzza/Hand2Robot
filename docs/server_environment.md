[English](server_environment.md) | [简体中文](server_environment.zh-CN.md)

# Server environment

Measured on 2026-08-29 from the read-only audit in
`scripts/server_audit_readonly.sh`. Evidence is kept on the persistent data
volume under `/root/autodl-tmp/embodied/artifacts/audit/`.

## Platform

| Item | Measured value |
|---|---|
| Host | `autodl-container-y6mn6kl23q-4a4f13e4`, AutoDL container, no systemd (PID 1 is not systemd) |
| OS | Ubuntu 22.04.4 LTS (jammy), kernel 5.15.0-78-generic |
| GPU | 1x NVIDIA GeForce RTX 4090, 24564 MiB, no ECC, idle at audit time |
| Driver / CUDA | 580.105.08, driver reports CUDA 13.0 |
| CPU | 2x Intel Xeon Platinum 8358P, 128 logical cores, 2 NUMA nodes |
| RAM | 1.0 TiB total, 944 GiB available, no swap |
| System disk | 30 GB overlay on `/`, roughly 19 GiB free after the ROS2 install |
| Persistent disk | `/dev/md0` XFS mounted at `/root/autodl-tmp`, **50 GB**, not 300 GB |
| Container runtime | Docker and Podman are absent; Docker-in-Docker is not available |
| Camera | No `/dev/video*` device; video-file, recorded, and synthetic input are the usable sources |

The 50 GB persistent quota is the binding constraint on this instance. It
supersedes the 300 GB figure recorded in earlier notes.

## Storage layout

The guide's `/data/embodied` example maps to `/root/autodl-tmp/embodied` here.
Nothing that grows belongs on the 30 GB overlay.

```text
/root/autodl-tmp/embodied/
├── repos/hand2robot/        # server-side checkout (work/server)
├── datasets/{raw,processed}/
├── runs/<run_id>/
├── checkpoints/
├── cache/{conda,hf,torch,pip,xdg,tmp,isaac}/
├── artifacts/{audit,gpu_smoke}/
├── logs/
├── archives/
└── config/                  # env.sh, activate.sh, ros2_env.sh, environments/
```

`datasets/raw` is read-only. Cache, processed data, runs, and checkpoints stay
separated so reconstructible bytes can be reclaimed without touching raw data.

## Software layers

| Layer | Component | State |
|---|---|---|
| L0 | NVIDIA driver 580.105.08, GPU visible via `nvidia-smi` | verified |
| L1 | git 2.34.1, cmake 3.22.1, tmux 3.2a, ffmpeg 4.4.2, rsync 3.2.7, gcc 11.4.0 | verified |
| L2 | ROS2 Humble desktop, colcon, rosbag2, tf2, cv_bridge, OpenCV 4.5.4 | verified |
| L3 | Isaac Sim 6.0.1.0 (pip, `[all,extscache,ros2]`) in `h2r-sim` | installed, headless run not yet verified |
| L4 | PyTorch, MediaPipe, HaMeR/MANO | not installed; versions not frozen |
| L5 | LeRobot, BC/Diffusion Policy | not installed |

## Python environments

ROS2 Humble is built against the Ubuntu system Python 3.10 ABI and is used
outside Conda. Isaac Sim 6.0.1 requires Python 3.12, so it cannot share the
3.10 environments and gets its own prefix.

| Environment | Python | Scope |
|---|---:|---|
| system `/usr/bin/python3` | 3.10.12 | ROS2, colcon, `hand_msgs`, `hand_pipeline`, `hand2robot_core` |
| `h2r-core` | 3.10.20 | contracts, calibration, retargeting, IK, tests |
| `h2r-reconstruction` | 3.10.20 | MediaPipe and HaMeR/MANO |
| `h2r-policy` | 3.10.20 | LeRobot, BC, Diffusion Policy |
| `h2r-sim` | 3.12.14 | Isaac Sim 6.0.1.0 and its ROS2 bridge extension |

Conda prefixes live under `/root/autodl-tmp/embodied/envs/conda/`.

### Activation

Miniconda's base `python3` precedes `/usr/bin` on `PATH`, which hides `cv2`,
`cv_bridge`, and the `rclpy` extension modules from ROS2. Source the ROS2
environment file for any ROS2 or colcon work; it puts the system interpreter
first and keeps DDS host-local.

```bash
source /root/autodl-tmp/embodied/config/ros2_env.sh          # ROS2 + workspace
source /root/autodl-tmp/embodied/config/activate.sh h2r-core  # Conda envs
```

## Verified tests

Run from `/root/Hand2Robot` after sourcing `ros2_env.sh`:

| Check | Result |
|---|---|
| `scripts/doctor.sh` | exit 0, visual input dependencies OK |
| `make test-unit` | 66 tests, OK |
| `colcon build --symlink-install` | 3 packages finished |
| `make smoke-local` | 16 observations, 15 valid, 0 drops, 30.0 Hz, 2.62 ms latency; fault probe reached 9 invalid with `low_confidence` |
| `make smoke-recorded` | count 5, sequences 0-4, source `recorded_fixture` |
| `make smoke-video-input` | 5 frames, 160x120, `bgr8`, strict timestamps |
| `make smoke-bag` | 5 bag messages, two independent replays each 0-4 |
| `make smoke-prototype` | 20 records, sequences 0-19, complete and successful |
| `make smoke-prototype-recorded` | 5 records, sequences 0-4 |
| `make smoke-prototype-watchdog` | passed |

## Risks and unverified items

1. **Persistent disk is 50 GB, not 300 GB.** Isaac Sim plus its extension
   cache consumes a large share. The pip cache under
   `cache/pip` must be pruned after installs, and datasets, checkpoints, and
   Isaac asset caches need a retention policy before Week 5-6 work.
2. **Shutdown persistence and snapshots are unconfirmed.** The AutoDL data
   volume retention and snapshot behavior have not been tested, so no long
   experiment should start yet.
3. **No container runtime.** Container GPU isolation from the guide's L0
   acceptance gate cannot be demonstrated on this instance; the host driver
   plus per-environment Python isolation is the substitute.
4. **No `systemd`.** Long jobs must use `tmux`, not user services.
5. **Isaac Sim headless closed loop is unproven.** Version 6.0.1.0 is
   installed but the 1000-step run, ROS2 bridge, robot assets, and five-minute
   stability smoke are still open.
6. **Robot and hand assets are not chosen.** `assets/robot_manifest.yaml`
   remains a placeholder; Franka/Panda plus Allegro is the intended target but
   joint names, limits, and licenses are unchecked.
7. **L4 and L5 stacks are deliberately absent.** PyTorch, MediaPipe,
   HaMeR/MANO, and LeRobot versions must be frozen against driver CUDA 13.0
   before download.

## Space policy

`/root/autodl-tmp` free-space thresholds, applied against the measured 50 GB:

| Free share | State | Action |
|---:|---|---|
| above 25% | normal | continue |
| 15-25% | warning | archive runs, prune reconstructible caches |
| below 15% | red line | no new experiments until space is reclaimed |
