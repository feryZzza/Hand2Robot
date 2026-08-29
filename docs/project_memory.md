[English](project_memory.md) | [简体中文](project_memory.zh-CN.md)

# Hand2Robot project memory

Last verified: 2026-08-29 (Asia/Shanghai)  
Current milestone: server L0-L5 environment verified on the RTX 4090 instance, including a headless Isaac Sim run; robot asset and ROS2 bridge pending  
Canonical remote: `https://github.com/feryZzza/Hand2Robot.git`

This document is the concise, version-controlled memory for future work. It records verified
facts and current decisions, not a transcript of conversations.

## Mission and completion definition

Build a reproducible path from RGB, recorded, or synthetic hand input through hand
reconstruction, calibration, retargeting, inverse kinematics, safety checks, ROS2 orchestration,
and Isaac Sim execution into versioned episode data suitable for small BC/Diffusion Policy
experiments.

The final release requires a runnable repository, a 2–3 minute demo, a 5–8 page technical
report, system/simulation and algorithm/VA resume variants, measurable failure handling, and a
reproduction checklist.

## Verified current state

- The repository began with three requirements documents under `doc/` and no source code.
- The canonical local checkout is `/home/fery/Hand2Robot`.
- The local OS is Ubuntu 22.04 with ROS2 Humble, colcon, Git, rsync, ffmpeg, CMake, Make, and
  Python 3 available.
- At the 2026-08-08 audit, `/` had approximately 4.1 GiB free and `/home` approximately
  24 GiB free. Local work is therefore restricted to lightweight builds and short samples.
- No `/dev/video*` device was present during the audit. Synthetic and recorded inputs are the
  non-blocking baseline.
- No GPU-server handoff or verified server environment report is present yet.
- The GitHub remote was empty when repository initialization began. Baseline commit `2e3ccca`
  initialized and was pushed to `main` on 2026-08-08.
- Stable branch `main` and local integration branch `work/local` both exist on `origin`.
  `work/local` was created from verified M0 memory commit `d78e063`.
- Contract commit `3fb0f80` defines schema `0.1.0`, four ROS2 messages, the 21-joint order,
  timestamp/validity/QoS rules, and frame transform direction. Five contract tests and the
  ROS2 `hand_msgs` build passed locally.
- Supplemental contract commit `cffc637` explicitly marks whether end-to-end latency is valid.
- M2 implementation commit `82f9a5f` adds the ROS-independent validator, synthetic ROS2 input,
  accepted-observation topic, system status, low-confidence fault probe, and finite smoke script.
  All 18 unit tests and all three ROS2 package builds pass.
- The committed-code M2 smoke recorded 15 valid/0 invalid/0 dropped at 30 Hz with a last sampled
  latency of 3.21 ms. Its fault phase rejected 9/9 low-confidence samples with `DEGRADED` and
  `low_confidence`. Evidence is in `runs/20260808_local_synthetic_smoke_seed0/manifest.yaml`.
- M3 commit `254e318` adds a dependency-free recorded-sequence schema/loader/player and a
  checksum-locked five-frame fixture. Commit `bbbdf27` adds raw rosbag capture plus two fresh
  validator replays; commit `8394368` unifies synthetic/recorded adapter selection by launch
  configuration. Twenty-three tests pass.
- The final M3 bag contains exactly five raw messages over 0.398 seconds. Both replays produced
  accepted sequences `[0, 1, 2, 3, 4]` from `recorded_fixture`. Evidence and bag hashes are in
  `runs/20260808_recorded_bag_replay_seed0/manifest.yaml`.
- M4 foundation commit `101e107` adds dependency-free rigid transforms, strict calibration
  loading, synthetic-only camera-to-robot calibration, and recorded-point transformation.
  Thirty-four tests pass, including inverse/composition direction and unit-error detection.
- Commit `8612de6` adds palm-local coordinates, explicit left/right anatomical mapping, palm-width
  scale normalization, low-pass and One Euro filters, bounded five-finger curl targets, workspace
  rejection, source-time rate limiting, and a monotonic stale-input watchdog.
- Commit `6c7cdbf` closes the ROS2 path through `/robot/target` and `/episode/record`, persists
  non-overwriting JSONL episodes, and adds synthetic, recorded, and interrupted-source smokes.
  Fifty-eight unit/contract tests and all three ROS2 packages pass.
- Safety fix `adc89a7` ensures any invalid result supersedes retained valid target state, so a
  later watchdog cannot revive or continue reasoning from a pre-fault command.
- Build fix `e6883b1` installs package-local checked copies of canonical runtime configuration;
  their byte equality is tested and the `hand_pipeline` colcon job exits successfully.
- The accepted prototype run produced 20 complete synthetic records, five exact recorded records
  with sequences 0–4, and one stale invalid target after 29 observed valid targets. The One Euro
  deterministic jitter ratio was 0.106169. Evidence is in
  `runs/20260808_local_cpu_prototype_seed0/manifest.yaml`.
