[English](server_latest.md) | [简体中文](server_latest.zh-CN.md)

# 服务器交接

- 更新时间：2026-08-29
- Git 提交：审计时为 `9910dbc`
- 服务器环境版本：已实测，见 `docs/server_environment.zh-CN.md`
- 输入与校验和：尚未收到本机提供的输入

## 已完成

只读审计已在真实 RTX 4090 实例上执行，输出保存在
`/root/autodl-tmp/embodied/artifacts/audit/`。实测的平台、存储和分层状态记录在
`docs/server_environment.zh-CN.md`。

L0 到 L2 层已安装并验证：

- L0：驱动 580.105.08，`nvidia-smi` 可见一块 24564 MiB 的 RTX 4090。
- L1：git、cmake、tmux、ffmpeg、rsync、gcc。
- L2：ROS2 Humble desktop、colcon、rosbag2、tf2、cv_bridge、OpenCV 4.5.4，
  基于 Ubuntu 系统 Python 3.10.12 ABI 安装。

`scripts/server_ros2_env.sh` 是 ROS2 入口脚本。它是必需的，因为 Miniconda base 的
`python3` 在 `PATH` 中位于 `/usr/bin` 之前，会让 ROS2 找不到 `cv2`、`cv_bridge` 和
`rclpy`。该脚本同时把 DDS 固定为 `ROS_LOCALHOST_ONLY=1` 并使用 domain 72。

新增第四个 Conda 环境 `h2r-sim`（Python 3.12.14），原因是 Isaac Sim 6.0.1 要求
Python 3.12，无法与 ROS2 依赖的 3.10 环境共用。

## 测试与指标

在 source `scripts/server_ros2_env.sh` 之后，从 `/root/Hand2Robot` 运行：

| 检查 | 结果 |
|---|---|
| `scripts/doctor.sh` | 退出码 0，视觉输入依赖 OK，摄像头 0 个 |
| `make test-unit` | 66 个测试，OK |
| `colcon build --symlink-install` | `hand2robot_core`、`hand_msgs`、`hand_pipeline` 全部完成 |
| `make smoke-local` | 16 条观测、15 有效、0 无效、0 丢帧、30.0 Hz、2.62 ms；故障探针 0 有效 / 9 无效并给出 `low_confidence` |
| `make smoke-recorded` | 数量 5，序列 `[0,1,2,3,4]`，数据源 `recorded_fixture` |
| `make smoke-video-input` | 5 帧，160x120，`bgr8`，时间戳严格递增 |
| `make smoke-bag` | bag 中 5 条消息、33853 字节，两次独立回放均为 `[0,1,2,3,4]` |
| `make smoke-prototype` | 20 条记录，序列 0-19，完整且成功 |
| `make smoke-prototype-recorded` | 5 条记录，序列 0-4 |
| `make smoke-prototype-watchdog` | 通过 |

仓库全部九项检查都在服务器上通过，结果与本地 CPU 基线的声明一致。没有任何结论是
直接沿用本机的。

## 生成产物

- `/root/autodl-tmp/embodied/artifacts/audit/server_audit_20260829T134813Z.txt`
- 被忽略的 `local_data/` 目录下的 episode JSONL 与 smoke 日志。

## 已知问题

1. 持久盘是 **50 GB**，不是早期笔记记录的 300 GB。这是 Isaac Sim、数据集和
   checkpoint 的关键约束。
2. 从 `pypi.nvidia.com` 安装 Isaac Sim 6.0.1.0 在本实例上很慢（下载后段约
   170 KB/s），撰写本交接时仍在进行。不对 Isaac Sim 场景可用性做任何声明。
3. AutoDL 数据盘的关机持久性、快照和恢复行为仍未确认，因此不应启动长时间实验。
4. 没有 Docker 或 Podman，指南中的容器 GPU 验收门槛无法在此演示。替代方案是宿主
   驱动加各环境的 Python 隔离。
5. 没有 `systemd`，长任务必须运行在 `tmux` 中。
6. 没有 `/dev/video*` 设备。重建集成必须走视频文件、录制或合成输入路径。
7. L4 和 L5 栈刻意缺失。PyTorch、MediaPipe、HaMeR/MANO 和 LeRobot 的版本必须先
   针对驱动 CUDA 13.0 固定。
8. `assets/robot_manifest.yaml` 仍是占位文件；尚未核对任何机器人或手部资产。

## 本机需要配合

当前没有阻塞项。本机准备验证服务器输入路径时，请提供一段短 rosbag 及其 SHA256、
schema 版本和期望帧数，以便服务器用同一校验器回放。

## 下一步

完成 Isaac Sim 安装，然后推进第 1 周验收目标：一个 headless 场景，消费仓库内的
录制序列，用经过检查的机器人关节名和 IK 替换 CPU 原型执行器 manifest，运行 1000 个
有界步，记录状态，并通过五分钟 smoke。启动任何长任务前先确认数据盘持久性。
