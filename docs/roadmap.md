# Hand2Robot roadmap

Status: `TODO`, `IN PROGRESS`, `VERIFIED`, or `BLOCKED`. A milestone is `VERIFIED` only when its
acceptance evidence is committed or referenced by a checksum-bearing manifest.

| Milestone | Status | Outcome | Acceptance gate |
|---|---|---|---|
| M0 Repository foundation | VERIFIED | Git, memory, workflow, skeleton | `make doctor`; baseline on `main`; `work/local` pushed from `d78e063` |
| M1 Shared contracts | VERIFIED | Messages, schemas, frames, units | Commit `3fb0f80`; 5 contract tests and rosidl build pass |
| M2 Local CPU input loop | VERIFIED | Synthetic input to diagnostics | Commit `82f9a5f`; 18 tests; normal and low-confidence smoke pass |
| M3 Offline capture and replay | VERIFIED | Synthetic/recorded input and short rosbag | Commits `254e318`/`bbbdf27`/`8394368`; two exact replays |
| M3b Camera and MediaPipe | TODO | Live 21-joint input | Hardware appears; space-approved dependency; same raw topic |
| M4 Local calibration and retargeting | VERIFIED | TF, scale, filtering, CPU safety target | Commits `8612de6`/`6c7cdbf`; 58 tests; three prototype smokes |
| M5 Server IK and simulation loop | TODO | Asset IK, Isaac Sim headless, ROS2 bridge | Audited asset; 1000 steps plus five-minute stable run |
| M6 Reliability | IN PROGRESS | State machine, watchdog, faults | Local watchdog/six classes covered; 30-minute server run remains |
| M7 Reconstruction and policy | TODO | HaMeR/MANO, LeRobot, BC/DP | Reproducible metrics and resumable experiment |
| M8 Release | TODO | Demo, report, resumes, release | Ten-minute smoke and final reproduction audit |

## Immediate build queue

1. Run and review the read-only GPU-server audit before starting M5.
2. Freeze the server robot/hand asset manifest, license, joint order, limits, and IK solver.
3. Add live camera/MediaPipe only after a camera appears and dependency storage is approved.
