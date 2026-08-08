[English](visual_input.md) | [简体中文](visual_input.zh-CN.md)

# Switchable camera and video input

## Purpose

The server reconstruction path can consume either a live camera or a video file without changing
its subscription. `visual_input_publisher` normalizes both sources to
`/visual/input/image_raw` as `sensor_msgs/msg/Image` with `bgr8` encoding and sensor-data QoS.

```text
camera device OR video file
          -> visual_input_publisher
          -> /visual/input/image_raw
          -> MediaPipe or HaMeR reconstruction (server adapter, pending)
          -> /hand/observation/raw
```

This raw-video mode is not the existing `recorded` mode. Raw video still needs reconstruction;
`recorded_sequence_player` already contains versioned 21-joint observations and bypasses RGB
decode and reconstruction.

## Launch commands

Build and source the workspace, then select exactly one mode:

```bash
source /opt/ros/humble/setup.bash
source ros2_ws/install/setup.bash

# Live camera
ros2 launch hand_pipeline visual_input.launch.py \
  visual_input_mode:=camera \
  camera_device:=0

# Video instead of a camera
ros2 launch hand_pipeline visual_input.launch.py \
  visual_input_mode:=video \
  video_path:=/persistent/data/hand_input.mp4 \
  loop_video:=false \
  playback_rate:=1.0
```

The launch argument uses ROS2 `choices`, so unsupported modes fail before node startup. Video mode
also fails closed when the path is empty, missing, or not a file. Camera mode fails if the device
cannot be opened.

## Parameters

| Launch argument | Default | Meaning |
|---|---:|---|
| `visual_input_mode` | `camera` | `camera` or `video` |
| `camera_device` | `0` | Non-negative OpenCV camera index |
| `video_path` | empty | Required readable file in video mode |
| `loop_video` | `false` | Seek to frame zero at end of video |
| `playback_rate` | `1.0` | Positive multiplier for the video's detected FPS |
| `frame_id` | `camera_optical_frame` | Optical frame used by the matching calibration |
| `output_topic` | `/visual/input/image_raw` | Stable reconstruction input topic |

`config/visual_input.yaml` also defines fallback FPS, subscriber discovery timeout, startup delay,
and the required subscriber count. The publisher waits for a subscriber before consuming camera
or video frames, which prevents a short video from finishing before the reconstruction node joins.

## Timestamp and calibration rules

Each decoded frame receives the active ROS time immediately after successful acquisition. The
timestamps therefore remain monotonic during looped playback but do not claim to be the original
media presentation timestamps. Use `recorded` input when historical capture timestamps must be
reproduced exactly.

The selected `frame_id` and calibration must describe the camera that produced the pixels. Do not
use the committed synthetic calibration with an arbitrary server video. A reconstruction adapter
must preserve the image stamp in `HandObservation` and distinguish its source, for example
`camera_hamer` versus `video_hamer`.

## Verification

Run the deterministic, camera-free video smoke:

```bash
make smoke-video-input
```

The script generates a tiny ignored MP4 under `local_data/tmp/`, launches video mode, and verifies
at least five `160x120` frames, `bgr8` encoding, the optical frame ID, payload size, and strictly
increasing timestamps. Project videos and datasets remain outside Git on the server's persistent
data disk.
