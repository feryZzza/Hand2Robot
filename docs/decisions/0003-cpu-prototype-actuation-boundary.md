[English](0003-cpu-prototype-actuation-boundary.md) | [简体中文](0003-cpu-prototype-actuation-boundary.zh-CN.md)

# ADR-0003: Keep the local target executable only by a CPU test sink

- Status: Accepted
- Date: 2026-08-08

## Context

The local integration needs a complete `HandObservation` to `RobotTarget` and `EpisodeRecord`
loop, but the server, simulator version, robot asset, hand asset, licenses, IK stack, and
collision model have not been audited. Naming unverified Panda/Allegro joints or pretending to
execute them would turn an integration scaffold into an unsafe implicit hardware contract.

## Decision

Select a five-flexion `cpu_prototype_v0.1` actuator manifest for local validation only. It maps
anatomical curl to bounded generic radians, maps the calibrated wrist into a checked workspace,
rate-limits targets, and fails closed on stale or invalid input. No physical robot or Isaac Sim
adapter may consume these generic names.

The server must replace the manifest with asset-specific names, limits, IK, collision checks,
and execution status after the read-only environment and asset audit. The shared message and
frame contracts remain unchanged.

## Consequences

The repository can verify transport, filtering, safety, degradation, and episode alignment now,
without claiming simulator or hardware control. A later asset integration requires an explicit
configuration/contract review rather than silently reinterpreting generic targets.
