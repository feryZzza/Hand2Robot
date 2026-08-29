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

Layers L0 through L5 are installed and verified:

- L0: driver 580.105.08, one RTX 4090 with 24564 MiB visible to `nvidia-smi`.
- L1: git, cmake, tmux, ffmpeg, rsync, gcc.
- L2: ROS2 Humble desktop, colcon, rosbag2, tf2, cv_bridge, OpenCV 4.5.4,
  installed against the Ubuntu system Python 3.10.12 ABI.
- L3: Isaac Sim 6.0.1.0 with `[all,extscache,ros2]` in `h2r-sim`, proven by a
  headless 1000-step run.
- L4: torch 2.9.1+cu128, MediaPipe 0.10.21, OpenCV 4.11.0.86, numpy 1.26.4 in
  `h2r-reconstruction`, with the hand graph loading over EGL on the 4090.
- L5: LeRobot 0.4.4, diffusers 0.35.2, gymnasium 1.3.0, zarr, h5py, wandb in
  `h2r-policy`.

Two version conflicts were resolved by measurement, not assumption. MediaPipe
0.10.21 requires `numpy<2` while opencv-python 4.12 requires `numpy>=2`, so
OpenCV is pinned to 4.11.0.86, which accepts numpy 1.x. Isaac Sim ships its own
torch 2.11.0+cu130 inside `h2r-sim` and does not share the 2.9.1+cu128 pin used
by the two Python 3.10 environments.

`scripts/server_ros2_env.sh` is the ROS2 entry point. It is required because
Miniconda's base `python3` precedes `/usr/bin` on `PATH` and hides `cv2`,
`cv_bridge`, and `rclpy` from ROS2. It also pins DDS to `ROS_LOCALHOST_ONLY=1`
on domain 72.

A fourth Conda environment, `h2r-sim` on Python 3.12.14, was added because
Isaac Sim 6.0.1 requires Python 3.12 and cannot share the 3.10 environments
that ROS2 depends on. `scripts/server_sim_env.sh` is its entry point and carries
the user's 2026-08-29 acceptance of the NVIDIA Omniverse License Agreement as
`OMNI_KIT_ACCEPT_EULA=YES`; without it every Kit bootstrap blocks on an
interactive prompt.

Isaac Sim was installed from `pypi.nvidia.cn`, the host `pypi.nvidia.com`
returns by 301 redirect. Following the redirect per package ran at 263 KB/s and
had not finished after 90 minutes; the direct host reached 11 MB/s and completed
in about 15. pip verified every package against the NVIDIA index hashes either
way.

The 50 GB volume needed active management. `h2r-reconstruction` and `h2r-policy`
pin the same torch 2.9.1+cu128, so their identical `nvidia/` and `triton/`
shared objects are hardlinked, reclaiming 4.81 GiB. All four environments were
re-verified on GPU afterwards.

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

Beyond the repository checks:

| Check | Result |
|---|---|
| `scripts/run_sim_headless_check.py --steps 1000` | startup 10.8 s, 1000 steps in 3.26 s (306.9 steps/s), cuboid height 0.1 m, state finite, settled |
| Warp init | 1.13.0 on RTX 4090, sm_89, CUDA Toolkit 12.9 against driver 13.0 |
| `h2r-reconstruction` GPU | torch 2.9.1+cu128 sees the 4090, GPU matmul finite, MediaPipe hand graph loads over EGL with 21 landmarks |
| `h2r-policy` GPU | torch, LeRobot, diffusers, gymnasium, zarr, h5py import; GPU matmul finite |

## Generated artifacts

- `/root/autodl-tmp/embodied/artifacts/audit/server_audit_20260829T134813Z.txt`
- `/root/autodl-tmp/embodied/artifacts/sim_headless/headless_20260829T162805Z.json`
- `/root/autodl-tmp/embodied/config/environments/{h2r-core,h2r-reconstruction,h2r-policy,h2r-sim}.lock`
- Episode JSONL and smoke logs under the ignored `local_data/` tree.

## Known issues

1. The persistent volume is **50 GB**, not the 300 GB recorded in earlier
   notes, and the four environments already occupy 38 GB (Isaac Sim alone is
   25 GB). Roughly 13 GB remains, which is the binding constraint on datasets
   and checkpoints. Prune `cache/pip` after every large install.
