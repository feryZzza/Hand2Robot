[English](README.md) | [简体中文](README.zh-CN.md)

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

The repository now contains a verified **local CPU prototype**. Synthetic or recorded
21-joint input crosses validation, calibration, palm/scale normalization, One Euro filtering,
workspace and velocity safety checks, `RobotTarget` publication, watchdog degradation, and
versioned `EpisodeRecord` persistence. The local machine intentionally contains no Isaac Sim,
large model, dataset, or training environment.

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
make smoke-video-input
make smoke-bag
make smoke-prototype
make smoke-prototype-recorded
make smoke-prototype-watchdog
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

The server visual-frame entry point independently switches between a camera and a video file while
keeping `/visual/input/image_raw` stable for MediaPipe or HaMeR:

```bash
ros2 launch hand_pipeline visual_input.launch.py visual_input_mode:=camera camera_device:=0
ros2 launch hand_pipeline visual_input.launch.py visual_input_mode:=video \
  video_path:=/persistent/data/hand_input.mp4
```

The reconstruction adapter is still pending; this node provides and verifies its shared RGB input
boundary. See [switchable visual input](docs/visual_input.md) for timestamps, calibration, looping,
and server storage rules.

`make smoke-bag` records the raw fixture into a temporary SQLite3 rosbag, confirms the bag has
exactly five messages, and replays it twice through fresh validator instances. Bags and logs stay
under ignored `local_data/tmp/` storage.

The three prototype targets verify the complete CPU path. The normal synthetic check writes and
validates a 20-step JSONL episode, recorded mode produces exactly sequences 0–4 through the same
downstream nodes, and the watchdog check stops its source and requires exactly one invalid
`STALE_INPUT` target. See [local reproduction](docs/reproduction.md) for expected output.

The runtime entry point for the initial prototype is:

```bash
source /opt/ros/humble/setup.bash
source ros2_ws/install/setup.bash
ros2 launch hand_pipeline prototype_pipeline.launch.py input_mode:=synthetic
```

`/robot/target` currently uses a five-flexion CPU test manifest. It is deliberately not a real
Panda/Allegro command interface; server-side asset selection, IK, collisions, and Isaac Sim
execution remain gated by the server audit.

## Project records

- [Current project memory](docs/project_memory.md)
- [Roadmap and acceptance gates](docs/roadmap.md)
- [Git workflow](docs/git_workflow.md)
- [Interface contract](docs/interfaces.md)
- [Coordinate-frame contract](docs/frames.md)
- [Current architecture](docs/architecture.md)
- [Recorded-sequence format](docs/recorded_sequence.md)
- [Calibration foundation](docs/calibration.md)
- [CPU retargeting and safety](docs/retargeting.md)
- [Switchable camera/video input](docs/visual_input.md)
- [Local reproduction](docs/reproduction.md)
- [Server bootstrap boundary](docs/server_bootstrap.md)
- [Measured server environment](docs/server_environment.md)
- [Architecture decisions](docs/decisions/README.md)
- [Local/server handoff](docs/handoff/README.md)

The original Chinese execution guides and detailed eight-week checklist are retained under
`doc/` as project requirements.

## Scope boundaries

The local Ubuntu 22.04 machine handles Git, capture, lightweight ROS2, MediaPipe baselines,
short bags, and CPU smoke tests. The RTX 4090 server handles Isaac Sim, HaMeR/MANO, datasets,
training, long integration tests, and large artifacts. Both sides share the same messages,
frames, units, schema versions, and Git history.
