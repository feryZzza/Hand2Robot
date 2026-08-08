[English](architecture.md) | [简体中文](architecture.zh-CN.md)

# 架构

状态：本地 CPU 原型已验证；服务器执行边界待完成。

## 当前数据路径

```text
synthetic_hand_publisher 或 recorded_sequence_player
    /hand/observation/raw  [HandObservation，best effort]
                    |
                    v
hand_observation_validator ----------------> /system/status
    /hand/observation     [仅通过校验的观测]      |
                    |                              |
                    v                              |
safe_retargeter                                    |
  标定 -> 手掌/尺度 -> One Euro -> 安全检查       |
    /robot/target [reliable，keep last 1]          |
                    |                              |
                    +---------------+--------------+
                                    v
                            episode_recorder
                 /episode/record + 被忽略的 JSONL 产物
```

`input_pipeline.launch.py` 只运行一个适配器和校验器。它通过 `input_mode` 选择
`synthetic` 或 `recorded`；任意时刻只运行一个适配器，下游 topic 保持不变。

`prototype_pipeline.launch.py` 保留同一适配器边界，并增加安全重定向器和可选的
episode 记录器。实时模式用 ROS 时钟检查事件年龄。录制模式保留历史事件时间，因此
必须显式设置 `enforce_capture_age:=false`；时间顺序、基于源时间的速率限制和单调到达
watchdog 仍然启用。

校验器只重新发布通过校验的消息。低置信度、不支持的 schema、空坐标系/数据源、
非有限值、无效像素 z、非单调时间/序列、无效源标志和畸形数组都不能进入
`/hand/observation`。

## 包职责

| 包 | 职责 | 运行时依赖 ROS2 |
|---|---|---|
| `hand_msgs` | 四个版本化线协议 | 是，仅用于接口生成 |
| `hand2robot_core` | 校验、SE(3)、手掌尺度、滤波、重定向安全、episode 对齐 | 否 |
| `hand_pipeline` | ROS 转换、适配器、校验器、重定向器、记录器、探针 | 是 |

`hand2robot_core` 接收普通不可变数据，因此无需 DDS、ROS 图启动、摄像头、NumPy 或
GPU 也能测试安全和对齐逻辑。

## 状态与安全行为

- 尚无输入时，校验器发布 `INIT`。
- 最近且通过校验的观测产生 `RUNNING` 并被转发。
- 被拒绝或过期的观测产生 `DEGRADED`，且不被转发。
- 不支持的 schema 会让对应校验器进程产生 `ERROR`。
- 计数器在校验器节点生命周期内保持单调。
- 重定向器只把有界目标标记为有效。
- 输入停止后，watchdog 发布一个无效 `STALE_INPUT` 目标，不会无限重复最后一条命令。

这只是本地状态子集。服务器侧 IK、碰撞状态、ROS2 Bridge 健康状态和仿真器恢复必须
在不削弱校验和过期命令边界的前提下扩展。

## 输入与证据路径

录制适配器在发布前完整加载并验证版本化 JSON 序列，等待发现，保留采集时间戳，且
每帧只发布一次。M3 bag 检查记录 `/hand/observation/raw`，每次回放都经过新的校验器，
从而同时测试序列化和确定性校验，而不只是统计已存储输出。

本地原型 smoke 覆盖连续合成输入、精确五帧录制输入、完整 episode 持久化和数据源
中断。ROS 构建产物、JSONL episode、bag 和日志都保存在被忽略的本地存储下；Git
跟踪的 run manifest 保存哈希和摘要。

## 安全边界与当前非目标

当前本地执行器清单为每根手指提供一个有界屈曲代理，并包含标定后的腕部位姿。只有
通过工作空间和速率限制后才会设置 `valid=true`。它用于在 CPU 上验证契约、传输、
降级和记录，名称上不兼容任何物理机器人或仿真器资产。

下一执行层必须加载经过检查的机器人清单、求解 IK、执行真实关节与碰撞限制、拒绝
过期或未知目标，并报告自身状态。本地原型不会暗中模拟 Isaac Sim、Panda/Allegro、
HaMeR/MANO 或策略训练。
