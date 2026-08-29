#!/usr/bin/env python3
"""Measure Panda IK success over a workspace box, using Isaac Sim's Lula solver.

The roadmap's M5 gate asks for at least 95% IK success on a reachable test set,
and the CPU prototype's workspace box in `configs/retargeting/` is a guess that
was never checked against a real arm. This script does both jobs: it samples a
grid of end-effector positions inside a candidate box, solves IK for each, and
reports the success rate plus the axis-aligned box that actually succeeded.

Failures are reported, not hidden. A position that the solver rejects counts
against the rate rather than being retried with a different seed, because the
pipeline needs to know how often a target is unreachable.

    source scripts/server_sim_env.sh
    python scripts/evaluate_arm_ik.py --samples-per-axis 6 --json out.json
"""

from __future__ import annotations

import argparse
import json
import sys
from itertools import product
from pathlib import Path

DEFAULT_MANIFEST = Path("configs/assets/panda_allegro_v0.1.json")
DEFAULT_ASSET_ROOT = Path("/root/autodl-tmp/embodied/datasets/raw/assets")
DEFAULT_STAGE_DIR = Path("/root/autodl-tmp/embodied/cache/isaac/staged")
LULA_CONFIG_SUBPATH = (
    "extsDeprecated/isaacsim.robot_motion.motion_generation/motion_policy_configs/franka"
)
# Candidate box from configs/retargeting/cpu_prototype_v0.1.json, expressed in the
# arm's own base frame. The script reports what of this is actually reachable.
DEFAULT_BOX_MIN = (0.25, -0.40, 0.10)
DEFAULT_BOX_MAX = (0.65, 0.40, 0.70)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--asset-root", type=Path, default=DEFAULT_ASSET_ROOT)
    parser.add_argument("--stage-dir", type=Path, default=DEFAULT_STAGE_DIR)
    parser.add_argument("--samples-per-axis", type=int, default=6,
                        help="grid resolution per axis; total samples is the cube of this")
    parser.add_argument("--box-min", type=float, nargs=3, default=list(DEFAULT_BOX_MIN))
    parser.add_argument("--box-max", type=float, nargs=3, default=list(DEFAULT_BOX_MAX))
    parser.add_argument("--json", type=Path, default=None)
    parser.add_argument("--min-success-rate", type=float, default=0.95,
                        help="fail the run if the reachable-box success rate falls below this")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.samples_per_axis < 2:
        print("ERROR: --samples-per-axis must be at least 2", file=sys.stderr)
        return 2
    manifest = json.loads(args.manifest.read_text())
    arm = manifest["arm"]

    from isaacsim import SimulationApp

    app = SimulationApp({"headless": True})

    import numpy as np
    from isaacsim.asset.importer.urdf import URDFImporter, URDFImporterConfig
    from isaacsim.core.api import World
    from isaacsim.robot_motion.motion_generation import LulaKinematicsSolver

    isaac_root = Path(sys.modules["isaacsim"].__file__).parent
    lula_dir = isaac_root / LULA_CONFIG_SUBPATH
    descriptor = lula_dir / "rmpflow/robot_descriptor.yaml"
    lula_urdf = lula_dir / "lula_franka_gen.urdf"
    for path in (descriptor, lula_urdf):
        if not path.is_file():
            print(f"ERROR: Lula config missing at {path}", file=sys.stderr)
            app.close()
            return 1

    args.stage_dir.mkdir(parents=True, exist_ok=True)
    world = World(stage_units_in_meters=1.0)
    world.scene.add_default_ground_plane()

    arm_urdf = args.asset_root / arm["urdf_relative_path"]
    usd = URDFImporter(
        URDFImporterConfig(
            urdf_path=str(arm_urdf),
            usd_path=str(args.stage_dir),
            fix_base=True,
            merge_fixed_joints=False,
            allow_self_collision=False,
            joint_target_type="position",
        )
    ).import_urdf()
    world.stage.DefinePrim("/World/arm").GetReferences().AddReference(str(usd))
    world.reset()
    print(f"[import] arm staged from {arm_urdf.name}", flush=True)

    solver = LulaKinematicsSolver(
        robot_description_path=str(descriptor),
        urdf_path=str(lula_urdf),
    )
    ee_frame = arm["end_effector_frame"]
    frames = list(solver.get_all_frame_names())
    if ee_frame not in frames:
        print(f"ERROR: end effector {ee_frame!r} not among solver frames {frames}",
              file=sys.stderr)
        app.close()
        return 1
    print(f"[solver] Lula ready, {len(frames)} frames, target {ee_frame}", flush=True)

    lower = np.array(arm["joint_position_min_rad"], dtype=float)
    upper = np.array(arm["joint_position_max_rad"], dtype=float)
    seed = (lower + upper) / 2.0

    box_min = np.array(args.box_min, dtype=float)
    box_max = np.array(args.box_max, dtype=float)
    if not np.all(box_max > box_min):
        print("ERROR: --box-max must exceed --box-min on every axis", file=sys.stderr)
        app.close()
        return 2

    axes = [
        np.linspace(box_min[axis], box_max[axis], args.samples_per_axis)
        for axis in range(3)
    ]
    # Keep the tool pointing down, the orientation a top-down grasp would use.
    orientation = np.array([0.0, 1.0, 0.0, 0.0], dtype=float)

    attempted = 0
    succeeded = 0
    limit_violations = 0
    reached: list[tuple[float, float, float]] = []
    failed: list[tuple[float, float, float]] = []
    for position in product(*axes):
        target = np.array(position, dtype=float)
        attempted += 1
        solver.set_robot_base_pose(
            np.zeros(3, dtype=float), np.array([1.0, 0.0, 0.0, 0.0], dtype=float)
        )
        action, success = solver.compute_inverse_kinematics(
            frame_name=ee_frame,
            target_position=target,
            target_orientation=orientation,
            warm_start=seed,
        )
        point = tuple(float(value) for value in target)
        if not success:
            failed.append(point)
            continue
        # This Lula build returns a bare joint-position array rather than an
        # ArticulationAction, so accept either shape.
        raw = getattr(action, "joint_positions", action)
        joints = np.asarray(raw, dtype=float)[: lower.size]
        if not np.all(np.isfinite(joints)):
            failed.append(point)
            continue
        if np.any(joints < lower - 1e-6) or np.any(joints > upper + 1e-6):
            # A solution outside the manifest's limits is not usable, so it is a
            # failure for this pipeline even though the solver returned success.
            limit_violations += 1
            failed.append(point)
            continue
        succeeded += 1
        reached.append(point)

    rate = succeeded / attempted if attempted else 0.0
    report: dict[str, object] = {
        "manifest": str(args.manifest),
        "end_effector_frame": ee_frame,
        "samples_per_axis": args.samples_per_axis,
        "attempted": attempted,
        "succeeded": succeeded,
        "limit_violations": limit_violations,
        "success_rate": round(rate, 4),
        "candidate_box_min_m": [float(v) for v in box_min],
        "candidate_box_max_m": [float(v) for v in box_max],
    }
    report["failed_positions_m"] = [[round(v, 4) for v in point] for point in failed]
    if reached:
        array = np.array(reached, dtype=float)
        report["reachable_box_min_m"] = [round(float(v), 4) for v in array.min(axis=0)]
        report["reachable_box_max_m"] = [round(float(v), 4) for v in array.max(axis=0)]
    else:
        report["reachable_box_min_m"] = None
        report["reachable_box_max_m"] = None

    print(f"[ik] {succeeded}/{attempted} solved = {rate:.1%}, "
          f"{limit_violations} rejected for joint limits", flush=True)
    print(f"[box] reachable min={report['reachable_box_min_m']} "
          f"max={report['reachable_box_max_m']}", flush=True)

    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(f"[artifact] report written to {args.json}", flush=True)

    exit_code = 0
    if rate < args.min_success_rate:
        print(f"ERROR: IK success rate {rate:.1%} is below the required "
              f"{args.min_success_rate:.1%} over the candidate box",
              file=sys.stderr, flush=True)
        exit_code = 1
    else:
        print("Arm IK evaluation passed.", flush=True)

    sys.stdout.flush()
    sys.stderr.flush()
    app.close()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