- Documentation localization commit `2845421` established same-directory Simplified Chinese
  translations with reciprocal language links. The policy now covers all 23 English Markdown
  project documents.
- Contract commit `4662122` defines one raw `bgr8` image boundary for camera and video sources.
  Implementation commit `b19f1b1` adds the validated launch-time switch, OpenCV/cv_bridge frame
  publisher, subscriber discovery, video looping/rate controls, and a camera-free smoke. The full
  suite contains 66 tests and all three ROS2 packages build. The accepted smoke received five
  strict-timestamp `160x120` frames from an eight-frame generated MP4; evidence is in
  `runs/20260808_video_input_smoke_seed0/manifest.yaml`. Follow-up `f9f54da` makes `make doctor`
  verify visual Python dependencies and advertise video fallback when no camera is detected.
- Server commit `f7a0daf` records the first verified GPU server facts. The read-only audit ran on
  an AutoDL container with one RTX 4090 (24564 MiB, driver 580.105.08, driver CUDA 13.0),
  128 logical Xeon 8358P cores, 1.0 TiB RAM, a 30 GB `/` overlay, and an XFS persistent volume at
  `/root/autodl-tmp` measured at **50 GB**, not the 300 GB assumed earlier. There is no Docker,
  no Podman, no `systemd`, and no `/dev/video*` device. Measured values are in
  `docs/server_environment.md`; evidence is under
  `/root/autodl-tmp/embodied/artifacts/audit/`.
- Layers L0-L2 are installed and verified on the server: driver and GPU, the L1 tools, and ROS2
  Humble desktop with colcon, rosbag2, tf2, cv_bridge and OpenCV 4.5.4 built against the Ubuntu
  system Python 3.10.12 ABI. All nine repository checks pass there: `doctor.sh` exits 0 with
  visual input dependencies OK, 66 unit tests pass, colcon builds three packages, and the local,
  recorded, video-input, bag-replay and three prototype smokes reproduce the same counts,
  sequences and diagnostics the local baseline claims.
- `scripts/server_ros2_env.sh` is required on the server because Miniconda's base `python3`
  precedes `/usr/bin` on `PATH` and hides `cv2`, `cv_bridge` and `rclpy` from ROS2. It puts the
  system interpreter first and pins DDS to `ROS_LOCALHOST_ONLY=1` on domain 72.
- A fourth server Conda environment, `h2r-sim` on Python 3.12.14, exists because Isaac Sim 6.0.1
  requires Python 3.12 and cannot share the 3.10 environments ROS2 depends on. The other three
  server environments (`h2r-core`, `h2r-reconstruction`, `h2r-policy`) remain Python 3.10.20.
- Layers L3 through L5 are installed and verified on the server. Isaac Sim 6.0.1.0 with
  `[all,extscache,ros2]` runs headless: `scripts/run_sim_headless_check.py --steps 1000` reports
  10.8 s startup, 1000 steps in 3.26 s (306.9 steps/s), a cuboid settled at 0.1 m, and finite
  state, with Warp 1.13.0 on the 4090 (sm_89, CUDA Toolkit 12.9 against driver 13.0). Evidence is
  in `/root/autodl-tmp/embodied/artifacts/sim_headless/`. The check loads a primitive, not a robot
  asset, so it is not evidence for joint names, IK, or collisions.
- `h2r-reconstruction` has torch 2.9.1+cu128, MediaPipe 0.10.21, OpenCV 4.11.0.86 and numpy
  1.26.4; the MediaPipe hand graph loads over EGL on the 4090 with the expected 21-landmark
  contract. `h2r-policy` has LeRobot 0.4.4, diffusers 0.35.2, gymnasium 1.3.0, zarr, h5py and
  wandb, all importing with a finite GPU matmul. OpenCV is pinned to 4.11.0.86 because MediaPipe
  0.10.21 requires `numpy<2` while opencv-python 4.12 requires `numpy>=2`.
- `scripts/server_sim_env.sh` is the Isaac Sim entry point. It carries the user's 2026-08-29
  acceptance of the NVIDIA Omniverse License Agreement as `OMNI_KIT_ACCEPT_EULA=YES`, without
  which every Kit bootstrap blocks on an interactive prompt. It must never be sourced into the
  same shell as `scripts/server_ros2_env.sh`.
- Isaac Sim installs from `pypi.nvidia.cn`, the host `pypi.nvidia.com` returns by 301 redirect.
  Following the redirect per package ran at 263 KB/s and had not finished after 90 minutes; the
  direct host reached 11 MB/s and completed in about 15. pip verified NVIDIA index hashes either
  way. National PyPI mirrors carry only 857-byte stub packages for these releases.
- The four environments occupy 38 GB of the 50 GB volume, Isaac Sim alone 25 GB. Because
  `h2r-reconstruction` and `h2r-policy` pin the same torch 2.9.1+cu128, their identical `nvidia/`
  and `triton/` shared objects are hardlinked, reclaiming 4.81 GiB; all four environments were
  re-verified on GPU afterwards. Reinstalling torch in either breaks the sharing.

## Accepted decisions