2. The Isaac Sim ROS2 bridge is untested. `isaacsim-ros2` is installed but no
   bridged topic has been exchanged with the ROS2 Humble workspace.
3. Shutdown persistence, snapshot, and recovery behavior of the AutoDL data
   volume are still unconfirmed, so no long experiment should start.
4. No Docker or Podman, so the guide's container-GPU acceptance gate cannot be
   demonstrated here. Host driver plus per-environment Python isolation is the
   substitute.
5. No `systemd`, so long jobs must run under `tmux`.
6. No `/dev/video*` device. Reconstruction integration must use the video-file,
   recorded, or synthetic input path.
7. HaMeR/MANO is still absent. MediaPipe is the only reconstruction backend
   installed; MANO needs its license accepted and model files that must never
   enter Git.
8. `assets/robot_manifest.yaml` is still a placeholder; no robot or hand asset
   has been checked. The headless check uses a primitive cuboid on purpose.
9. No 30-minute stability or five-minute continuous smoke has run. Only bounded
   1000-step runs are verified, so long-run resource growth is unknown.
10. Reinstalling torch in `h2r-reconstruction` or `h2r-policy` breaks the
    hardlink sharing and costs back 4.81 GiB.

## Local action required

None blocking. When the local machine is ready to exercise the server input
path, send a short rosbag with its SHA256, schema version, and expected frame
count so the server can replay it against the same validator.

## M5 progress at 2026-08-30

Commits `d007050`, `705dc10`, `7bb1057` on `work/server`.

Done and verified:

- Assets staged on the data volume under `datasets/raw/assets`: the Franka Panda
  bundled with Isaac Sim, and the Allegro right hand from dex-urdf. The NVIDIA
  cloud asset server returns 404 and GitHub is unreachable, so the hand came
  through the `ghfast.top` proxy.
- `scripts/audit_sim_assets.py` confirms the manifest against the simulated
  articulations: 9 arm DOF, 16 hand DOF, zero missing joints, zero unexpected
  joints, zero limit mismatches.
- `hand2robot_core.dexterous_hand` maps the 21-joint human contract onto 16
  Allegro joints, one abduction plus three flexion stages per finger. 23 new
  tests; the suite is 89 and passes.
- `scripts/evaluate_arm_ik.py` with Isaac Sim's Lula solver: **729/729**
  end-effector positions solved inside the measured workspace box, all within
  the manifest joint limits. This corrected a guess: the CPU prototype's wider
  box reached only 94.4%, with every failure on the Panda's reach boundary.
- Panda drive gains measured at 1e5 Nm/rad and 1e4 Nm*s/rad, holding a commanded
  posture over 600 steps with a 0.00154 rad peak error.

Blocked, with the cause identified:

- The dex-urdf Allegro hand is not usable under physics in Isaac Sim 6.0.1.0.
  Its joints drift from limits of about 1.5 rad past 100 rad within 300 steps,
  and three thumb joints start outside their limits before the first physics
  step. The Panda is stable in the same scene, so the defect is asset-specific.
- Eleven approaches were measured and ruled out. The full list is in the
  manifest under `hand.thumb_chain_defect` and in commit `7bb1057`. Do not
  restart from drive tuning.
- `scripts/run_sim_execution_check.py` therefore reports the hand as out of
  limits. That failure is real and is not suppressed. The arm half of the loop
  is sound.

Next: evaluate a replacement hand asset with `scripts/audit_sim_assets.py`
before rewiring the finger groups. LEAP Hand (MIT, 16 revolute joints) and
SCHUNK SVH (Apache-2.0, 20 joints) are both confirmed downloadable from the same
dex-urdf repository through the proxy.

## Next step

Confirm the data volume survives a stop/start cycle, then attempt the rest of the
Week 1 acceptance target: a headless scene that consumes the committed recorded
sequences, replaces the CPU prototype actuator manifest with checked robot joint
names and IK, records state, and survives a five-minute smoke. The bounded
1000-step part of that gate is already met by
`scripts/run_sim_headless_check.py`, but with a primitive, not a robot. Bridging
Isaac Sim to the ROS2 Humble workspace across the Python 3.12/3.10 boundary is
the next unproven piece.
