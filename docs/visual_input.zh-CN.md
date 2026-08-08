[English](visual_input.md) | [简体中文](visual_input.zh-CN.md)

# 可切换的摄像头与视频输入

## 用途

服务器重建链路可以在不改变订阅关系的情况下，使用实时摄像头或视频文件。
`visual_input_publisher` 会把两种来源统一为 `/visual/input/image_raw`，消息类型为
`sensor_msgs/msg/Image`，编码为 `bgr8`，采用 sensor-data QoS。

```text
摄像头设备 或 视频文件
          -> visual_input_publisher
          -> /visual/input/image_raw
          -> MediaPipe 或 HaMeR 重建（服务器适配器，待完成）
          -> /hand/observation/raw
```

该原始视频模式不同于现有 `recorded` 模式。原始视频仍需经过重建；
`recorded_sequence_player` 已经包含版本化的 21 关节观测，会绕过 RGB 解码和重建。

## 启动命令

构建并加载工作区，然后只选择一种模式：

```bash
source /opt/ros/humble/setup.bash
source ros2_ws/install/setup.bash

# 实时摄像头
ros2 launch hand_pipeline visual_input.launch.py \
  visual_input_mode:=camera \
  camera_device:=0

# 使用视频代替摄像头
ros2 launch hand_pipeline visual_input.launch.py \
  visual_input_mode:=video \
  video_path:=/persistent/data/hand_input.mp4 \
  loop_video:=false \
  playback_rate:=1.0
```

启动参数使用 ROS2 `choices`，因此不支持的模式会在节点启动前失败。视频模式在路径为
空、缺失或不是文件时也会关闭失败；摄像头模式在无法打开设备时失败。

## 参数

| 启动参数 | 默认值 | 含义 |
|---|---:|---|
| `visual_input_mode` | `camera` | `camera` 或 `video` |
| `camera_device` | `0` | 非负的 OpenCV 摄像头索引 |
| `video_path` | 空 | 视频模式下必填的可读文件 |
| `loop_video` | `false` | 视频结束时跳回第零帧 |
| `playback_rate` | `1.0` | 视频检测 FPS 的正数倍率 |
| `frame_id` | `camera_optical_frame` | 与对应标定一致的光学坐标系 |
| `output_topic` | `/visual/input/image_raw` | 稳定的重建输入 topic |

`config/visual_input.yaml` 还定义备用 FPS、订阅者发现超时、启动延迟和所需订阅者数量。
发布器会等待订阅者后再消耗摄像头或视频帧，避免短视频在重建节点加入前就播放完毕。

## 时间戳与标定规则

每个解码帧在成功采集后立即获得当前 ROS 时间，因此循环播放时仍能保持时间戳单调，
但它不声称还原原始媒体的显示时间戳。需要精确复现历史采集时间时应使用 `recorded`
输入。

所选 `frame_id` 和标定必须描述产生这些像素的摄像头。不得把仓库内的合成标定用于
任意服务器视频。重建适配器必须把图像时间戳保留到 `HandObservation` 中，并区分来源，
例如使用 `camera_hamer` 和 `video_hamer`。

## 验证

运行不需要摄像头的确定性视频 smoke：

```bash
make smoke-video-input
```

脚本会在 `local_data/tmp/` 下生成一个被忽略的小型 MP4，启动视频模式，并验证至少
五帧 `160x120` 图像、`bgr8` 编码、光学坐标系 ID、载荷大小和严格递增时间戳。项目
视频与数据集继续保存在服务器持久化数据盘，不进入 Git。
