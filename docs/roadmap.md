# Hand2Robot roadmap

Status: `TODO`, `IN PROGRESS`, `VERIFIED`, or `BLOCKED`. A milestone is `VERIFIED` only when its
acceptance evidence is committed or referenced by a checksum-bearing manifest.

| Milestone | Status | Outcome | Acceptance gate |
|---|---|---|---|
| M0 Repository foundation | IN PROGRESS | Git, memory, workflow, skeleton | `make doctor`; baseline pushed to `main` and `work/local` |
| M1 Shared contracts | TODO | Messages, schemas, frames, units | Contract docs, samples, and validation tests agree |
| M2 Local CPU input loop | TODO | Synthetic/recorded input to diagnostics | Deterministic smoke test; malformed inputs diagnosed |
| M3 Capture and replay | TODO | Camera/MediaPipe/short rosbag | Input changes by config; two replays agree |
| M4 Calibration and retargeting | TODO | TF, scale, filtering, IK/safety | TF and limit tests; reachable IK target at least 95% |
| M5 Server simulation loop | TODO | Isaac Sim headless and ROS2 bridge | 1000 steps plus five-minute stable run |
| M6 Reliability | TODO | State machine, watchdog, faults | Six fault classes; 30-minute stable run |
| M7 Reconstruction and policy | TODO | HaMeR/MANO, LeRobot, BC/DP | Reproducible metrics and resumable experiment |
| M8 Release | TODO | Demo, report, resumes, release | Ten-minute smoke and final reproduction audit |

## Immediate build queue

1. Complete M0 and establish the `work/local` branch.
2. Define M1 as a dedicated `contract:` change.
3. Build the smallest M2 path: synthetic publisher → validator → system diagnostics.
4. Request and review the independent GPU-server audit before starting M5.
