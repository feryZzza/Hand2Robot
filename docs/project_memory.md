# Hand2Robot project memory

Last verified: 2026-08-08 (Asia/Shanghai)  
Current milestone: M0 — repository bootstrap and shared-contract definition  
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
- The GitHub remote was empty when repository initialization began.

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

1. Finish the lightweight repository skeleton and project-memory system.
2. Define version 0.1 drafts for `HandObservation`, `RobotTarget`, `SystemStatus`, and
   `EpisodeRecord`.
3. Implement a CPU-only ROS2 synthetic-input-to-diagnostics smoke path.
4. Obtain `docs/handoff/server_latest.md` populated from a read-only RTX 4090 server audit.

## Pending verification

- Server OS, GPU, driver, RAM, persistent data-disk path, free space, container runtime, and
  snapshot behavior. Validation: complete the server audit guide and update the server handoff.
- Actual robot asset pair. Current example is Franka/Panda plus Allegro Hand, but this is not
  frozen until server asset and license checks pass.
- Camera availability and MediaPipe package availability. Validation is deferred until after
  the synthetic CPU baseline.

## Risks and stop conditions

- Do not install system packages or large Python environments on the local machine.
- Stop local project processes when `/` has less than 3 GiB free.
- Keep at least 15 GiB free on `/home`; keep total new local project content below 8 GiB.
- Do not expose raw ROS2 DDS to the public internet.
- Do not begin Isaac Sim, HaMeR/MANO, dataset, or training work until the server persistent disk
  and recovery behavior are verified.

## Next actions

1. Commit and push the M0 repository baseline.
2. Draft and review interface and frame contracts as a separate `contract:` commit.
3. Create ROS2 `hand_msgs` plus synthetic publisher and validator packages.
4. Add deterministic CPU tests for valid and malformed observations.

## Memory update rules

- Update “Verified current state” only from commands, committed files, or accepted handoffs.
- Put uncertainty in “Pending verification”, including the exact validation action.
- Record architecture changes as ADRs; never silently rewrite an accepted decision.
- After each verified milestone, update the relevant handoff with commit, tests, artifacts,
  known issues, and next action.
- Keep this file concise. Detailed experiment history belongs in `runs/` and detailed progress
  belongs in `docs/roadmap.md`.
