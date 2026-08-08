# Hand2Robot roadmap

Status: `TODO`, `IN PROGRESS`, `VERIFIED`, or `BLOCKED`. A milestone is `VERIFIED` only when its
acceptance evidence is committed or referenced by a checksum-bearing manifest.

| Milestone | Status | Outcome | Acceptance gate |
|---|---|---|---|
| M0 Repository foundation | VERIFIED | Git, memory, workflow, skeleton | `make doctor`; baseline on `main`; `work/local` pushed from `d78e063` |
| M1 Shared contracts | VERIFIED | Messages, schemas, frames, units | Commit `3fb0f80`; 5 contract tests and rosidl build pass |
| M2 Local CPU input loop | VERIFIED | Synthetic input to diagnostics | Commit `82f9a5f`; 18 tests; normal and low-confidence smoke pass |
| M3 Capture and replay | IN PROGRESS | Recorded/camera input and short rosbag | Input changes by config; two replays agree |
| M4 Calibration and retargeting | TODO | TF, scale, filtering, IK/safety | TF and limit tests; reachable IK target at least 95% |
| M5 Server simulation loop | TODO | Isaac Sim headless and ROS2 bridge | 1000 steps plus five-minute stable run |
| M6 Reliability | TODO | State machine, watchdog, faults | Six fault classes; 30-minute stable run |
| M7 Reconstruction and policy | TODO | HaMeR/MANO, LeRobot, BC/DP | Reproducible metrics and resumable experiment |
| M8 Release | TODO | Demo, report, resumes, release | Ten-minute smoke and final reproduction audit |

## Immediate build queue

1. Add deterministic recorded input and verify two short rosbag replays.
2. Request and review the independent GPU-server audit before starting M5.