- Local/server responsibility is split by ADR-0001.
- Git branches and release behavior follow ADR-0002 and `docs/git_workflow.md`.
- Shared contracts live in `docs/interfaces.md` and `docs/frames.md`; implementations do not
  invent alternate units, frames, or joint ordering.
- Core validation, calibration, filtering, retargeting, and data-schema logic should remain
  testable without ROS2. ROS2 packages wrap the core logic for transport and orchestration.
- Heavy artifacts never enter ordinary Git history. Git stores code, configuration, manifests,
  hashes, metrics summaries, and documentation.
- ADR-0003 limits the generic five-flexion target to a CPU test sink. It is not a physical or
  Isaac Sim command contract; asset-specific names, IK, joint limits, and collisions are a
  server-side acceptance gate.
- English and Simplified Chinese Markdown pairs are maintained together and checked in CI-style
  local tests; the already-Chinese original requirements under `doc/` are not duplicated.
- Camera and video-file sources share `/visual/input/image_raw`; reconstruction subscribes once
  and distinguishes the resulting `HandObservation.source`. Raw video does not impersonate the
  post-reconstruction `recorded` adapter.

## Current objectives

1. Confirm AutoDL data-volume persistence, snapshot, and recovery behavior before any long run.
2. Bridge Isaac Sim to the ROS2 Humble workspace across the Python 3.12/3.10 boundary, and adopt a
   retention policy that fits the roughly 13 GB left on the 50 GB volume.
3. Freeze one licensed robot/hand asset and implement its IK/collision execution adapter on the
   server without changing schema `0.1.0`.
4. Connect one server MediaPipe or HaMeR reconstruction adapter to `/visual/input/image_raw`,
   validating video mode before camera hardware is available.

## Pending verification

- Server data-volume persistence across shutdown, snapshot availability, and recovery behavior.
  Server OS, GPU, driver, RAM, disk paths, free space, and container runtime are now measured in
  `docs/server_environment.md`, but AutoDL retention is untested. Validation: stop and restart the
  instance, then confirm `/root/autodl-tmp/embodied` survives intact.
- The Isaac Sim ROS2 bridge. `isaacsim-ros2` is installed but no bridged topic has crossed the
  Python 3.12/3.10 boundary. Validation: publish and receive one topic between a Kit scene and the
  ROS2 Humble workspace.
- Long-run stability. Only bounded 1000-step runs are verified. Validation: run the 30-minute
  headless soak and the five-minute continuous smoke, recording resource growth.
- Whether roughly 13 GB of remaining volume is sufficient for datasets and checkpoints.
  Validation: size the Week 5-6 data plan against measured free space, then set retention limits.
- Actual robot asset pair. Current example is Franka/Panda plus Allegro Hand, but this is not
  frozen until server asset and license checks pass.
- Physical camera availability and server MediaPipe/HaMeR environment. Video frame transport is
  verified locally, but representative-video reconstruction and the real camera path are pending.
- Repository code license. The initial ROS2 package uses `TODO` until the user selects a license;
  no external code or asset should be added under an assumed license.

## Risks and stop conditions

- Do not install system packages or large Python environments on the local machine.
- Stop local project processes when `/` has less than 3 GiB free.
- Keep at least 15 GiB free on `/home`; keep total new local project content below 8 GiB.
- Do not expose raw ROS2 DDS to the public internet.
- Do not begin HaMeR/MANO, dataset, or training work until the server data volume's shutdown
  persistence and recovery behavior are verified.
- Do not reinstall torch in `h2r-reconstruction` or `h2r-policy`. That breaks the hardlink sharing
  of their identical CUDA libraries and costs back 4.81 GiB on a volume with roughly 13 GB free.
- Keep every growing path on the server's persistent volume, never the 30 GB `/` overlay. Apply
  the space thresholds in `docs/server_environment.md`: warn below 25% free, stop new experiments
  below 15%.
- Run long server jobs under `tmux`. The instance has no `systemd`, so user services are not
  available.

## Next actions

1. Confirm the AutoDL data volume survives a stop/start cycle before starting anything long.
2. Exchange one bridged ROS2 topic between an Isaac Sim Kit scene and the ROS2 Humble workspace,
   then run the 30-minute soak and five-minute continuous smoke.
3. Connect the selected reconstruction backend once to `/visual/input/image_raw` and validate a
   checksum-recorded server video before testing a physical camera.
4. Replace the CPU test manifest with one checked server asset manifest, then implement actual IK,
   collision limits, execution feedback, and the 1000-step headless gate.

## Memory update rules

- Update “Verified current state” only from commands, committed files, or accepted handoffs.
- Put uncertainty in “Pending verification”, including the exact validation action.
- Record architecture changes as ADRs; never silently rewrite an accepted decision.
- After each verified milestone, update the relevant handoff with commit, tests, artifacts,
  known issues, and next action.
- Keep this file concise. Detailed experiment history belongs in `runs/` and detailed progress
  belongs in `docs/roadmap.md`.
- Update this English file and `project_memory.zh-CN.md` together.
