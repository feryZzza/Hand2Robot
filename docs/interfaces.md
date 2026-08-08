# Shared interfaces

Status: draft, schema version `0.1.0`.

This file will be the single source of truth for `HandObservation`, `RobotTarget`,
`SystemStatus`, and `EpisodeRecord`. No implementation contract is frozen yet. The next
dedicated `contract:` change will define field types, shapes, units, ordering, validity rules,
timestamp semantics, QoS, failure behavior, and version migration policy.

Minimum required concepts from the project requirements:

| Interface | Required information |
|---|---|
| `HandObservation` | timestamp, handedness, 2D/3D joints, confidence, frame ID |
| `RobotTarget` | end-effector pose, finger joints, velocity limits, validity |
| `SystemStatus` | state, latency, drop rate, last error |
| `EpisodeRecord` | observation, action, task, success, timestamps, schema version |
