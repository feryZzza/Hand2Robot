# CPU prototype retargeting

The local prototype turns a validated 21-joint `HandObservation` into a bounded
`RobotTarget` without depending on ROS2, NumPy, a simulator, or a GPU model. It is a safety and
integration target, not a claim that a physical robot or Isaac Sim asset has been commissioned.

## Geometry and scale

The wrist is the palm-local origin. The local x-axis points from little MCP to index MCP, the
y-axis is the orthogonalized wrist-to-middle-MCP direction, and z is `x cross y`. Coordinates
are divided by the index-to-little MCP distance and can then be rescaled to the configured
prototype palm width. Degenerate palms and missing required joints fail closed.

Left and right observations use the same anatomical joint order. Mapping between handedness is
named in every core result (`left_to_right_anatomical`, for example); the palm-normal reflection
is never hidden in a generic camera transform.

## Filtering and safe target policy

The One Euro filter operates on the calibrated wrist using capture timestamps. Non-increasing
timestamps are rejected. The output policy then applies these checks:

1. reject future or stale input;
2. reject frame/calibration mismatches and invalid palm geometry;
3. reject a wrist outside the configured 3D workspace;
4. limit accepted Cartesian and finger steps by elapsed source time;
5. emit one invalid `STALE_INPUT` target when the monotonic watchdog expires.

Live adapters enforce capture-to-target age. Offline replay preserves historical capture times,
so `prototype_pipeline.launch.py input_mode:=recorded enforce_capture_age:=false` disables only
that cross-clock age comparison; timestamp ordering, source-time rate limits, and the monotonic
arrival watchdog remain active.

The five `prototype_*_flexion` joints form the selected local CPU test manifest. They are
bounded curl proxies in radians, not commands for Panda, Allegro, or any other real asset. The
server adapter must replace this manifest with checked robot-specific names, limits, IK, and
collision validation before simulation or hardware execution.

Canonical configuration:
`configs/retargeting/cpu_prototype_v0.1.json`. Deterministic evidence can be reproduced with:

```bash
python3 scripts/evaluate_cpu_retargeting.py
make test-unit
```
