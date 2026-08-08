# Architecture

Status: M2 local CPU baseline.

## Current data path

```text
synthetic_hand_publisher
    /hand/observation/raw  [HandObservation, SensorDataQoS]
                    |
                    v
hand_observation_validator
    |-- /hand/observation [accepted observations, SensorDataQoS]
    `-- /system/status    [counters/diagnostics, reliable >= 1 Hz]
                    |
                    v
hand_smoke_check / low_confidence_probe
```

`recorded_sequence_player` is an alternate publisher for `/hand/observation/raw`. It loads and
fully validates a versioned JSON sequence before advertising data, waits for subscriber
discovery, retains capture timestamps, and publishes each frame once. Downstream topics and the
validator are unchanged.

`input_pipeline.launch.py` selects `synthetic` or `recorded` through the `input_mode` launch
argument. Exactly one adapter runs, while validator node, raw/accepted/status topics, message
types, and QoS remain identical.

The validator republishes only accepted messages. Low confidence, unsupported schema, empty
frames/sources, non-finite values, invalid pixel `z`, non-monotonic time/sequence, invalid source
flags, and malformed arrays never reach `/hand/observation`.

## Package responsibilities

| Package | Responsibility | Runtime dependency on ROS2 |
|---|---|---|
| `hand_msgs` | Four versioned wire contracts | yes, interface generation only |
| `hand2robot_core` | Deterministic validation, counters, and source ordering | no |
| `hand_pipeline` | ROS conversion, publishers, validator node, status, smoke probes | yes |

`hand2robot_core` deliberately accepts plain immutable data. This keeps safety rules testable on
CPU without DDS, ROS graph startup, a camera, or a GPU.

## Current state behavior

- Before any input, the validator publishes `INIT`.
- A recent accepted observation produces `RUNNING` and is forwarded.
- A rejected or stale observation produces `DEGRADED` and is not forwarded.
- An unsupported schema produces `ERROR` until the validator process is restarted or a future
  explicit recovery transition is implemented.
- Counters remain monotonic for the lifetime of the validator node.

This is an input-boundary state subset, not the final system state machine. Calibration,
retargeting, IK, bridge, and execution states will extend it without weakening the current
validation boundary.

## Local smoke

`scripts/run_local_smoke.sh` keeps ROS logs under `local_data/tmp/smoke`, restricts discovery to
localhost, and uses a dedicated ROS domain. Its two checks are:

1. deterministic 30 Hz synthetic input reaches the accepted topic with valid latency and zero
   invalid samples;
2. low-confidence input is rejected, no valid sample is emitted, state becomes `DEGRADED`, and
   the stable error code is `low_confidence`.

ROS build/install/log output and smoke logs are local generated state and are excluded from Git.

The M3 bag check records `/hand/observation/raw`, not the already validated topic. Each replay
therefore crosses a new validator instance before its accepted sequences are counted. This tests
both serialization and deterministic validation rather than merely counting stored output.
