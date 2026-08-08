[English](roadmap.md) | [简体中文](roadmap.zh-CN.md)

# Hand2Robot 路线图

状态取值：`TODO`、`IN PROGRESS`、`VERIFIED` 或 `BLOCKED`。只有验收证据已提交，或被
带校验和的 manifest 引用时，里程碑才能标记为 `VERIFIED`。

| 里程碑 | 状态 | 成果 | 验收门槛 |
|---|---|---|---|
| M0 仓库基础 | VERIFIED | Git、记忆、工作流、骨架 | `make doctor`；基线进入 `main`；从 `d78e063` 推送 `work/local` |
| M1 共享契约 | VERIFIED | 消息、schema、坐标系、单位 | 提交 `3fb0f80`；5 项契约测试和 rosidl 构建通过 |
| M2 本地 CPU 输入闭环 | VERIFIED | 合成输入到诊断 | 提交 `82f9a5f`；18 项测试；普通与低置信度 smoke 通过 |
| M3 离线采集与回放 | VERIFIED | 合成/录制输入和短 rosbag | 提交 `254e318`/`bbbdf27`/`8394368`；两次精确回放 |
| M3b 视觉输入与重建 | IN PROGRESS | 可切换摄像头/视频 RGB；实时 21 关节输入 | 视频帧 smoke 已验证；MediaPipe/HaMeR 适配器和摄像头硬件待完成 |
| M4 本地标定与重定向 | VERIFIED | TF、尺度、滤波、CPU 安全目标 | 提交 `8612de6`/`6c7cdbf`；66 项测试；三类原型 smoke |
| M5 服务器 IK 与仿真闭环 | TODO | 资产 IK、Isaac Sim headless、ROS2 bridge | 资产完成审计；1000 步加五分钟稳定运行 |
| M6 可靠性 | IN PROGRESS | 状态机、watchdog、故障 | 本地 watchdog/六类故障已覆盖；仍需服务器 30 分钟运行 |
| M7 重建与策略 | TODO | HaMeR/MANO、LeRobot、BC/DP | 可复现指标和可恢复实验 |
| M8 发布 | TODO | 演示、报告、简历、发布 | 十分钟 smoke 和最终复现审计 |

## 当前构建队列

1. 在开始 M5 前运行并审查 GPU 服务器只读审计。
2. 冻结服务器机器人/手部资产 manifest、许可证、关节顺序、限制和 IK 求解器。
3. 让 MediaPipe 或 HaMeR 只接入一次 `/visual/input/image_raw`；先验证视频模式，再在硬件
   和依赖获批后验证摄像头模式。
