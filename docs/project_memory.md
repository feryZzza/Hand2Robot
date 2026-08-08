# Hand2Robot project memory

Last verified: 2026-08-08 (Asia/Shanghai)  
Current milestone: M4 — calibration and retargeting foundation  
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

## Accepted decisions

- Local/server responsibility is split by ADR-0001.
- Git branches and release behavior follow ADR-0002 and `docs/git_workflow.md`.
- Shared contracts live in `docs/interfaces.md` and `docs/frames.md`; implementations do not
  invent alternate units, frames, or joint ordering.
- Core validation, calibration, filtering, retargeting, and data-schema logic should remain
  testable without ROS2. ROS2 packages wrap the core logic for transport and orchestration.
- Heavy artifacts never enter ordinary Git history. Git stores code, configuration, manifests,
  hashes, metrics summaries, and documentation.

## Current objectives

1. Add palm-relative scale normalization and low-pass/One Euro filtering on deterministic
   trajectories without publishing robot commands.
2. Obtain `docs/handoff/server_latest.md` populated from a read-only RTX 4090 server audit.

## Pending verification

- Server OS, GPU, driver, RAM, persistent data-disk path, free space, container runtime, and
  snapshot behavior. Validation: complete the server audit guide and update the server handoff.
- Actual robot asset pair. Current example is Franka/Panda plus Allegro Hand, but this is not
  frozen until server asset and license checks pass.
- Camera availability and MediaPipe package availability. Validation is deferred until after
  the synthetic CPU baseline.
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

1. Define palm basis and hand-scale normalization with left/right tests.
2. Implement low-pass and One Euro filters with explicit timestamp handling.
3. Compare raw/filtered deterministic trajectories for jitter and lag before adding IK.

## Memory update rules

- Update “Verified current state” only from commands, committed files, or accepted handoffs.
- Put uncertainty in “Pending verification”, including the exact validation action.
- Record architecture changes as ADRs; never silently rewrite an accepted decision.
- After each verified milestone, update the relevant handoff with commit, tests, artifacts,
  known issues, and next action.
- Keep this file concise. Detailed experiment history belongs in `runs/` and detailed progress
  belongs in `docs/roadmap.md`.
