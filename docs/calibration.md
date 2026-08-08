# Calibration foundation

Status: M4 CPU foundation; no real camera calibration has been claimed.

`hand2robot_core.geometry.RigidTransform` implements the direction fixed in `docs/frames.md`:
`T_A_B` maps points from `B` into `A`. It validates finite translations and unit quaternions,
applies points, computes an inverse, and composes only matching frame chains.

`load_calibration` reads a versioned JSON record with the fields required by the frame contract.
It rejects unsupported schema, reversed expected frames, non-unit quaternions, timestamps without
a timezone, invalid residuals, and translations beyond a configured workspace bound. The bound
also catches common millimetre-as-metre mistakes.

`configs/calibration/synthetic_camera_to_robot_v0.1.json` is only a deterministic test fixture:
identity rotation plus translation `[0.5, 0.0, 0.8]` metres. It is not measured hardware data and
must never be used as a real robot calibration. Applied to the recorded wrist point
`[0.0, 0.06, 0.45]`, it yields `[0.5, 0.06, 1.25]` in `robot_base`.

The current boundary transforms all valid 3D points and returns zeros for masked points. It does
not yet produce `RobotTarget`; scale normalization, palm basis, filtering, workspace limits, and
IK remain separate downstream steps.
