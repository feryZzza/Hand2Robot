[English](reproduction.md) | [简体中文](reproduction.zh-CN.md)

# Local CPU prototype reproduction

## Preconditions

- Ubuntu 22.04 with ROS2 Humble and `colcon` already installed;
- the repository checked out at a writable path with at least 15 GiB free on `/home`;
- no camera, GPU, model download, Python virtual environment, or server access is required.

Run the read-only environment check first:

```bash
make doctor
```

## Complete verification

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

Expected prototype evidence:

- 66 dependency-free unit/contract/documentation tests pass;
- all three ROS2 packages build;
- video mode publishes at least five valid `160x120` `bgr8` images with strict timestamps;
- synthetic mode produces 20 complete paired records with valid bounded targets;
- recorded mode produces exactly sequences 0–4 as five complete paired records;
- source interruption produces exactly one `STALE_INPUT`, `valid=false` target;
- each episode script prints its JSONL path and SHA256.

Generated logs, bags, and episodes remain below ignored `local_data/`. Only checksums, metrics,
configuration, and run manifests are committed.

## Manual launch

```bash
source /opt/ros/humble/setup.bash
source ros2_ws/install/setup.bash
export ROS_LOCALHOST_ONLY=1
ros2 launch hand_pipeline prototype_pipeline.launch.py \
  input_mode:=synthetic \
  expected_steps:=100 \
  episode_output_path:="$PWD/local_data/artifacts/manual_episode.jsonl"
```

The recorder opens output with exclusive creation and refuses to overwrite an existing episode.
Choose a new path for every run. For historical replay use `input_mode:=recorded` together with
`enforce_capture_age:=false`.

To verify server-style video input without a camera, run `make smoke-video-input`. It generates a
small temporary MP4 below ignored `local_data/tmp/`; it does not download or commit media.

## Sandbox transport warning

A network-isolated sandbox can make Fast DDS report `getifaddrs` or UDP socket warnings even
with `ROS_LOCALHOST_ONLY=1`. The verified local tests communicated through the available local
transport despite those warnings. Outside such a sandbox, treat a total lack of topics as a real
DDS configuration problem and inspect `ROS_DOMAIN_ID`, RMW selection, and localhost settings.
