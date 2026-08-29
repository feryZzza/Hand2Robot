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

L0 到 L5 层已安装并验证：

- L0：驱动 580.105.08，`nvidia-smi` 可见一块 24564 MiB 的 RTX 4090。
- L1：git、cmake、tmux、ffmpeg、rsync、gcc。
- L2：ROS2 Humble desktop、colcon、rosbag2、tf2、cv_bridge、OpenCV 4.5.4，
  基于 Ubuntu 系统 Python 3.10.12 ABI 安装。
- L3：`h2r-sim` 中的 Isaac Sim 6.0.1.0（含 `[all,extscache,ros2]`），已通过
  headless 1000 步运行验证。
- L4：`h2r-reconstruction` 中的 torch 2.9.1+cu128、MediaPipe 0.10.21、
  OpenCV 4.11.0.86、numpy 1.26.4，手部图已在 4090 上通过 EGL 加载。
- L5：`h2r-policy` 中的 LeRobot 0.4.4、diffusers 0.35.2、gymnasium 1.3.0、
  zarr、h5py、wandb。

两处版本冲突通过实测而非假设解决。MediaPipe 0.10.21 要求 `numpy<2`，而
opencv-python 4.12 要求 `numpy>=2`，因此 OpenCV 固定在接受 numpy 1.x 的 4.11.0.86。
Isaac Sim 在 `h2r-sim` 中自带 torch 2.11.0+cu130，不与两个 Python 3.10 环境使用的
2.9.1+cu128 共用。

`scripts/server_ros2_env.sh` 是 ROS2 入口脚本。它是必需的，因为 Miniconda base 的
`python3` 在 `PATH` 中位于 `/usr/bin` 之前，会让 ROS2 找不到 `cv2`、`cv_bridge` 和
`rclpy`。该脚本同时把 DDS 固定为 `ROS_LOCALHOST_ONLY=1` 并使用 domain 72。

新增第四个 Conda 环境 `h2r-sim`（Python 3.12.14），原因是 Isaac Sim 6.0.1 要求
Python 3.12，无法与 ROS2 依赖的 3.10 环境共用。它的入口是
`scripts/server_sim_env.sh`，其中以 `OMNI_KIT_ACCEPT_EULA=YES` 记录用户在
2026-08-29 对 NVIDIA Omniverse 许可协议的接受；缺少它时每次 Kit 启动都会停在交互
提示上。

Isaac Sim 从 `pypi.nvidia.cn` 安装，这是 `pypi.nvidia.com` 通过 301 重定向返回的
主机。逐包跟随跳转的速率是 263 KB/s，90 分钟后仍未完成；直连该主机达到 11 MB/s，
约 15 分钟完成。两种方式下 pip 都按 NVIDIA 索引中的哈希校验每个包。

50 GB 数据盘需要主动管理。`h2r-reconstruction` 与 `h2r-policy` 固定同一个
torch 2.9.1+cu128，因此二者完全相同的 `nvidia/` 和 `triton/` 共享库已通过硬链接
合并，回收 4.81 GiB。之后四个环境都在 GPU 上重新验证通过。

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

仓库检查之外：

| 检查 | 结果 |
|---|---|
| `scripts/run_sim_headless_check.py --steps 1000` | 启动 10.8 s，1000 步耗时 3.26 s（306.9 steps/s），立方体高度 0.1 m，状态有限且已静止 |
| Warp 初始化 | 1.13.0 运行在 RTX 4090，sm_89，CUDA Toolkit 12.9 对应驱动 13.0 |
| `h2r-reconstruction` GPU | torch 2.9.1+cu128 识别到 4090，GPU 矩阵乘法有限，MediaPipe 手部图通过 EGL 加载且具备 21 关节 |
| `h2r-policy` GPU | torch、LeRobot、diffusers、gymnasium、zarr、h5py 均可导入；GPU 矩阵乘法有限 |

## 生成产物

- `/root/autodl-tmp/embodied/artifacts/audit/server_audit_20260829T134813Z.txt`
- `/root/autodl-tmp/embodied/artifacts/sim_headless/headless_20260829T162805Z.json`
- `/root/autodl-tmp/embodied/config/environments/{h2r-core,h2r-reconstruction,h2r-policy,h2r-sim}.lock`
- 被忽略的 `local_data/` 目录下的 episode JSONL 与 smoke 日志。

## 已知问题

1. 持久盘是 **50 GB**，不是早期笔记记录的 300 GB，且四个环境已占用 38 GB（仅
   Isaac Sim 就是 25 GB）。目前约剩 13 GB，这是数据集和 checkpoint 的关键约束。
   每次大型安装后都要清理 `cache/pip`。
2. Isaac Sim 的 ROS2 bridge 未测试。`isaacsim-ros2` 已安装，但尚未与 ROS2 Humble
   工作区交换任何桥接 topic。
3. AutoDL 数据盘的关机持久性、快照和恢复行为仍未确认，因此不应启动长时间实验。
4. 没有 Docker 或 Podman，指南中的容器 GPU 验收门槛无法在此演示。替代方案是宿主
   驱动加各环境的 Python 隔离。
5. 没有 `systemd`，长任务必须运行在 `tmux` 中。
6. 没有 `/dev/video*` 设备。重建集成必须走视频文件、录制或合成输入路径。
7. HaMeR/MANO 仍然缺失。目前只安装了 MediaPipe 一个重建后端；MANO 需要接受许可并
   获取模型文件，且这些文件绝不能进入 Git。
8. `assets/robot_manifest.yaml` 仍是占位文件；尚未核对任何机器人或手部资产。
   headless 检查刻意使用基本立方体。
9. 尚未运行 30 分钟长稳或五分钟连续 smoke。目前只验证了有界的 1000 步运行，因此
   长时间的资源增长行为仍未知。
10. 在 `h2r-reconstruction` 或 `h2r-policy` 中重装 torch 会破坏硬链接共享，并把
    4.81 GiB 重新占回去。

## 本机需要配合

当前没有阻塞项。本机准备验证服务器输入路径时，请提供一段短 rosbag 及其 SHA256、
schema 版本和期望帧数，以便服务器用同一校验器回放。

## 下一步

先确认数据盘经过停止/启动周期后完好，然后推进第 1 周验收目标的其余部分：一个
headless 场景，消费仓库内的录制序列，用经过检查的机器人关节名和 IK 替换 CPU 原型
执行器 manifest，记录状态，并通过五分钟 smoke。该门槛中有界 1000 步的部分已由
`scripts/run_sim_headless_check.py` 满足，但用的是基本几何体而非机器人。跨
Python 3.12/3.10 边界把 Isaac Sim 桥接到 ROS2 Humble 工作区，是下一个未验证环节。
