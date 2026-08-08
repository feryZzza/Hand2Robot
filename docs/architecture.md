[English](architecture.md) | [简体中文](architecture.zh-CN.md)

# Architecture

Status: verified local CPU prototype; server execution boundary pending.

## Current data path

```text
synthetic_hand_publisher OR recorded_sequence_player
    /hand/observation/raw  [HandObservation, best effort]
                    |
                    v
hand_observation_validator ----------------> /system/status
    /hand/observation     [accepted only]          |
                    |                              |
                    v                              |
safe_retargeter                                    |
  calibration -> palm/scale -> One Euro -> safety |
    /robot/target [reliable, keep last 1]          |
                    |                              |
                    +---------------+--------------+
                                    v
                            episode_recorder
                 /episode/record + ignored JSONL artifact
```

`input_pipeline.launch.py` runs only an adapter and the validator. It selects `synthetic` or
`recorded` through `input_mode`; exactly one adapter runs and downstream topics do not change.

`prototype_pipeline.launch.py` preserves that adapter boundary and adds the safe retargeter and
optional episode recorder. Live mode enforces event age against the ROS clock. Recorded mode
must explicitly set `enforce_capture_age:=false` because it preserves historical event times;
ordering, source-time rate limits, and the monotonic arrival watchdog stay enabled.

The validator republishes only accepted messages. Low confidence, unsupported schema, empty
frames/sources, non-finite values, invalid pixel z, non-monotonic time/sequence, invalid source
flags, and malformed arrays never reach `/hand/observation`.

## Prepared server visual path

```text
camera device OR video file
    visual_input_publisher -> /visual/input/image_raw [sensor_msgs/Image, bgr8]
                                      |
                                      v
                    MediaPipe or HaMeR reconstruction [pending]
                                      |
                                      v
                         /hand/observation/raw
```

`visual_input.launch.py` selects `camera` or `video` through `visual_input_mode`; both publish the
same image contract, so the server reconstruction adapter does not branch on transport. Video
mode validates its file before opening, follows detected FPS and `playback_rate`, optionally
loops, and waits for a subscriber before decoding. This prepared boundary does not pretend that
MediaPipe or HaMeR reconstruction has already been implemented.

## Package responsibilities

| Package | Responsibility | Runtime dependency on ROS2 |
|---|---|---|
| `hand_msgs` | Four versioned wire contracts | yes, interface generation only |
| `hand2robot_core` | Validation, SE(3), palm scale, filters, retargeting safety, episode alignment | no |
| `hand_pipeline` | ROS conversion, adapters, validator, retargeter, recorder, probes | yes |

`hand2robot_core` accepts plain immutable data. Safety and alignment therefore remain testable
without DDS, ROS graph startup, a camera, NumPy, or a GPU.

## State and safety behavior

- Before any input, the validator publishes `INIT`.
- A recent accepted observation produces `RUNNING` and is forwarded.
- A rejected or stale observation produces `DEGRADED` and is not forwarded.
- An unsupported schema produces `ERROR` for that validator process.
- Counters remain monotonic for the lifetime of the validator node.
- The retargeter publishes only bounded targets as valid.
- After input stops, its watchdog publishes one invalid `STALE_INPUT` target and does not
  indefinitely repeat the last command.

This is a local state subset. Server-side IK, collision state, ROS2 Bridge health, and simulator
recovery must extend it without weakening the validation or stale-command boundaries.

## Input and evidence paths

The visual adapter provides a stable raw RGB boundary for live cameras and server-resident video
files. The recorded adapter loads and fully validates a versioned JSON sequence before publishing,
waits for discovery, retains capture timestamps, and publishes each frame once. The M3 bag check
records `/hand/observation/raw` and crosses a fresh validator on each replay, testing
serialization plus deterministic validation rather than merely counting stored output.

The local prototype smokes cover continuous synthetic input, exact five-frame recorded input,
complete episode persistence, and source interruption. ROS build products, JSONL episodes, bags,
and logs remain below ignored local storage; tracked run manifests contain hashes and summaries.

## Safety boundary and current non-goals

The selected local actuator manifest contains one bounded curl proxy for each finger and a
calibrated wrist pose. Workspace and rate limits are enforced before `valid=true`. It exists to
exercise contracts, transport, degradation, and recording on CPU. It is not compatible with a
physical robot or simulator asset by name.

The next execution layer must load a checked robot manifest, solve IK, enforce actual joint and
collision limits, reject stale or unknown targets, and report its state. Isaac Sim,
Panda/Allegro, HaMeR/MANO, and policy training are not silently emulated by this local prototype.
