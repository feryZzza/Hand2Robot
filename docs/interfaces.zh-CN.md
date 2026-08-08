[English](interfaces.md) | [简体中文](interfaces.zh-CN.md)

# 共享接口

状态：M1 已接受，schema 版本 `0.1.0`。

本文件是四个初始接口的唯一事实来源。ROS2 定义位于 `ros2_ws/src/hand_msgs/msg/`。
字段、单位、关节顺序、时间戳、坐标系、有效性或 QoS 的修改，必须使用独立的
`contract:` 提交并更新测试。

## 全局规则

- `schema_version` 必须等于 `0.1.0`。消费者应拒绝不支持的主版本，而不是猜测含义。
  主版本表示不兼容修改，次版本增加兼容语义，补丁版本在不改变线布局的前提下澄清
  行为。
- `std_msgs/Header.stamp` 是源事件时间，不是订阅者接收时间。摄像头使用采集时间，
  录制输入使用录制时的采集时间，合成输入使用活动 ROS 时钟中的生成时间。
- 在一个数据源会话内，时间戳必须严格递增。数据源重启会重置校验器状态，并在序列
  号重新开始前产生诊断。
- `sequence` 从零开始，每次尝试产生源样本时加一。向前跳跃表示观测到样本丢失；
  未显式重置数据源时减少序列号属于无效行为。
- 所有数值字段都必须是有限值，包括被 mask 或无效的字段。缺失值使用显式 mask 和
  零值占位；NaN 与无穷大违反契约。
- 坐标使用米，角度使用弧度；只有名称以 `_ms` 结尾的消息字段使用毫秒；频率使用
  赫兹；二维图像位置使用像素。
- 置信度和名为 `*_rate` 的比率位于 `[0, 1]`。表示手部的关节数组必须恰好有 21 项。

## 手部关节顺序

所有 21 项手部数组使用以下固定解剖顺序：

| 索引 | 名称 | 索引 | 名称 | 索引 | 名称 |
|---:|---|---:|---|---:|---|
| 0 | `wrist` | 7 | `index_dip` | 14 | `ring_pip` |
| 1 | `thumb_cmc` | 8 | `index_tip` | 15 | `ring_dip` |
| 2 | `thumb_mcp` | 9 | `middle_mcp` | 16 | `ring_tip` |
| 3 | `thumb_ip` | 10 | `middle_pip` | 17 | `little_mcp` |
| 4 | `thumb_tip` | 11 | `middle_dip` | 18 | `little_pip` |
| 5 | `index_mcp` | 12 | `middle_tip` | 19 | `little_dip` |
| 6 | `index_pip` | 13 | `ring_mcp` | 20 | `little_tip` |

各后端必须在自身边界把原生顺序转换成该顺序。

## 原始视觉帧边界

摄像头和视频文件输入统一使用 `/visual/input/image_raw`，ROS 类型为
`sensor_msgs/msg/Image`，采用 sensor-data QoS、`bgr8` 编码和非空的光学
`header.frame_id`。切换只发生在启动时的数据源选择；重建代码不得为两种来源使用不同
的图像 topic 或编码。

适配器会在摄像头成功采集或视频成功解码后，立即使用当前 ROS 时钟为图像打时间戳。
同一进程内时间戳必须严格递增，视频循环后也不例外。重建后端应把该时间戳保留到
生成的 `HandObservation` 中，并使用能够区分摄像头和视频的来源标识，例如
`camera_mediapipe` 或 `video_hamer`。

视频文件必须使用录制该视频的摄像头标定；合成标定固定样例不能用于任意视频。原始
视频模式也不同于 `recorded` 模式：视频提供重建前的 RGB 帧，而 `recorded` 提供已经
重建并版本化的 21 关节观测。

## `HandObservation`

ROS 类型：`hand_msgs/msg/HandObservation`。

