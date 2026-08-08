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

## Project records

- [Current project memory](docs/project_memory.md)
- [Roadmap and acceptance gates](docs/roadmap.md)
- [Git workflow](docs/git_workflow.md)
- [Interface contract](docs/interfaces.md)
- [Coordinate-frame contract](docs/frames.md)
- [Architecture decisions](docs/decisions/README.md)
- [Local/server handoff](docs/handoff/README.md)

The original Chinese execution guides and detailed eight-week checklist are retained under
`doc/` as project requirements.

## Scope boundaries

The local Ubuntu 22.04 machine handles Git, capture, lightweight ROS2, MediaPipe baselines,
short bags, and CPU smoke tests. The RTX 4090 server handles Isaac Sim, HaMeR/MANO, datasets,
training, long integration tests, and large artifacts. Both sides share the same messages,
frames, units, schema versions, and Git history.
