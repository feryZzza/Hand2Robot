# Local handoff

- Updated: 2026-08-08 (Asia/Shanghai)
- Git commits: `8612de6` (core), `6c7cdbf` (ROS loop), `adc89a7` (safety), `e6883b1` (build)
- Branch: `work/local` (pushed and tracking `origin/work/local`)
- Schema version: accepted `0.1.0`
- Disk: `/` approximately 4.1 GiB free; `/home` approximately 24 GiB free
- Input: synthetic and recorded modes verified through one launch; no camera detected

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

## Local verification

- ROS2 Humble and colcon commands are available.
- Fifty-eight unit/contract tests pass; all three ROS2 packages build.
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

No external upload. The tracked fixture SHA256 is
`73dac677df09df1ab6d82b78710911025cf8b34d0c4e84bc34f42c185802c725`;
the 37,876-byte local bag and its hashes are recorded in the M3 run manifest.

## Server action required

Complete the read-only server audit and populate `server_latest.md` before large installation or
simulation work.

## Known issues

- Low root-partition headroom prohibits local dependency installation.
- Camera availability is unresolved but does not block synthetic input.
- The sandbox blocks UDP interface enumeration and emits Fast DDS warnings; local ROS transport
  still passed. Recheck normal DDS networking outside the sandbox.
- The five `prototype_*_flexion` targets are CPU test-sink values, not real robot or simulator
  commands. Asset-specific IK and collision safety remain server work.

## Next step

Run the server read-only audit, freeze one robot/hand asset manifest, then implement server IK
and Isaac Sim execution against the unchanged shared contracts.
