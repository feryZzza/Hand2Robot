[English](local_latest.md) | [简体中文](local_latest.zh-CN.md)

# Local handoff

- Updated: 2026-08-08 (Asia/Shanghai)
- Git commits: `8612de6` (core), `6c7cdbf` (ROS loop), `adc89a7` (safety), `e6883b1` (build),
  `2845421` (bilingual documentation), `4662122` (visual contract), `b19f1b1` (visual switch),
  `f9f54da` (visual diagnostics)
- Branch: `work/local` (pushed and tracking `origin/work/local`)
- Schema version: accepted `0.1.0`
- Disk: `/` approximately 4.1 GiB free; `/home` approximately 24 GiB free
- Input: synthetic/recorded observations and video RGB verified; no camera detected

## Completed

- Read the local guide, server guide, and full 29-page implementation checklist.
- Audited the initial workspace and core local commands.
- Established repository memory, ADR, handoff, Git workflow, and safety rules.
- Ran the read-only local doctor and pushed the verified M0 baseline to GitHub.
- Created the protected local integration path through `work/local`.
- Defined and compiled the four ROS2 interfaces and accepted the frame/transform contract.
- Added the synthetic publisher, ROS-independent validator, ROS2 validation/status node, and
  normal plus low-confidence smoke probes.
- Added the recorded JSON schema/player, checksum-locked five-frame fixture, unified input-mode
  launch, short rosbag capture, and independent double-replay checker.
- Added strict SE(3), calibration loading, unit/frame validation, and synthetic-fixture point
  transformation without publishing robot commands.
- Added palm-local scale normalization, explicit left/right mapping, low-pass and One Euro
  filters, calibrated wrist pose, five bounded prototype finger targets, workspace/rate limits,
  and a fail-closed stale-input watchdog.
- Added `/robot/target`, `/episode/record`, sequence alignment, JSONL persistence, a full launch,
  and finite synthetic, recorded, and interrupted-source acceptance scripts.
- Added Simplified Chinese counterparts for all 23 English documents, reciprocal language
  switches, and an automated localization completeness test.
- Added one stable raw-image topic with a launch-time `camera`/`video` switch, strict file and
  rate validation, subscriber discovery, optional video looping, and a finite video smoke.

## Local verification

- ROS2 Humble and colcon commands are available.
- Sixty-six unit/contract/documentation tests pass; all three ROS2 packages build.
- Video-input smoke: five `160x120` `bgr8` frames received with valid payloads and strictly
  increasing timestamps from an eight-frame generated MP4.
- Final M2 smoke: 15 valid, 0 invalid, 0 dropped, 30 Hz, last sampled latency 3.21 ms.
- Fault smoke: 0 valid, 9 invalid, state `DEGRADED`, error `low_confidence`.
- Recorded smoke: exactly 5 frames with sequences 0–4, 0 invalid, and 0 dropped.
- Bag smoke: 5 raw SQLite3 messages; two fresh validators each accepted sequences 0–4 exactly.
- Calibration: recorded wrist `[0.0, 0.06, 0.45]` maps to robot-base
  `[0.5, 0.06, 1.25]`; inverse/composition/unit-error checks pass.
- Filter evaluation: deterministic jitter RMS falls from `0.004` m to `0.000424675` m, ratio
  `0.106169`.
- Prototype synthetic smoke: 20 complete, paired, valid records and a checksum-verified JSONL.
- Prototype recorded smoke: five complete records with exact sequences 0–4.
- Watchdog smoke: 29 observed valid targets followed by exactly one `STALE_INPUT` invalid target.
- No model, dataset, virtual environment, or system package was installed.

## Uploaded files and checksums

No external upload. The generated video remains ignored; its SHA256 is
`cc864de1b5f6037e2f457f4333bf46c02ba698a0eeb1682158cc5877a2ab4b5a`. The tracked fixture SHA256 is
`73dac677df09df1ab6d82b78710911025cf8b34d0c4e84bc34f42c185802c725`;
the 37,876-byte local bag and its hashes are recorded in the M3 run manifest.

## Server action required

Complete the read-only server audit and populate `server_latest.md` before large installation or
simulation work.

## Known issues

- Low root-partition headroom prohibits local dependency installation.
- Camera availability is unresolved but no longer blocks raw visual/reconstruction integration;
  use the verified video mode first.
- The sandbox blocks UDP interface enumeration and emits Fast DDS warnings; local ROS transport
  still passed. Recheck normal DDS networking outside the sandbox.
- The five `prototype_*_flexion` targets are CPU test-sink values, not real robot or simulator
  commands. Asset-specific IK and collision safety remain server work.

## Next step

Run the server read-only audit, connect reconstruction once to the shared visual topic using a
checksummed video, then freeze the robot/hand asset and implement server IK and Isaac Sim.
