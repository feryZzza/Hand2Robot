# Local handoff

- Updated: 2026-08-08 (Asia/Shanghai)
- Git commit: `82f9a5f` (`work/local`, pending push with this evidence update)
- Branch: `work/local` (pushed and tracking `origin/work/local`)
- Schema version: accepted `0.1.0`
- Disk: `/` approximately 4.1 GiB free; `/home` approximately 24 GiB free
- Input: no camera detected; synthetic input is the planned baseline

## Completed

- Read the local guide, server guide, and full 29-page implementation checklist.
- Audited the initial workspace and core local commands.
- Established repository memory, ADR, handoff, Git workflow, and safety rules.
- Ran the read-only local doctor and pushed the verified M0 baseline to GitHub.
- Created the protected local integration path through `work/local`.
- Defined and compiled the four ROS2 interfaces and accepted the frame/transform contract.
- Added the synthetic publisher, ROS-independent validator, ROS2 validation/status node, and
  normal plus low-confidence smoke probes.

## Local verification

- ROS2 Humble and colcon commands are available.
- Eighteen unit/contract tests pass; `hand_msgs`, `hand2robot_core`, and `hand_pipeline` build.
- Final M2 smoke: 15 valid, 0 invalid, 0 dropped, 30 Hz, last sampled latency 3.21 ms.
- Fault smoke: 0 valid, 9 invalid, state `DEGRADED`, error `low_confidence`.
- No model, dataset, virtual environment, or system package was installed.

## Uploaded files and checksums

None.

## Server action required

Complete the read-only server audit and populate `server_latest.md` before large installation or
simulation work.

## Known issues

- Low root-partition headroom prohibits local dependency installation.
- Camera availability is unresolved but does not block synthetic input.

## Next step

Add deterministic recorded input and verify repeatable short rosbag replay.
