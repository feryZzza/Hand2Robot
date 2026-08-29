[English](server_environment.md) | [简体中文](server_environment.zh-CN.md)

# 服务器环境

以下数值来自 2026-08-29 通过 `scripts/server_audit_readonly.sh` 完成的只读审计。
证据文件保存在持久数据盘 `/root/autodl-tmp/embodied/artifacts/audit/`。

## 平台

| 项目 | 实测值 |
|---|---|
| 主机 | `autodl-container-y6mn6kl23q-4a4f13e4`，AutoDL 容器，无 systemd（PID 1 不是 systemd） |
| 系统 | Ubuntu 22.04.4 LTS (jammy)，内核 5.15.0-78-generic |
| GPU | 1x NVIDIA GeForce RTX 4090，24564 MiB，无 ECC，审计时空闲 |
| 驱动 / CUDA | 580.105.08，驱动报告 CUDA 13.0 |
| CPU | 2x Intel Xeon Platinum 8358P，128 逻辑核，2 个 NUMA 节点 |
| 内存 | 共 1.0 TiB，可用 944 GiB，无交换空间 |
| 系统盘 | `/` 为 30 GB overlay，装完 ROS2 后剩余约 19 GiB |
| 持久盘 | `/dev/md0` XFS 挂载在 `/root/autodl-tmp`，**50 GB**，不是 300 GB |
| 容器运行时 | 没有 Docker 和 Podman；无法使用 Docker-in-Docker |
| 摄像头 | 没有 `/dev/video*` 设备；可用输入是视频文件、录制序列和合成数据 |

50 GB 持久盘配额是本实例的关键约束，它取代了早期笔记中记录的 300 GB。

## 存储布局

指南中的 `/data/embodied` 示例在这里对应 `/root/autodl-tmp/embodied`。任何会增长的
内容都不能放在 30 GB overlay 上。

```text
/root/autodl-tmp/embodied/
├── repos/hand2robot/        # 服务器侧检出（work/server）
├── datasets/{raw,processed}/
├── runs/<run_id>/
├── checkpoints/
├── cache/{conda,hf,torch,pip,xdg,tmp,isaac}/
├── artifacts/{audit,gpu_smoke}/
├── logs/
├── archives/
└── config/                  # env.sh、activate.sh、ros2_env.sh、environments/
```

`datasets/raw` 已设为只读。缓存、处理数据、runs 和 checkpoint 相互分离，使可重建
数据能够被回收，而不影响原始数据。

## 软件分层

| 层 | 组件 | 状态 |
|---|---|---|
| L0 | NVIDIA 驱动 580.105.08，`nvidia-smi` 可见 GPU | 已验证 |
| L1 | git 2.34.1、cmake 3.22.1、tmux 3.2a、ffmpeg 4.4.2、rsync 3.2.7、gcc 11.4.0 | 已验证 |
| L2 | ROS2 Humble desktop、colcon、rosbag2、tf2、cv_bridge、OpenCV 4.5.4 | 已验证 |
| L3 | Isaac Sim 6.0.1.0（pip，`[all,extscache,ros2]`）位于 `h2r-sim` | 已安装，headless 运行尚未验证 |
| L4 | PyTorch、MediaPipe、HaMeR/MANO | 未安装；版本未固定 |
| L5 | LeRobot、BC/Diffusion Policy | 未安装 |

## Python 环境

ROS2 Humble 基于 Ubuntu 系统 Python 3.10 ABI 构建，在 Conda 之外使用。Isaac Sim
6.0.1 要求 Python 3.12，无法共用 3.10 环境，因此单独建立前缀。

| 环境 | Python | 范围 |
|---|---:|---|
| 系统 `/usr/bin/python3` | 3.10.12 | ROS2、colcon、`hand_msgs`、`hand_pipeline`、`hand2robot_core` |
| `h2r-core` | 3.10.20 | 契约、标定、重定向、IK、测试 |
| `h2r-reconstruction` | 3.10.20 | MediaPipe 和 HaMeR/MANO |
| `h2r-policy` | 3.10.20 | LeRobot、BC、Diffusion Policy |
| `h2r-sim` | 3.12.14 | Isaac Sim 6.0.1.0 及其 ROS2 bridge 扩展 |

Conda 前缀位于 `/root/autodl-tmp/embodied/envs/conda/`。

### 激活方式

Miniconda base 的 `python3` 在 `PATH` 中位于 `/usr/bin` 之前，会让 ROS2 找不到
`cv2`、`cv_bridge` 和 `rclpy` 扩展模块。任何 ROS2 或 colcon 工作都要先 source ROS2
环境文件；它会把系统解释器放在最前面，并把 DDS 限制在本机。

```bash
source /root/autodl-tmp/embodied/config/ros2_env.sh          # ROS2 + 工作区
source /root/autodl-tmp/embodied/config/activate.sh h2r-core  # Conda 环境
```

## 已验证测试

在 source `ros2_env.sh` 之后，从 `/root/Hand2Robot` 运行：

| 检查 | 结果 |
|---|---|
| `scripts/doctor.sh` | 退出码 0，视觉输入依赖 OK |
| `make test-unit` | 66 个测试，OK |
| `colcon build --symlink-install` | 3 个包完成 |
| `make smoke-local` | 16 条观测、15 有效、0 丢帧、30.0 Hz、2.62 ms 延迟；故障探针达到 9 条无效并给出 `low_confidence` |
| `make smoke-recorded` | 数量 5，序列 0-4，数据源 `recorded_fixture` |
| `make smoke-video-input` | 5 帧，160x120，`bgr8`，时间戳严格递增 |
| `make smoke-bag` | bag 中 5 条消息，两次独立回放均为 0-4 |
| `make smoke-prototype` | 20 条记录，序列 0-19，完整且成功 |
| `make smoke-prototype-recorded` | 5 条记录，序列 0-4 |
| `make smoke-prototype-watchdog` | 通过 |

## 风险与未验证项

1. **持久盘是 50 GB，不是 300 GB。** Isaac Sim 及其扩展缓存占用很大比例。安装后
   必须清理 `cache/pip`；在进入第 5-6 周工作前，数据集、checkpoint 和 Isaac 资产
   缓存需要明确的保留策略。
2. **关机持久性和快照未确认。** AutoDL 数据盘保留与快照行为尚未测试，因此还不能
   启动长时间实验。
3. **没有容器运行时。** 指南 L0 验收门槛中的容器 GPU 隔离无法在本实例演示；替代
   方案是宿主驱动加各环境的 Python 隔离。
4. **没有 `systemd`。** 长任务必须使用 `tmux`，不能用 user service。
5. **Isaac Sim headless 闭环未验证。** 6.0.1.0 已安装，但 1000 步运行、ROS2
   bridge、机器人资产和五分钟稳定性 smoke 仍未完成。
6. **机器人与手部资产未选定。** `assets/robot_manifest.yaml` 仍是占位文件；
   Franka/Panda 加 Allegro 是预期目标，但关节名、限位和许可证均未核对。
7. **L4 和 L5 栈刻意缺失。** PyTorch、MediaPipe、HaMeR/MANO 和 LeRobot 的版本
   必须先针对驱动 CUDA 13.0 固定后再下载。

## 空间策略

按实测 50 GB 计算的 `/root/autodl-tmp` 可用空间阈值：

| 可用比例 | 状态 | 动作 |
|---:|---|---|
| 大于 25% | 正常 | 继续运行 |
| 15%-25% | 警告 | 归档 runs，清理可重建缓存 |
| 小于 15% | 红线 | 先处理空间，禁止启动新实验 |
