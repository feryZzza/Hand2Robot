# ADR-0001: Separate local interaction from server compute

- Status: Accepted
- Date: 2026-08-08

## Context

The local Ubuntu machine has ROS2 Humble and adequate CPU resources but only about 4.1 GiB free
on `/`, approximately 24 GiB free on `/home`, no working local GPU path, and no detected camera
at the initial audit. The project also requires Isaac Sim, HaMeR/MANO, datasets, and policy
training.

## Decision

Use the local machine for Git, SSH, capture, lightweight ROS2, synthetic/recorded input,
MediaPipe when feasible, short bags, calibration tests, reporting, and CPU smoke tests. Use the
RTX 4090 server's persistent data disk for simulation, large models, datasets, training, long
tests, caches, and checkpoints.

Connect the two sides through Git-tracked contracts and checksum-verified small data transfers.
Do not expose raw ROS2 DDS to the public internet.

## Consequences

The project remains usable when the camera or server is temporarily unavailable. More effort is
required to version messages, frames, schemas, and handoffs, but this also makes failures easier
to reproduce and provides stronger engineering evidence.
