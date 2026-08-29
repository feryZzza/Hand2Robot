#!/usr/bin/env python3
"""Bounded Isaac Sim headless check for the server acceptance gate.

This is the smallest honest proof that Isaac Sim runs on this server: bring up a
headless SimulationApp, add a ground plane and one dynamic cuboid, step the
physics a bounded number of times, and assert the resulting state is finite and
settled. It deliberately loads no robot asset. Asset-specific joint names, IK,
collision limits and the Franka/Allegro manifest remain a separate gate, so this
script must not be read as evidence for them.

Run it from the Isaac Sim environment, which is Python 3.12 and separate from the
Python 3.10 environments ROS2 depends on:

    source /root/autodl-tmp/embodied/config/sim_env.sh
    python scripts/run_sim_headless_check.py --steps 1000 --json out.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

CUBOID_START_HEIGHT_M = 1.0
CUBOID_SIZE_M = 0.2
# A settled cuboid rests with its centre half a side length above the plane.
SETTLED_TOLERANCE_M = 0.02


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--steps",
        type=int,
        default=1000,
        help="bounded number of physics steps to run (default: 1000)",
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=None,
        help="write measured metrics to this path as JSON",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.steps <= 0:
        print("ERROR: --steps must be positive", file=sys.stderr)
        return 2

    start = time.monotonic()
    from isaacsim import SimulationApp

    app = SimulationApp({"headless": True})
    startup_seconds = time.monotonic() - start
    print(f"[bootstrap] SimulationApp ready in {startup_seconds:.2f}s", flush=True)

    # These imports require a live SimulationApp, so they cannot move to module scope.
    import numpy as np
    from isaacsim.core.api import World
    from isaacsim.core.api.objects import DynamicCuboid

    world = World(stage_units_in_meters=1.0)
    world.scene.add_default_ground_plane()
    cuboid = world.scene.add(
        DynamicCuboid(
            prim_path="/World/check_cuboid",
            name="check_cuboid",
            position=np.array([0.0, 0.0, CUBOID_START_HEIGHT_M]),
            size=CUBOID_SIZE_M,
        )
    )
    world.reset()
    print("[scene] ground plane and one dynamic cuboid added", flush=True)

    step_start = time.monotonic()
    for _ in range(args.steps):
        world.step(render=False)
    step_seconds = time.monotonic() - step_start

    position, orientation = cuboid.get_world_pose()
    velocity = cuboid.get_linear_velocity()
    finite = bool(
        np.all(np.isfinite(position))
        and np.all(np.isfinite(orientation))
        and np.all(np.isfinite(velocity))
    )
    expected_height = CUBOID_SIZE_M / 2.0
    settled = bool(abs(float(position[2]) - expected_height) <= SETTLED_TOLERANCE_M)

    metrics = {
        "steps": args.steps,
        "startup_seconds": round(startup_seconds, 3),
        "step_seconds": round(step_seconds, 3),
        "steps_per_second": round(args.steps / step_seconds, 1),
        "final_height_m": round(float(position[2]), 5),
        "expected_height_m": expected_height,
        "state_finite": finite,
        "settled": settled,
    }
    print(f"[run] {args.steps} steps in {step_seconds:.2f}s "
          f"= {metrics['steps_per_second']} steps/s", flush=True)
    print(f"[state] height={metrics['final_height_m']} m "
          f"finite={finite} settled={settled}", flush=True)

    # Write before closing. Kit runs with fastShutdown, which can terminate the
    # process inside app.close() before any later statement executes.
    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n")
        print(f"[artifact] metrics written to {args.json}", flush=True)

    # Decide the verdict before app.close() for the same fastShutdown reason, then
    # flush it so a truncated shutdown cannot hide a failure.
    exit_code = 0
    if not finite:
        print("ERROR: simulation produced non-finite state", file=sys.stderr, flush=True)
        exit_code = 1
    elif not settled:
        print(
            f"ERROR: cuboid did not settle at {expected_height} m "
            f"(measured {metrics['final_height_m']} m)",
            file=sys.stderr,
            flush=True,
        )
        exit_code = 1
    else:
        print("Isaac Sim headless check passed.", flush=True)

    sys.stdout.flush()
    sys.stderr.flush()
    app.close()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
