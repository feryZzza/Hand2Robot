#!/usr/bin/env python3
"""Drive Panda plus Allegro in Isaac Sim from the committed recorded sequence.

This is the M5 execution closed loop. It consumes the repository's recorded
21-joint observations, maps each one onto Allegro joint angles and a Panda
end-effector target, solves IK, commands the articulations, steps physics a
bounded number of times, and records what the simulation actually did.

Every command is checked before it reaches the articulation: joint values must be
finite and inside the manifest limits, and the end-effector target must be inside
the measured workspace box. A rejected sample is counted and the previous held
pose is kept, rather than letting an invalid command through. That matches the
fail-closed rule the CPU pipeline already follows.

    source scripts/server_sim_env.sh
    python scripts/run_sim_execution_check.py --steps 1000 --json out.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = PROJECT_ROOT / "configs/assets/panda_allegro_v0.1.json"
DEFAULT_RETARGET = PROJECT_ROOT / "configs/retargeting/panda_allegro_v0.1.json"
DEFAULT_SEQUENCE = (
    PROJECT_ROOT / "ros2_ws/src/hand_pipeline/examples/recorded_hand_static_v0.1.json"
)
DEFAULT_ASSET_ROOT = Path("/root/autodl-tmp/embodied/datasets/raw/assets")
DEFAULT_STAGE_DIR = Path("/root/autodl-tmp/embodied/cache/isaac/staged")
CORE_PATH = PROJECT_ROOT / "ros2_ws/src/hand2robot_core"
LULA_CONFIG_SUBPATH = (
    "extsDeprecated/isaacsim.robot_motion.motion_generation/motion_policy_configs/franka"
)
HANDEDNESS_NAME = {0: "unknown", 1: "left", 2: "right"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--retarget-config", type=Path, default=DEFAULT_RETARGET)
    parser.add_argument("--sequence", type=Path, default=DEFAULT_SEQUENCE)
    parser.add_argument("--asset-root", type=Path, default=DEFAULT_ASSET_ROOT)
    parser.add_argument("--stage-dir", type=Path, default=DEFAULT_STAGE_DIR)
    parser.add_argument("--steps", type=int, default=1000,
                        help="bounded physics steps to run")
    parser.add_argument("--steps-per-sample", type=int, default=20,
                        help="physics steps to hold each recorded observation")
    parser.add_argument("--json", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.steps <= 0 or args.steps_per_sample <= 0:
        print("ERROR: --steps and --steps-per-sample must be positive", file=sys.stderr)
        return 2

    sys.path.insert(0, str(CORE_PATH))
    from hand2robot_core.dexterous_hand import load_hand_mapping
    from hand2robot_core.palm import build_palm_frame, normalize_hand
    from hand2robot_core.recorded_sequence import load_recorded_sequence

    manifest = json.loads(args.manifest.read_text())
    retarget = json.loads(args.retarget_config.read_text())
    if retarget.get("schema_version") != "0.1.0":
        print(f"ERROR: unsupported retarget schema {retarget.get('schema_version')!r}",
              file=sys.stderr)
        return 2
    arm = manifest["arm"]
    hand_mapping = load_hand_mapping(
        args.manifest,
        flexion_span_rad=tuple(retarget["hand_mapping"]["flexion_span_rad"]),
        abduction_span_rad=tuple(retarget["hand_mapping"]["abduction_span_rad"]),
    )
    sequence = load_recorded_sequence(args.sequence)
    sequence_count = len(sequence.frames)

    from isaacsim import SimulationApp

    app = SimulationApp({"headless": True})

    import numpy as np
    from isaacsim.asset.importer.urdf import URDFImporter, URDFImporterConfig
    from isaacsim.core.api import World
    from isaacsim.core.prims import Articulation
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

    def stage(spec: dict, prim_path: str) -> None:
        # Drive gains come from the manifest, not importer defaults. The upstream
        # Allegro URDF declares no joint dynamics, so without them the position
        # targets are inert and the fingers spin past their limits.
        usd = URDFImporter(
            URDFImporterConfig(
                urdf_path=str(args.asset_root / spec["urdf_relative_path"]),
                usd_path=str(args.stage_dir),
                fix_base=True,
                merge_fixed_joints=False,
                allow_self_collision=False,
                joint_drive_type="force",
                joint_target_type="position",
                override_joint_stiffness=float(spec["drive_stiffness_nm_rad"]),
                override_joint_damping=float(spec["drive_damping_nm_s_rad"]),
            )
        ).import_urdf()
        world.stage.DefinePrim(prim_path).GetReferences().AddReference(str(usd))

    stage(arm, "/World/arm")
    stage(manifest["hand"], "/World/hand")
    world.reset()
    print("[stage] arm and hand loaded", flush=True)

    arm_articulation = Articulation(prim_paths_expr="/World/arm")
    hand_articulation = Articulation(prim_paths_expr="/World/hand")
    arm_dofs = list(arm_articulation.dof_names or [])
    hand_dofs = list(hand_articulation.dof_names or [])
    arm_index = [arm_dofs.index(name) for name in arm["joint_names"]]
    # Reads the final state back in mapping order, so an index into hand_measured
    # means the same joint as the same index into the mapping's limits.
    hand_index = [hand_dofs.index(name) for name in hand_mapping.joint_names]

    # The manifest splits the hand into joints that are safe under physics and the
    # thumb chain, which is not: see thumb_chain_defect. Physics-driven joints get
    # a drive; the thumb is pinned kinematically and excluded from the limit check
    # so a known asset defect does not masquerade as a pipeline failure.
    hand_spec = manifest["hand"]
    physics_names = list(hand_spec["physics_driven_joint_names"])
    kinematic_names = list(hand_spec["kinematic_only_joint_names"])
    physics_dof = [hand_dofs.index(name) for name in physics_names]
    kinematic_dof = [hand_dofs.index(name) for name in kinematic_names]
    physics_slots = [hand_mapping.joint_index(name) for name in physics_names]
    kinematic_slots = [hand_mapping.joint_index(name) for name in kinematic_names]

    arm_articulation.set_gains(
        kps=np.full((1, len(arm_dofs)), float(arm["drive_stiffness_nm_rad"])),
        kds=np.full((1, len(arm_dofs)), float(arm["drive_damping_nm_s_rad"])),
    )
    hand_gains_kp = np.zeros((1, len(hand_dofs)))
    hand_gains_kd = np.zeros((1, len(hand_dofs)))
    hand_gains_kp[0, physics_dof] = float(hand_spec["drive_stiffness_nm_rad"])
    hand_gains_kd[0, physics_dof] = float(hand_spec["drive_damping_nm_s_rad"])
    hand_articulation.set_gains(kps=hand_gains_kp, kds=hand_gains_kd)
    print(f"[drive] arm {len(arm_index)} joints, hand {len(physics_dof)} physics-driven, "
          f"{len(kinematic_dof)} kinematic-only", flush=True)

    def pin_thumb_chain(values) -> None:
        """Hold the defective thumb chain at ``values`` with zero velocity.

        Writing state directly is what makes this chain kinematic rather than
        dynamic. Only the thumb DOFs are written; the finger joints keep whatever
        the solver produced, so their readings stay a genuine physics result.
        """

        positions = hand_articulation.get_joint_positions()[0].copy()
        velocities = hand_articulation.get_joint_velocities()[0].copy()
        positions[kinematic_dof] = values
        velocities[kinematic_dof] = 0.0
        hand_articulation.set_joint_positions(positions[None, :])
        hand_articulation.set_joint_velocities(velocities[None, :])

    solver = LulaKinematicsSolver(
        robot_description_path=str(descriptor), urdf_path=str(lula_urdf)
    )
    ee_frame = arm["end_effector_frame"]
    arm_lower = np.array(arm["joint_position_min_rad"], dtype=float)
    arm_upper = np.array(arm["joint_position_max_rad"], dtype=float)
    warm_start = (arm_lower + arm_upper) / 2.0
    box_min = np.array(retarget["workspace_min_m"], dtype=float)
    box_max = np.array(retarget["workspace_max_m"], dtype=float)
    # A top-down tool orientation, matching what the IK evaluation measured.
    orientation = np.array([0.0, 1.0, 0.0, 0.0], dtype=float)

    accepted = 0
    rejected: dict[str, int] = {}
    def reject(reason: str) -> None:
        rejected[reason] = rejected.get(reason, 0) + 1

    held_arm = warm_start.copy()
    held_hand = np.array(hand_mapping.neutral_positions_rad(), dtype=float)
    # Seed a legal pose before stepping. Straight out of the importer three thumb
    # joints already sit outside their limits.
    seed_hand = hand_articulation.get_joint_positions()[0].copy()
    seed_hand[physics_dof] = held_hand[physics_slots]
    seed_hand[kinematic_dof] = held_hand[kinematic_slots]
    hand_articulation.set_joint_positions(seed_hand[None, :])
    hand_articulation.set_joint_velocities(np.zeros((1, len(hand_dofs))))
    hand_articulation.set_joint_position_targets(seed_hand[None, :])
    seed_arm = arm_articulation.get_joint_positions()[0].copy()
    seed_arm[arm_index] = held_arm
    arm_articulation.set_joint_positions(seed_arm[None, :])
    arm_articulation.set_joint_velocities(np.zeros((1, len(arm_dofs))))
    arm_articulation.set_joint_position_targets(seed_arm[None, :])
    clamped_samples = 0
    steps_done = 0
    sample_index = 0

    while steps_done < args.steps:
        observation = sequence.observation_at(sample_index % sequence_count)
        sample_index += 1
        handedness = HANDEDNESS_NAME.get(observation.handedness, "unknown")

        try:
            frame = build_palm_frame(
                observation.joints_3d_m,
                handedness=handedness,
                minimum_palm_width_m=retarget["minimum_palm_width_m"],
            )
            points = normalize_hand(
                observation.joints_3d_m,
                handedness=handedness,
                target_handedness=retarget["target_handedness"],
                minimum_palm_width_m=retarget["minimum_palm_width_m"],
            ).points_at_scale(retarget["target_palm_width_m"])
            hand_positions = hand_mapping.positions_from_human(points, frame)
        except (IndexError, TypeError, ValueError) as error:
            reject(f"input_invalid: {type(error).__name__}")
            for _ in range(args.steps_per_sample):
                world.step(render=False)
                steps_done += 1
                if steps_done >= args.steps:
                    break
            continue

        hand_command, touched = hand_mapping.clamp(hand_positions)
        clamped_samples += int(touched)

        # Place the tool at the centre of the measured box, offset by the wrist's
        # normalized position. The recorded fixture is a static hand, so this is a
        # bounded excursion inside the verified workspace rather than a full
        # camera-to-robot calibration, which stays a separate gate.
        centre = (box_min + box_max) / 2.0
        wrist = np.array(points[0], dtype=float)
        target = np.clip(centre + wrist, box_min, box_max)
        if not np.all(np.isfinite(target)):
            reject("target_not_finite")
            target = centre

        action, ok = solver.compute_inverse_kinematics(
            frame_name=ee_frame,
            target_position=target,
            target_orientation=orientation,
            warm_start=warm_start,
        )
        if not ok:
            reject("ik_failed")
        else:
            raw = getattr(action, "joint_positions", action)
            solution = np.asarray(raw, dtype=float)[: arm_lower.size]
            if not np.all(np.isfinite(solution)):
                reject("ik_not_finite")
            elif np.any(solution < arm_lower - 1e-6) or np.any(solution > arm_upper + 1e-6):
                reject("joint_limit")
            else:
                held_arm = solution
                held_hand = np.array(hand_command, dtype=float)
                accepted += 1

        arm_target = arm_articulation.get_joint_positions()[0].copy()
        arm_target[arm_index] = held_arm
        arm_articulation.set_joint_position_targets(arm_target[None, :])

        # Physics-driven finger joints get a position target and are left to the
        # solver, so their reported state is a real dynamic result.
        hand_target = hand_articulation.get_joint_positions()[0].copy()
        hand_target[physics_dof] = held_hand[physics_slots]
        hand_target[kinematic_dof] = held_hand[kinematic_slots]
        hand_articulation.set_joint_position_targets(hand_target[None, :])
        pin_thumb_chain(held_hand[kinematic_slots])

        for _ in range(args.steps_per_sample):
            world.step(render=False)
            steps_done += 1
            # Re-pin every step: a single write before the loop is undone by the
            # first solver iteration on this chain.
            pin_thumb_chain(held_hand[kinematic_slots])
            if steps_done >= args.steps:
                break

    arm_final = arm_articulation.get_joint_positions()[0]
    hand_final = hand_articulation.get_joint_positions()[0]
    arm_measured = np.asarray(arm_final, dtype=float)[arm_index]
    hand_measured = np.asarray(hand_final, dtype=float)[hand_index]
    finite = bool(np.all(np.isfinite(arm_final)) and np.all(np.isfinite(hand_final)))
    arm_in_limits = bool(
        np.all(arm_measured >= arm_lower - 1e-3) and np.all(arm_measured <= arm_upper + 1e-3)
    )
    hand_low = np.array(hand_mapping.position_min_rad, dtype=float)
    hand_high = np.array(hand_mapping.position_max_rad, dtype=float)
    # Judge the physics-driven joints, which is the claim this check makes. The
    # thumb chain is reported separately because it is pinned, not simulated.
    hand_in_limits = bool(
        np.all(hand_measured[physics_slots] >= hand_low[physics_slots] - 1e-3)
        and np.all(hand_measured[physics_slots] <= hand_high[physics_slots] + 1e-3)
    )
    thumb_in_limits = bool(
        np.all(hand_measured[kinematic_slots] >= hand_low[kinematic_slots] - 1e-3)
        and np.all(hand_measured[kinematic_slots] <= hand_high[kinematic_slots] + 1e-3)
    )

    report = {
        "steps": steps_done,
        "steps_per_sample": args.steps_per_sample,
        "samples_consumed": sample_index,
        "sequence_count": sequence_count,
        "accepted_samples": accepted,
        "rejected_samples": rejected,
        "hand_clamped_samples": clamped_samples,
        "state_finite": finite,
        "arm_within_limits": arm_in_limits,
        "hand_physics_joints_within_limits": hand_in_limits,
        "hand_thumb_chain_within_limits": thumb_in_limits,
        "hand_physics_driven_joints": physics_names,
        "hand_kinematic_only_joints": kinematic_names,
        "arm_final_rad": [round(float(v), 5) for v in arm_measured],
        "hand_final_rad": [round(float(v), 5) for v in hand_measured],
        "workspace_min_m": [float(v) for v in box_min],
        "workspace_max_m": [float(v) for v in box_max],
    }
    print(f"[run] {steps_done} steps, {sample_index} samples, "
          f"{accepted} accepted, {sum(rejected.values())} rejected {rejected or '{}'}",
          flush=True)
    print(f"[state] finite={finite} arm_in_limits={arm_in_limits} "
          f"hand_physics_in_limits={hand_in_limits} "
          f"thumb_pinned_in_limits={thumb_in_limits} "
          f"clamped_samples={clamped_samples}", flush=True)

    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(f"[artifact] report written to {args.json}", flush=True)

    failures = []
    if not finite:
        failures.append("simulation state became non-finite")
    if not arm_in_limits:
        failures.append("arm left its manifest joint limits")
    if not hand_in_limits:
        failures.append("physics-driven hand joints left their manifest limits")
    if not thumb_in_limits:
        failures.append("pinned thumb chain left its manifest limits")
    if accepted == 0:
        failures.append("no recorded sample produced a commanded pose")

    exit_code = 0
    for line in failures:
        print(f"ERROR: {line}", file=sys.stderr, flush=True)
        exit_code = 1
    if exit_code == 0:
        print("Isaac Sim execution check passed.", flush=True)

    sys.stdout.flush()
    sys.stderr.flush()
    app.close()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
