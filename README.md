# Hand2Robot

Hand2Robot is an eight-week embodied-AI engineering project that converts visual hand
observations into safe robot-arm and dexterous-hand targets, validates them in simulation,
and records reproducible training episodes.

```text
camera / recording / synthetic input
                 -> hand reconstruction
                 -> calibration and retargeting
                 -> IK and safety limits
                 -> ROS2 and Isaac Sim
                 -> versioned episode data
```

## Current status

The repository is in milestone M0: project bootstrap and contract definition. The local
machine intentionally contains no Isaac Sim installation, large model, dataset, or training
environment.

Start with:

```bash
git clone https://github.com/feryZzza/Hand2Robot.git
cd Hand2Robot
make doctor
```

`make doctor` is read-only. It reports local disk limits, ROS2 availability, repository
state, and connected camera devices.

Build and verify the current CPU-only baseline:

```bash
make test-unit
make build-ros
make smoke-local
make smoke-recorded
make smoke-bag
```

The smoke target launches a deterministic 21-joint source and validator, verifies accepted
observations and `RUNNING` status, then injects low-confidence observations and verifies
`DEGRADED` diagnostics. It uses localhost-only ROS2 domain 72 by default; override it with
`HAND2ROBOT_ROS_DOMAIN_ID` if that domain is already in use.

`make smoke-recorded` uses the committed five-frame fixture and verifies exact sequence numbers,
source, accepted count, invalid count, and dropped count through the same validator.

The normal runtime entry point switches adapters without changing downstream nodes:

```bash
ros2 launch hand_pipeline input_pipeline.launch.py input_mode:=synthetic
ros2 launch hand_pipeline input_pipeline.launch.py input_mode:=recorded
```

`make smoke-bag` records the raw fixture into a temporary SQLite3 rosbag, confirms the bag has
exactly five messages, and replays it twice through fresh validator instances. Bags and logs stay
under ignored `local_data/tmp/` storage.

## Project records

- [Current project memory](docs/project_memory.md)
- [Roadmap and acceptance gates](docs/roadmap.md)
- [Git workflow](docs/git_workflow.md)
- [Interface contract](docs/interfaces.md)
- [Coordinate-frame contract](docs/frames.md)
- [Current architecture](docs/architecture.md)
- [Recorded-sequence format](docs/recorded_sequence.md)
- [Calibration foundation](docs/calibration.md)
- [Architecture decisions](docs/decisions/README.md)
- [Local/server handoff](docs/handoff/README.md)

The original Chinese execution guides and detailed eight-week checklist are retained under
`doc/` as project requirements.

## Scope boundaries

The local Ubuntu 22.04 machine handles Git, capture, lightweight ROS2, MediaPipe baselines,
short bags, and CPU smoke tests. The RTX 4090 server handles Isaac Sim, HaMeR/MANO, datasets,
training, long integration tests, and large artifacts. Both sides share the same messages,
frames, units, schema versions, and Git history.
