# Recorded hand-sequence format

Status: format version `0.1.0`, used by the M3 CPU fixture.

The recorded adapter reads UTF-8 JSON with top-level metadata, deduplicated poses, and ordered
frames. The format is deliberately small and dependency-free so it can be validated before ROS2
starts.

Required metadata:

- `schema_version`: currently `0.1.0`;
- `frame_id`: coordinate frame of every 3D joint;
- `handedness`: `unknown`, `left`, or `right`;
- `source`: stable source/session name;
- `nominal_rate_hz`: finite positive acquisition rate;
- `poses`: one or more complete 21-joint observations;
- `frames`: ordered capture timestamps, sequences, pose references, and validity flags.

Each pose contains `joints_2d_px`, `joints_3d_m`, `joints_3d_valid`, and `confidence` using the
order and units in `docs/interfaces.md`. Frames retain absolute `capture_timestamp_ns`; playback
uses timestamp differences for scheduling but does not rewrite the timestamps. Consequently,
capture-to-now latency from an old offline sequence is not a live pipeline-latency benchmark.

The committed fixture is `recorded_hand_static_v0.1.json`: five static frames at 10 Hz, one pose,
sequences 0–4, all valid, and source `recorded_fixture`. Its manifest records the exact SHA256.
