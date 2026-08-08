[English](project_memory.md) | [简体中文](project_memory.zh-CN.md)

# Hand2Robot project memory

Last verified: 2026-08-08 (Asia/Shanghai)  
Current milestone: local CPU prototype and switchable visual input verified; M5 server adaptation pending  
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

1. Obtain `docs/handoff/server_latest.md` populated from a read-only RTX 4090 server audit.
2. Freeze one licensed robot/hand asset and implement its IK/collision execution adapter on the
   server without changing schema `0.1.0`.
3. Connect one server MediaPipe or HaMeR reconstruction adapter to `/visual/input/image_raw`,
   validating video mode before camera hardware is available.

## Pending verification

- Server OS, GPU, driver, RAM, persistent data-disk path, free space, container runtime, and
  snapshot behavior. Validation: complete the server audit guide and update the server handoff.
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
- Do not begin Isaac Sim, HaMeR/MANO, dataset, or training work until the server persistent disk
  and recovery behavior are verified.

## Next actions

1. Run `scripts/server_audit_readonly.sh` on the RTX 4090 host and update the server handoff.
2. Verify persistent disk, container GPU, Isaac Sim version, asset licenses, and recovery before
   installing or downloading anything large.
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
