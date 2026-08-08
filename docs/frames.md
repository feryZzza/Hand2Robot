# Coordinate frames

Status: draft.

The planned frame vocabulary is `world`, `robot_base`, `camera`, `human_wrist`, `robot_ee`,
`robot_hand_base`, and per-finger frames. The next dedicated `contract:` change will define:

- parent/child direction for every transform;
- right-handed axis conventions;
- metres, radians, seconds, and pixel-coordinate conventions;
- static versus dynamic transforms;
- calibration provenance and validity period;
- left/right-hand mirroring rules;
- TF closure, unit, and transform-order tests.

Until that contract is accepted, code must not embed an assumed camera-to-robot transform.
