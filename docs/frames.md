[English](frames.md) | [简体中文](frames.zh-CN.md)

# Coordinate frames

Status: accepted for M1, frame contract version `0.1.0`.

## Notation and axes

`T_A_B` maps coordinates expressed in frame `B` into frame `A`:

```text
p_A = T_A_B * p_B
T_A_C = T_A_B * T_B_C
```

In TF2 this is published with `A` as parent and `B` as child. Stored calibration keys use the
same `parent_frame`, `child_frame`, and `T_parent_child` direction; inverse transforms must be
computed explicitly, not inferred from a filename.

All 3D frames are right-handed and all translations use metres. Robot/world frames follow ROS
REP-103 body axes: `x` forward, `y` left, `z` up. Camera optical frames follow the ROS optical
convention: `x` right in the image, `y` down, `z` forward through the lens. Rotations are unit
quaternions in ROS messages and radians in configuration or calculations.

2D image coordinates are not TF frames. Their origin is the upper-left pixel centre, `x` grows
right, `y` grows down, and no implicit image mirroring is allowed.

## Frame tree

```text
world
└── robot_base
    ├── camera_optical_frame
    │   └── human_wrist
    └── robot_ee
        └── robot_hand_base
            └── <robot finger link frames>
```

| Frame | Parent | Transform | Owner |
|---|---|---|---|
| `world` | none | fixed simulation reference | simulator |
| `robot_base` | `world` | static per scene | simulator/asset config |
| `camera_optical_frame` | `robot_base` | static during a calibrated run | calibration |
| `human_wrist` | `camera_optical_frame` | dynamic observation | reconstruction adapter |
| `robot_ee` | `robot_base` | dynamic forward kinematics | robot/simulator |
| `robot_hand_base` | `robot_ee` | fixed by selected asset | robot manifest |
| finger link frames | `robot_hand_base` hierarchy | dynamic kinematics | robot/simulator |

The names above are canonical logical names. A robot-specific alias is allowed only through a
checked configuration mapping; interface messages continue to identify the actual configured
frame.

## Retargeting transform

Hand 3D points enter in `camera_optical_frame`. Calibration provides
`T_robot_base_camera_optical`. A direct wrist target is therefore derived in this order:

```text
p_robot_base = T_robot_base_camera_optical * p_camera_optical
```

Finger retargeting first builds an anatomical palm-local basis from the fixed joint order in
`docs/interfaces.md`, then removes global wrist translation/rotation and applies configured hand
scale. The resulting robot command is always expressed in `robot_base`.

## Handedness and mirroring

`LEFT` and `RIGHT` mean the person's anatomical hand. A camera preview mirror must be undone at
the input-adapter boundary. Mapping a left human hand to a right robot hand requires a named,
configured reflection/mapping step and a diagnostic annotation; it must never be hidden inside a
generic transform.

## Calibration record

Every camera-to-robot calibration file must contain:

```yaml
schema_version: 0.1.0
parent_frame: robot_base
child_frame: camera_optical_frame
translation_m: [x, y, z]
quaternion_xyzw: [x, y, z, w]
method: <method name>
source: <input/calibration asset>
created_at: <ISO-8601 timestamp>
residual_translation_m: <value>
residual_rotation_rad: <value>
```

Consumers reject a non-unit quaternion, non-finite value, unknown frame, reversed parent/child
pair, unsupported schema, or calibration outside its declared validity conditions.

The committed `synthetic_camera_to_robot_v0.1.json` file is a unit-test fixture, not a measured
camera calibration. Real calibration files must use a distinct source and measured residuals.

## Required tests

- identity, inverse, and composition order for `T_A_B`;
- TF chain closure within configured translation/rotation tolerances;
- metre/millimetre and radian/degree mistake detection;
- quaternion normalization and handed coordinate bases;
- left/right joint-label mapping;
- camera pixel convention independent of preview mirroring.
