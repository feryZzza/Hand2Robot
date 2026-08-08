# Shared interfaces

Status: accepted for M1, schema version `0.1.0`.

This file is the single source of truth for the four initial interfaces. ROS2 definitions live
in `ros2_ws/src/hand_msgs/msg/`. A field, unit, joint order, timestamp, frame, validity, or QoS
change requires a separate `contract:` commit with updated tests.

## Global rules

- `schema_version` must equal `0.1.0`. A consumer rejects an unsupported major version rather
  than guessing. Major versions break compatibility, minor versions add compatible semantics,
  and patch versions clarify behavior without changing the wire layout.
- `std_msgs/Header.stamp` is the source event time, not subscriber receipt time. For a camera it
  is capture time; for recorded input it is the recorded capture time; for synthetic input it is
  the generation time in the active ROS clock.
- Timestamps must increase strictly within one source session. A source restart resets validator
  state and emits a diagnostic before sequence numbering restarts.
- `sequence` starts at zero and increases by one per attempted source sample. A forward gap is a
  dropped-sample observation. A decrease without an explicit source reset is invalid.
- All numeric fields must be finite, including masked or invalid fields. Missing values use an
  explicit mask and zero-valued placeholder; NaN and infinity are contract violations.
- Coordinates use metres, angles use radians, durations in messages use milliseconds only where
  the field name ends in `_ms`, rates use hertz, and 2D image locations use pixels.
- Confidence and rates named `*_rate` lie in `[0, 1]`. Joint arrays that represent the hand have
  exactly 21 entries.

## Hand joint order

All 21-element hand arrays use this fixed anatomical order:

| Index | Name | Index | Name | Index | Name |
|---:|---|---:|---|---:|---|
| 0 | `wrist` | 7 | `index_dip` | 14 | `ring_pip` |
| 1 | `thumb_cmc` | 8 | `index_tip` | 15 | `ring_dip` |
| 2 | `thumb_mcp` | 9 | `middle_mcp` | 16 | `ring_tip` |
| 3 | `thumb_ip` | 10 | `middle_pip` | 17 | `little_mcp` |
| 4 | `thumb_tip` | 11 | `middle_dip` | 18 | `little_pip` |
| 5 | `index_mcp` | 12 | `middle_tip` | 19 | `little_dip` |
| 6 | `index_pip` | 13 | `ring_mcp` | 20 | `little_tip` |

Backends must convert their native order to this order at their boundary.

## `HandObservation`

ROS type: `hand_msgs/msg/HandObservation`.

| Field | Meaning and constraint |
|---|---|
| `header` | Capture/generation timestamp; `frame_id` is the coordinate frame of `joints_3d_m` |
| `schema_version` | Exact schema version |
| `sequence` | Monotonic source sample sequence |
| `handedness` | `UNKNOWN`, `LEFT`, or `RIGHT`; anatomical hand, not mirrored screen position |
| `source` | Stable adapter identifier such as `synthetic`, `recorded`, `camera_mediapipe`, or `hamer` |
| `joints_2d_px` | 21 image points; `x` right, `y` down, `z` must be zero |
| `joints_3d_m` | 21 3D points expressed in `header.frame_id`, in metres |
| `joints_3d_valid` | Whether the corresponding 3D point is measured/estimated and usable |
| `confidence` | Per-joint confidence in `[0, 1]` |
| `valid` | Source-level statement that the observation is eligible for downstream validation |

`valid=true` does not bypass validation. The validator still checks version, timestamp, finite
values, confidence, frame, sequence, and configured minimum confident-joint count.

## `RobotTarget`

ROS type: `hand_msgs/msg/RobotTarget`.

`header.frame_id` must be `robot_base` or a configured equivalent documented in
`docs/frames.md`; its timestamp is target creation time. `end_effector_pose` is expressed in that
frame. Finger names, target positions, and maximum velocities have identical lengths, and names
follow the selected asset manifest order. Positions and velocity limits use radians and
radians/second. End-effector velocity limits use metres/second and radians/second.

The status code distinguishes `OK`, `INPUT_INVALID`, `CALIBRATION_INVALID`, `IK_FAILED`,
`OUT_OF_WORKSPACE`, `JOINT_LIMIT`, and `STALE_INPUT`. An execution layer must reject
`valid=false`, an unknown status, a non-finite value, mismatched arrays, or a stale timestamp.
It must never indefinitely reuse an invalid target.

## `SystemStatus`

ROS type: `hand_msgs/msg/SystemStatus`. It is published at least once per second. Its header
timestamp is status creation time and `frame_id` is empty because the message is non-spatial.

States are `INIT`, `CALIBRATING`, `READY`, `RUNNING`, `DEGRADED`, and `ERROR`. Counters are
monotonic during one node process. `drop_rate` is `dropped_count / (received_count +
dropped_count)` and is zero when the denominator is zero. Latency is capture-to-status time on a
shared clock. `end_to_end_latency_valid=false` whenever clock domains are unknown or a negative
delta is observed; the accompanying numeric value is then a finite zero placeholder.
`last_error_code` is stable and machine-readable; `last_error_message` is diagnostic text.

## `EpisodeRecord`

ROS type: `hand_msgs/msg/EpisodeRecord`. Each record stores the original observation and action,
their independent timestamps, an episode ID, monotonic step index, task label, missing-value
masks, completion flag, success label, and failure reason. Alignment must not overwrite original
timestamps or silently fill missing values. `success` is meaningful only when
`episode_complete=true`; incomplete records keep it false.

Dataset train/validation/test splits operate on whole episodes, never adjacent frames from the
same episode.

## Initial topics and QoS

| Topic | Type | QoS | Purpose |
|---|---|---|---|
| `/hand/observation/raw` | `HandObservation` | sensor data, best effort, depth 5 | Adapter output before validation |
| `/hand/observation` | `HandObservation` | sensor data, best effort, depth 5 | Accepted observation |
| `/robot/target` | `RobotTarget` | reliable, volatile, keep last 1 | Latest safe target |
| `/system/status` | `SystemStatus` | reliable, volatile, keep last 10 | Health and counters, at least 1 Hz |
| `/episode/record` | `EpisodeRecord` | reliable, volatile, keep last 10 | Versioned aligned records |

Public-network transport must use an explicit VPN, Zenoh, WebSocket, or RPC gateway. Raw DDS is
not exposed to the public internet.