| 字段 | 含义与约束 |
|---|---|
| `header` | 采集/生成时间戳；`frame_id` 是 `joints_3d_m` 所在坐标系 |
| `schema_version` | 精确 schema 版本 |
| `sequence` | 单调递增的源样本序列 |
| `handedness` | `UNKNOWN`、`LEFT` 或 `RIGHT`；表示解剖学手别，不是屏幕镜像位置 |
| `source` | 稳定适配器标识，如 `synthetic`、`recorded`、`camera_mediapipe` 或 `hamer` |
| `joints_2d_px` | 21 个图像点；`x` 向右、`y` 向下、`z` 必须为零 |
| `joints_3d_m` | 在 `header.frame_id` 中表达的 21 个三维点，单位米 |
| `joints_3d_valid` | 对应三维点是否已测量/估计且可用 |
| `confidence` | 每关节 `[0, 1]` 置信度 |
| `valid` | 数据源声明该观测是否有资格进入下游校验 |

`valid=true` 不会绕过校验。校验器仍会检查版本、时间戳、有限值、置信度、坐标系、
序列号和配置的最少高置信度关节数。

## `RobotTarget`

ROS 类型：`hand_msgs/msg/RobotTarget`。

`header.frame_id` 必须是 `robot_base`，或 `docs/frames.md` 中记录的配置等价坐标系；
时间戳为目标创建时间。`end_effector_pose` 在该坐标系中表达。手指名称、目标位置和最大
速度数组长度必须相同，名称遵循所选资产 manifest 顺序。位置与速度限制使用弧度和
弧度/秒；末端执行器速度限制使用米/秒和弧度/秒。

状态码包括 `OK`、`INPUT_INVALID`、`CALIBRATION_INVALID`、`IK_FAILED`、
`OUT_OF_WORKSPACE`、`JOINT_LIMIT` 和 `STALE_INPUT`。执行层必须拒绝 `valid=false`、
未知状态、非有限值、长度不匹配数组或过期时间戳，并且绝不能无限复用无效目标。

## `SystemStatus`

ROS 类型：`hand_msgs/msg/SystemStatus`。至少每秒发布一次。header 时间戳为状态创建
时间；由于消息不表示空间位置，`frame_id` 为空。

状态包括 `INIT`、`CALIBRATING`、`READY`、`RUNNING`、`DEGRADED` 和 `ERROR`。
计数器在单个节点进程中单调递增。`drop_rate` 等于
`dropped_count / (received_count + dropped_count)`，分母为零时取零。延迟是在共享
时钟上的采集到状态时间。如果时钟域未知或观察到负时间差，
`end_to_end_latency_valid=false`，对应数值使用有限零占位。`last_error_code` 是稳定、
机器可读的代码，`last_error_message` 是诊断文本。

## `EpisodeRecord`

ROS 类型：`hand_msgs/msg/EpisodeRecord`。每条记录保存原始观测和动作、各自独立的
时间戳、episode ID、单调步索引、任务标签、缺失值 mask、完成标志、成功标签和失败
原因。对齐过程不得覆盖原始时间戳或静默填补缺失值。只有 `episode_complete=true`
时 `success` 才有意义；未完成记录保持 false。

数据集的训练/验证/测试划分以完整 episode 为单位，绝不能把同一 episode 的相邻帧
拆到不同集合。

## 初始 topic 与 QoS

| Topic | 类型 | QoS | 用途 |
|---|---|---|---|
| `/visual/input/image_raw` | `sensor_msgs/msg/Image` | sensor data、best effort、depth 5 | 重建前统一的摄像头/视频帧输入 |
| `/hand/observation/raw` | `HandObservation` | sensor data、best effort、depth 5 | 校验前适配器输出 |
| `/hand/observation` | `HandObservation` | sensor data、best effort、depth 5 | 已接受观测 |
| `/robot/target` | `RobotTarget` | reliable、volatile、keep last 1 | 最新安全目标 |
| `/system/status` | `SystemStatus` | reliable、volatile、keep last 10 | 健康与计数器，至少 1 Hz |
| `/episode/record` | `EpisodeRecord` | reliable、volatile、keep last 10 | 版本化对齐记录 |

公网传输必须显式使用 VPN、Zenoh、WebSocket 或 RPC 网关。不得把原始 DDS 暴露到
公网。
