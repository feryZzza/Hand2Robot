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
| L3 | Isaac Sim 6.0.1.0 (pip, `[all,extscache,ros2]`) in `h2r-sim` | verified headless, 1000 bounded steps |
| L4 | PyTorch 2.9.1+cu128, MediaPipe 0.10.21, OpenCV 4.11.0.86, numpy 1.26.4 | verified on GPU; HaMeR/MANO still absent |
| L5 | LeRobot 0.4.4, diffusers 0.35.2, gymnasium 1.3.0, zarr, h5py, wandb | verified imports on GPU; no experiment run |

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

Conda prefixes live under `/root/autodl-tmp/embodied/envs/conda/`. Frozen package
sets are exported to
`/root/autodl-tmp/embodied/config/environments/<name>.lock`.

`h2r-reconstruction` and `h2r-policy` both pin torch 2.9.1+cu128, so their
identical `nvidia/` and `triton/` shared objects are hardlinked together. This
reclaimed 4.81 GiB of the 50 GB volume. Reinstalling torch in either environment
breaks the sharing and costs that space back.

### Activation

Miniconda's base `python3` precedes `/usr/bin` on `PATH`, which hides `cv2`,
`cv_bridge`, and the `rclpy` extension modules from ROS2. Source the ROS2
environment file for any ROS2 or colcon work; it puts the system interpreter
first and keeps DDS host-local.

```bash
source scripts/server_ros2_env.sh                             # ROS2 + workspace
source scripts/server_sim_env.sh                              # Isaac Sim (py3.12)
source /root/autodl-tmp/embodied/config/activate.sh h2r-core   # other Conda envs
```

Never source the ROS2 and Isaac Sim entry points into the same shell. They use
different Python versions and must communicate over ROS2 messages, versioned
files, or an explicit RPC contract.

`scripts/server_sim_env.sh` exports `OMNI_KIT_ACCEPT_EULA=YES`, recording the
user's acceptance of the NVIDIA Omniverse License Agreement on 2026-08-29.
Without it every Kit bootstrap stops on an interactive prompt.

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

### Isaac Sim headless check

`scripts/run_sim_headless_check.py` brings up a headless `SimulationApp`, adds a
ground plane and one dynamic cuboid, steps physics a bounded number of times, and
asserts the state is finite and settled. Run it from the Isaac Sim environment:

```bash
source scripts/server_sim_env.sh
python scripts/run_sim_headless_check.py --steps 1000 \
  --json /root/autodl-tmp/embodied/artifacts/sim_headless/headless_$(date -u +%Y%m%dT%H%M%SZ).json
```

Measured on 2026-08-29: startup 10.8 s, 1000 steps in 3.26 s (306.9 steps/s),
final cuboid height 0.1 m, state finite, settled. Warp 1.13.0 initialized on the
RTX 4090 (sm_89, CUDA Toolkit 12.9 against driver 13.0). The check loads no robot
asset, so it is not evidence for joint names, IK, or collision behavior.

### Reconstruction and policy checks

- `h2r-reconstruction`: torch 2.9.1+cu128 reports CUDA available on the RTX 4090,
  a GPU matmul returns finite values, and the MediaPipe hand graph loads over EGL
  with the expected 21-landmark contract.
- `h2r-policy`: torch, LeRobot 0.4.4, diffusers, gymnasium, zarr, and h5py all
  import and a GPU matmul returns finite values.

## Risks and unverified items

1. **Persistent disk is 50 GB, not 300 GB, and the environments already use
   38 GB.** Isaac Sim alone is 25 GB; `h2r-reconstruction` and `h2r-policy` are
   roughly 8 GB each before hardlink deduplication. Roughly 13 GB remains, so
   datasets, checkpoints, and Isaac asset caches need a retention policy before
   Week 5-6. Prune `cache/pip` after every large install.
2. **Shutdown persistence and snapshots are unconfirmed.** The AutoDL data
   volume retention and snapshot behavior have not been tested, so no long
   experiment should start yet.
3. **No container runtime.** Container GPU isolation from the guide's L0
   acceptance gate cannot be demonstrated on this instance; the host driver
   plus per-environment Python isolation is the substitute.
4. **No `systemd`.** Long jobs must use `tmux`, not user services.
5. **The Isaac Sim ROS2 bridge is untested.** `isaacsim-ros2` is installed but
   no bridged topic has been exchanged with the ROS2 Humble workspace, and the
   two runtimes are on different Python versions by design.
6. **Robot and hand assets are not chosen.** `assets/robot_manifest.yaml`
   remains a placeholder; Franka/Panda plus Allegro is the intended target but
   joint names, limits, and licenses are unchecked. The headless check
   deliberately uses a primitive cuboid, not a robot.
7. **HaMeR/MANO is absent.** MediaPipe is the only reconstruction backend
   installed. MANO requires accepting its license and obtaining model files that
   must never enter Git.
8. **No 30-minute stability or five-minute continuous smoke has run.** Only
   bounded 1000-step runs are verified, so resource-growth behavior over time is
   unknown.
9. **Isaac Sim was installed from `pypi.nvidia.cn`**, the domain
   `pypi.nvidia.com` returns by 301 redirect. Direct use reached 11 MB/s against
   263 KB/s through the redirect chain, cutting the install from over 90 minutes
   to about 15. pip still verified every package against the NVIDIA index
   hashes.

## Space policy

`/root/autodl-tmp` free-space thresholds, applied against the measured 50 GB:

| Free share | State | Action |
|---:|---|---|
| above 25% | normal | continue |
| 15-25% | warning | archive runs, prune reconstructible caches |
| below 15% | red line | no new experiments until space is reclaimed |
