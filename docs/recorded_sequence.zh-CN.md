[English](recorded_sequence.md) | [简体中文](recorded_sequence.zh-CN.md)

# 录制手部序列格式

状态：格式版本 `0.1.0`，用于 M3 CPU 固定样例。

录制适配器读取 UTF-8 JSON，其中包含顶层元数据、去重姿态和有序帧。该格式刻意保持
小型且无依赖，以便在 ROS2 启动前完成校验。

必需元数据：

- `schema_version`：当前为 `0.1.0`；
- `frame_id`：每个三维关节所在坐标系；
- `handedness`：`unknown`、`left` 或 `right`；
- `source`：稳定的数据源/会话名称；
- `nominal_rate_hz`：有限正数采集频率；
- `poses`：一个或多个完整的 21 关节观测；
- `frames`：有序采集时间戳、序列号、姿态引用和有效标志。

每个姿态包含 `joints_2d_px`、`joints_3d_m`、`joints_3d_valid` 和 `confidence`，顺序
与单位遵循 `docs/interfaces.md`。帧保留绝对 `capture_timestamp_ns`；回放使用时间戳
差值调度，但不改写时间戳。因此，旧离线序列的“采集到当前”延迟不能作为实时管线
延迟基准。

仓库固定样例为 `recorded_hand_static_v0.1.json`：10 Hz 的五个静态帧、一个姿态、
序列 0–4、全部有效，数据源为 `recorded_fixture`。其 manifest 记录精确 SHA256。
