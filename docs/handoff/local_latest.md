# Local handoff

- Updated: 2026-08-08 (Asia/Shanghai)
- Git base: `d78e063` (`main`, pushed to `origin/main`)
- Branch: `work/local` (pushed and tracking `origin/work/local`)
- Schema version: draft `0.1.0`
- Disk: `/` approximately 4.1 GiB free; `/home` approximately 24 GiB free
- Input: no camera detected; synthetic input is the planned baseline

## Completed

- Read the local guide, server guide, and full 29-page implementation checklist.
- Audited the initial workspace and core local commands.
- Established repository memory, ADR, handoff, Git workflow, and safety rules.
- Ran the read-only local doctor and pushed the verified M0 baseline to GitHub.
- Created the protected local integration path through `work/local`.

## Local verification

- ROS2 Humble and colcon commands are available.
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

Freeze the shared interface and frame contract, then build the local CPU synthetic smoke loop.
