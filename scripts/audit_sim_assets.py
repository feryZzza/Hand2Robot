#!/usr/bin/env python3
"""Audit the Isaac Sim robot assets against the committed manifest.

The manifest in `configs/assets/` states joint names, limits and velocities. This
script imports both URDFs, loads them into a headless stage, and checks that the
simulated articulation actually agrees with what the manifest claims. It fails
loudly on any mismatch, so the manifest cannot silently drift from the assets.

The assets themselves live on the persistent data volume and are never committed,
so this script takes their root as an argument.

    source scripts/server_sim_env.sh
    python scripts/audit_sim_assets.py \
        --manifest configs/assets/panda_allegro_v0.1.json \
        --asset-root /root/autodl-tmp/embodied/datasets/raw/assets \
        --json out.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_ASSET_ROOT = Path("/root/autodl-tmp/embodied/datasets/raw/assets")
DEFAULT_STAGE_DIR = Path("/root/autodl-tmp/embodied/cache/isaac/staged")
LIMIT_TOLERANCE_RAD = 1e-4


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--asset-root", type=Path, default=DEFAULT_ASSET_ROOT)
    parser.add_argument("--stage-dir", type=Path, default=DEFAULT_STAGE_DIR)
    parser.add_argument("--steps", type=int, default=200,
                        help="bounded steps to run with both assets loaded")
    parser.add_argument("--json", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = json.loads(args.manifest.read_text())
    args.stage_dir.mkdir(parents=True, exist_ok=True)

    from isaacsim import SimulationApp

    app = SimulationApp({"headless": True})

    import numpy as np
    from isaacsim.asset.importer.urdf import URDFImporter, URDFImporterConfig
    from isaacsim.core.api import World
    from isaacsim.core.prims import Articulation

    failures: list[str] = []
    report: dict[str, object] = {"manifest": str(args.manifest), "parts": {}}

    world = World(stage_units_in_meters=1.0)
    world.scene.add_default_ground_plane()

    def convert(urdf: Path) -> str:
        config = URDFImporterConfig(
            urdf_path=str(urdf),
            usd_path=str(args.stage_dir),
            fix_base=True,
            merge_fixed_joints=False,
            allow_self_collision=False,
            joint_target_type="position",
        )
        return URDFImporter(config).import_urdf()

    loaded: dict[str, tuple[str, dict]] = {}
    for part in ("arm", "hand"):
        spec = manifest[part]
        urdf = args.asset_root / spec["urdf_relative_path"]
        if not urdf.is_file():
            failures.append(f"{part}: URDF missing at {urdf}")
            continue
        usd = convert(urdf)
        prim_path = f"/World/{part}"
        world.stage.DefinePrim(prim_path).GetReferences().AddReference(str(usd))
        loaded[part] = (prim_path, spec)
        print(f"[import] {part}: {urdf.name} -> {usd}", flush=True)

    if failures:
        for line in failures:
            print(f"ERROR: {line}", file=sys.stderr, flush=True)
        app.close()
        return 1

    world.reset()

    for part, (prim_path, spec) in loaded.items():
        articulation = Articulation(prim_paths_expr=prim_path)
        dof_names = list(articulation.dof_names or [])
        expected = list(spec["joint_names"])
        if part == "arm":
            expected = expected + list(spec.get("gripper_joint_names", []))

        missing = [n for n in expected if n not in dof_names]
        extra = [n for n in dof_names if n not in expected]
        part_report: dict[str, object] = {
            "prim_path": prim_path,
            "dof_count": len(dof_names),
            "expected_count": len(expected),
            "missing_from_stage": missing,
            "unexpected_on_stage": extra,
        }
        if missing:
            failures.append(f"{part}: manifest joints absent from stage: {missing}")
        if extra:
            failures.append(f"{part}: stage exposes joints absent from manifest: {extra}")

        lower, upper = articulation.get_dof_limits()[0].T if len(dof_names) else (None, None)
        limit_mismatches = []
        if lower is not None:
            declared_min = list(spec["joint_position_min_rad"])
            declared_max = list(spec["joint_position_max_rad"])
            for index, name in enumerate(spec["joint_names"]):
                if name not in dof_names:
                    continue
                dof = dof_names.index(name)
                got = (float(lower[dof]), float(upper[dof]))
                want = (declared_min[index], declared_max[index])
                if (abs(got[0] - want[0]) > LIMIT_TOLERANCE_RAD
                        or abs(got[1] - want[1]) > LIMIT_TOLERANCE_RAD):
                    limit_mismatches.append(
                        {"joint": name, "manifest": want, "stage": got})
        part_report["limit_mismatches"] = limit_mismatches
        if limit_mismatches:
            failures.append(
                f"{part}: {len(limit_mismatches)} joint limits disagree with the manifest")

        report["parts"][part] = part_report
        print(f"[joints] {part}: {len(dof_names)} DOF, "
              f"{len(missing)} missing, {len(extra)} unexpected, "
              f"{len(limit_mismatches)} limit mismatches", flush=True)

    for _ in range(args.steps):
        world.step(render=False)

    states = {}
    for part, (prim_path, _spec) in loaded.items():
        articulation = Articulation(prim_paths_expr=prim_path)
        positions = articulation.get_joint_positions()
        finite = bool(np.all(np.isfinite(positions)))
        states[part] = {"positions_finite": finite}
        if not finite:
            failures.append(f"{part}: joint positions became non-finite after stepping")
    report["steps"] = args.steps
    report["post_step_state"] = states
    report["passed"] = not failures
    report["failures"] = failures
    print(f"[run] {args.steps} steps with both assets, "
          f"finite state: {all(s['positions_finite'] for s in states.values())}", flush=True)

    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(f"[artifact] report written to {args.json}", flush=True)

    exit_code = 0
    if failures:
        for line in failures:
            print(f"ERROR: {line}", file=sys.stderr, flush=True)
        exit_code = 1
    else:
        print("Asset audit passed: manifest agrees with the simulated articulations.", flush=True)

    sys.stdout.flush()
    sys.stderr.flush()
    app.close()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
