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
| L3 | Isaac Sim 6.0.1.0（pip，`[all,extscache,ros2]`）位于 `h2r-sim` | 已验证 headless，完成 1000 个有界步 |
| L4 | PyTorch 2.9.1+cu128、MediaPipe 0.10.21、OpenCV 4.11.0.86、numpy 1.26.4 | 已在 GPU 上验证；HaMeR/MANO 仍缺失 |
| L5 | LeRobot 0.4.4、diffusers 0.35.2、gymnasium 1.3.0、zarr、h5py、wandb | 已验证 GPU 导入；未运行实验 |

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

Conda 前缀位于 `/root/autodl-tmp/embodied/envs/conda/`。已固定的包清单导出到
`/root/autodl-tmp/embodied/config/environments/<name>.lock`。

`h2r-reconstruction` 与 `h2r-policy` 都固定 torch 2.9.1+cu128，因此二者完全相同的
`nvidia/` 和 `triton/` 共享库已通过硬链接合并，回收了 50 GB 盘上的 4.81 GiB。在任一
环境中重装 torch 会破坏共享，并把这部分空间重新占回去。

### 激活方式

Miniconda base 的 `python3` 在 `PATH` 中位于 `/usr/bin` 之前，会让 ROS2 找不到
`cv2`、`cv_bridge` 和 `rclpy` 扩展模块。任何 ROS2 或 colcon 工作都要先 source ROS2
环境文件；它会把系统解释器放在最前面，并把 DDS 限制在本机。

```bash
source scripts/server_ros2_env.sh                             # ROS2 + 工作区
source scripts/server_sim_env.sh                              # Isaac Sim（py3.12）
source /root/autodl-tmp/embodied/config/activate.sh h2r-core   # 其他 Conda 环境
```

绝不要在同一个 shell 中同时 source ROS2 和 Isaac Sim 的入口脚本。二者使用不同的
Python 版本，必须通过 ROS2 消息、版本化文件或显式 RPC 契约通信。

`scripts/server_sim_env.sh` 会导出 `OMNI_KIT_ACCEPT_EULA=YES`，记录用户在
2026-08-29 对 NVIDIA Omniverse 许可协议的接受。缺少它时每次 Kit 启动都会停在交互
提示上。

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

### Isaac Sim headless 检查

`scripts/run_sim_headless_check.py` 会启动 headless `SimulationApp`，添加地面和一个
动态立方体，运行有界步数的物理仿真，并断言最终状态有限且已静止。从 Isaac Sim 环境
运行：

```bash
source scripts/server_sim_env.sh
python scripts/run_sim_headless_check.py --steps 1000 \
  --json /root/autodl-tmp/embodied/artifacts/sim_headless/headless_$(date -u +%Y%m%dT%H%M%SZ).json
```

2026-08-29 实测：启动 10.8 s，1000 步耗时 3.26 s（306.9 steps/s），立方体最终高度
0.1 m，状态有限且已静止。Warp 1.13.0 在 RTX 4090 上初始化成功（sm_89，CUDA
Toolkit 12.9 对应驱动 13.0）。该检查不加载任何机器人资产，因此不能作为关节名、IK
或碰撞行为的证据。

### 重建与策略检查

- `h2r-reconstruction`：torch 2.9.1+cu128 在 RTX 4090 上报告 CUDA 可用，GPU 矩阵乘法
  返回有限值，MediaPipe 手部图通过 EGL 加载并具备预期的 21 关节契约。
- `h2r-policy`：torch、LeRobot 0.4.4、diffusers、gymnasium、zarr 和 h5py 均可导入，
  GPU 矩阵乘法返回有限值。

## 风险与未验证项

1. **持久盘是 50 GB 而非 300 GB，且环境本身已占用 38 GB。** 仅 Isaac Sim 就是
   25 GB；`h2r-reconstruction` 和 `h2r-policy` 在硬链接去重前各约 8 GB。目前约剩
   13 GB，因此在第 5-6 周之前，数据集、checkpoint 和 Isaac 资产缓存需要明确的保留
   策略。每次大型安装后都要清理 `cache/pip`。
2. **关机持久性和快照未确认。** AutoDL 数据盘保留与快照行为尚未测试，因此还不能
   启动长时间实验。
3. **没有容器运行时。** 指南 L0 验收门槛中的容器 GPU 隔离无法在本实例演示；替代
   方案是宿主驱动加各环境的 Python 隔离。
4. **没有 `systemd`。** 长任务必须使用 `tmux`，不能用 user service。
5. **Isaac Sim 的 ROS2 bridge 未测试。** `isaacsim-ros2` 已安装，但尚未与 ROS2
   Humble 工作区交换任何桥接 topic，且两个运行时按设计使用不同的 Python 版本。
6. **机器人与手部资产未选定。** `assets/robot_manifest.yaml` 仍是占位文件；
   Franka/Panda 加 Allegro 是预期目标，但关节名、限位和许可证均未核对。headless
   检查刻意使用基本立方体，而非机器人。
7. **HaMeR/MANO 缺失。** 目前只安装了 MediaPipe 一个重建后端。MANO 需要接受其许可
   并获取模型文件，且这些文件绝不能进入 Git。
8. **尚未运行 30 分钟长稳或五分钟连续 smoke。** 目前只验证了有界的 1000 步运行，
   因此长时间的资源增长行为仍未知。
9. **Isaac Sim 从 `pypi.nvidia.cn` 安装**，这是 `pypi.nvidia.com` 通过 301 重定向
   返回的域名。直连它达到 11 MB/s，而经由跳转链路只有 263 KB/s，安装时间从 90 分钟
   以上缩短到约 15 分钟。pip 仍按 NVIDIA 索引中的哈希校验每个包。

## 空间策略

按实测 50 GB 计算的 `/root/autodl-tmp` 可用空间阈值：

| 可用比例 | 状态 | 动作 |
|---:|---|---|
| 大于 25% | 正常 | 继续运行 |
| 15%-25% | 警告 | 归档 runs，清理可重建缓存 |
| 小于 15% | 红线 | 先处理空间，禁止启动新实验 |
