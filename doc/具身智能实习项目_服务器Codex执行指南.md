# Hand2Robot 具身智能实习项目：服务器 Codex 执行指南

版本：1.0  
日期：2026-08-08  
适用环境：远端 RTX 4090 服务器  
项目周期：8 周

## 1. 使用方式

将本文件复制到服务器，并要求服务器上的 Codex 在任何安装或实现前完整阅读本文件。本文件是服务器侧的独立执行依据，不依赖本地电脑上的原始 PDF。

服务器 Codex 的工作原则：

1. 先做只读环境审计，再安装或修改系统。
2. 先完成最小闭环，再增加模型、数据集和复杂策略。
3. 所有大文件、缓存、容器层和实验输出必须进入数据盘，不能挤占系统盘。
4. 每项“完成”必须对应代码、配置、日志、指标、视频或可重复测试。
5. 不把服务器作为代码或重要数据的唯一副本。
6. 不直接向公网暴露 ROS2 DDS；跨机器优先使用离线 rosbag，实时阶段使用 VPN、Zenoh、WebSocket 或 RPC 网关。
7. 涉及删除数据、重分区、修改防火墙、迁移 Docker 根目录或开放公网端口时，先向用户报告具体目标、影响和回滚方法。

## 2. 项目目标与完成定义

项目名称：Hand2Robot。

目标是构建从人手视觉输入到机器人仿真执行的数据闭环：

```text
RGB / 录制序列 / 合成输入
        ↓
MediaPipe 或 HaMeR/MANO 手部重建
        ↓
坐标标定、尺度归一化、重定向
        ↓
机械臂 IK、灵巧手关节映射、安全限幅
        ↓
ROS2 编排与 Isaac Sim 执行
        ↓
观测、动作、时间戳、状态、成功标签记录
        ↓
LeRobot 数据与 BC/Diffusion Policy 小实验
```

最终必须交付：

- 可从固定环境复现的代码仓库。
- 2–3 分钟演示视频。
- 5–8 页技术报告。
- 系统/仿真版和算法/VA 版两套简历材料。
- 环境、实验、指标和故障排查证据链。
- `release v1.0` 和最终复现清单。

明确不做：

- 不从零训练通用视觉动作大模型。
- 不以真机为前置条件。
- 不同时支持大量机器人和灵巧手资产。
- 不把“安装成功”当作项目成果。

## 3. 服务器职责与边界

服务器负责：

- Isaac Sim GUI 调试、headless 仿真和服务器端录屏。
- ROS2 Bridge、机械臂和灵巧手资产验证。
- HaMeR/MANO 推理、批处理和公开数据子集评测。
- 数据转换、LeRobot、BC 和 Diffusion Policy 实验。
- 完整集成测试、30 分钟长稳测试、故障注入和性能分析。
- 保存原始数据、处理数据、模型缓存、运行日志和 checkpoint。

服务器不负责：

- 直接访问本地摄像头。
- 保存唯一的代码副本。
- 把原始 ROS2 DDS 暴露到公网。
- 无限制保留所有缓存、视频和中间 checkpoint。
- 在用户未确认时删除原始数据或持久化磁盘。

## 4. 阶段 0：环境和资源验收

### 4.1 第一次进入服务器时先执行只读审计

至少检查并记录：

```bash
hostnamectl
cat /etc/os-release
nvidia-smi
free -h
lsblk -f
df -hT
df -i
lscpu
python3 --version
git --version
docker --version
ip addr
```

将结果整理到 `docs/server_environment.md`，不要只保留终端截图。

### 4.2 验收门槛

| 项目 | 目标 | 不满足时的动作 |
|---|---:|---|
| GPU | RTX 4090，显存约 24 GB，`nvidia-smi` 无错误 | 停止安装 Isaac/模型，先报告供应商问题 |
| 内存 | 推荐至少 64 GB | 少于 64 GB 时降低并发并评估交换空间 |
| 持久化数据盘 | 推荐 200–300 GB，最低可用约 180 GB | 先扩盘或制定更严格的数据保留策略 |
| 系统盘 | 安装后仍保留至少 15 GB | 所有缓存和容器层迁移到数据盘 |
| 容器 GPU | 容器内 `nvidia-smi` 正常 | 修复驱动/容器运行时后再继续 |
| 网络 | SSH 稳定，能断点上传和下载 | 先完成带宽测试和断点续传方案 |
| 持久化 | 关机后数据盘保留，有快照或镜像 | 未确认前不开始长实验 |

### 4.3 输出首份审计报告

报告必须包含：

- 主机、镜像、GPU、显存、驱动、CUDA、CPU、内存和磁盘。
- 系统盘与数据盘的真实挂载点。
- Docker/Podman 是否存在、数据根目录在哪里。
- SSH、远程桌面、WebRTC 和端口策略。
- 关机计费、磁盘保留和快照方式。
- 风险、阻塞项、推荐安装方案和预计磁盘占用。

## 5. 存储布局与空间纪律

优先使用真实持久化数据盘。以下以 `/data/embodied` 为例；若实际挂载点不同，应在所有配置中统一替换并记录。

```text
/data/embodied/
├── repos/hand2robot/
├── datasets/
│   ├── raw/                 # 只读原始数据
│   └── processed/           # 可由配置重建
├── runs/<run_id>/
├── checkpoints/            # best / last / milestone
├── cache/
│   ├── hf/
│   ├── torch/
│   ├── pip/
│   ├── xdg/
│   ├── tmp/
│   └── isaac/
├── artifacts/week_<n>/
└── archives/
```

环境变量应指向数据盘：

```bash
export PROJECT_ROOT=/data/embodied
export HF_HOME=/data/embodied/cache/hf
export TORCH_HOME=/data/embodied/cache/torch
export XDG_CACHE_HOME=/data/embodied/cache/xdg
export PIP_CACHE_DIR=/data/embodied/cache/pip
export TMPDIR=/data/embodied/cache/tmp
```

执行要求：

- Docker `data-root` 或 rootless 容器存储必须位于数据盘。
- 迁移容器根目录前记录原路径、服务状态和回滚步骤。
- 原始数据设为只读；`processed`、`runs`、`cache` 严格分开。
- 每个训练任务只保留 `best`、`last` 和明确标记的 `milestone`。
- 每周归档小产物；可重建缓存可删除，原始数据不能无记录删除。

空间报警：

| 数据盘可用比例 | 状态 | 动作 |
|---:|---|---|
| 大于25% | 正常 | 继续运行 |
| 15%–25% | 警告 | 归档 runs、清理可重建缓存 |
| 小于15% | 红线 | 禁止启动新实验，先处理空间 |

## 6. 安全连接与远程运行纪律

- 使用非 root 开发用户和 SSH 密钥，禁用弱密码登录。
- 只开放 SSH 和实际需要的可视化端口；能限制来源 IP 时进行限制。
- 凭据放在未提交的 `.env` 或供应商密钥管理系统；仓库只提交 `.env.example`。
- Isaac Sim 可视化优先使用供应商 WebRTC 或远程桌面。
- 长任务必须进入 `tmux`、systemd user service 或调度器，不依赖本地 SSH 会话存活。
- 初期跨机器流程固定为“本地短 bag → 校验 → 上传 → 服务器回放”。
- 实时联调时只桥接必要的关键点、状态和命令，不转发完整 DDS 广播。

每次重任务启动前必须：

1. 用 1% 数据或 100–500 step 做小样本验证。
2. 记录显存、预计时长、磁盘增长和费用。
3. 确认输出不在容器临时层。
4. 验证 checkpoint 恢复和异常退出后的产物完整性。
5. 保存完整命令、Git commit、配置、随机种子和数据版本。
6. 设置最长运行时间和磁盘/显存监控。

## 7. 软件基线与可复现环境

建议主基线：Ubuntu 22.04 + ROS2 Humble。若服务器镜像或 Isaac Sim 要求不同，优先通过容器隔离，不随意改变主机系统。

分层管理：

| 层 | 内容 | 验收 |
|---|---|---|
| L0 | NVIDIA 驱动、GPU 容器运行时 | 容器内 `nvidia-smi` |
| L1 | Git、CMake、tmux、ffmpeg、rsync | 编译 hello、视频编码、断点传输 |
| L2 | ROS2 Humble、colcon、rosbag2、tf2 | talker/listener 和 bag 回放 |
| L3 | Isaac Sim、ROS2 Bridge | headless 场景和 ROS2 topic |
| L4 | PyTorch、MediaPipe、HaMeR/MANO | 固定单图推理和指标脚本 |
| L5 | LeRobot、BC/DP | 小数据过拟合与 checkpoint 恢复 |

必须固定并记录：

- NVIDIA driver、CUDA、PyTorch、Python、ROS2、Isaac Sim 版本。
- 容器镜像摘要或构建文件。
- Python lock 文件或导出的环境定义。
- 首次启动、第二次启动、服务器重启后三种 smoke test 结果。

不要把 ROS2、Isaac、HaMeR 和 LeRobot 强行塞进单一巨型环境。通过 ROS2 消息、文件 schema 或 RPC 契约连接。

## 8. 仓库结构与统一接口

推荐仓库：

```text
hand2robot/
├── src/{input,reconstruction,calibration,retargeting,control,sim,data}/
├── ros2_ws/src/{hand_msgs,hand_pipeline,sim_bridge,system_monitor}/
├── configs/{robot,hand,sim,experiments}/
├── assets/{urdf,usd,meshes}/
├── tests/{unit,integration,fault_injection}/
├── scripts/{setup,download,run,eval,export}/
├── docs/{architecture,frames,interfaces,experiments,handoff,interview_notes}/
├── examples/
├── Makefile
├── Dockerfile
└── README.md
```

统一接口：

| 接口 | 最小字段 | 硬约束 |
|---|---|---|
| `HandObservation` | timestamp、handedness、2D/3D joints、confidence、frame_id | 时间单调，单位和关节顺序固定 |
| `RobotTarget` | ee pose、finger joints、velocity limits、valid | 使用 robot base frame，关节顺序固定 |
| `SystemStatus` | state、latency、drop rate、last_error | 至少1 Hz，错误可定位 |
| `EpisodeRecord` | observation、action、task、success、timestamps | schema 版本化，多频率对齐可追踪 |

共享契约统一写入 `docs/interfaces.md`。任何字段、坐标系、关节顺序或单位变更必须单独提交，并在本地侧同步确认后再修改依赖模块。

## 9. 八周服务器执行路线

### 第1周：服务器落地与最小仿真闭环

任务：

- 完成环境、磁盘、权限、安全、容器和快照验收。
- 固定一个机械臂与一个末端执行器，例如 Franka/Panda + Allegro Hand。
- 导入 URDF/USD，核对关节、轴向、上下限、质量、惯量和碰撞几何。
- headless 运行1000 step，记录启动时间、RTF、CPU/GPU/显存。
- 执行最小 joint trajectory，无爆炸、穿模或 NaN。
- 建立 ROS2 command → sim bridge → joint state 闭环。
- 录制20–30秒服务器基线视频。

交付：

- `docs/server_environment.md`
- `docs/server_recovery.md`
- `assets/robot_manifest.yaml`
- `scripts/run_sim_headless.sh`
- `artifacts/week_1/{baseline.mp4,metrics.json,server_spec.txt}`

验收：服务器重启后20分钟内复现；连续运行5分钟稳定；topic 和时间戳可观测。

### 第2周：输入契约、回放和数据记录

- 接收本地提供的短 rosbag、checksum 和 schema 版本。
- 验证实时、录制、合成三类输入使用同一 `HandObservation`。
- 接入 rosbag2 回放、数据记录和系统监控。
- 输出频率、掉帧、时间戳异常和端到端延迟。
- 生成节点图、topic/QoS 表和回放视频。

验收：同一 bag 两次回放帧数和主要输出一致；异常输入产生诊断事件。

### 第3周：坐标标定、重定向和 IK

- 固定 world、robot_base、camera、human_wrist、robot_ee、robot_hand_base 和 finger frames。
- 完成尺度归一化、左右手处理、手腕姿态与关节映射。
- 实现机械臂 IK、工作空间裁剪、速度/加速度限制和失败状态码。
- 比较无滤波、低通和 One Euro 滤波。

验收：关节命令100%在限制内；可达测试 IK 成功率不低于95%；不可达目标被拒绝或裁剪。

### 第4周：可靠性、故障注入和完整演示

- 实现 INIT→CALIBRATING→READY→RUNNING→DEGRADED→ERROR 状态机。
- 为输入、重建、IK 和 bridge 建立 heartbeat/watchdog。
- 注入相机掉线、检测丢失、时间戳倒退、节点退出、越界、IK 失败和延迟激增。
- 分解 capture、reconstruction、retarget、IK、bridge 延迟。
- 录制包含正常路径和至少两种异常恢复的 `demo_v1.mp4`。

验收：连续30分钟无失控或持续资源增长；异常命令不进入执行层；故障恢复条件明确。

### 第5周：HaMeR/MANO 与误差分析

- 配置 MANO 许可和模型文件，模型不得提交仓库。
- 固定样例跑通 HaMeR 单图及批量推理。
- 实现 `HaMeRBackend`，与 MediaPipe 共用 `HandObservation`。
- 在公开数据小子集或自采序列计算 MPJPE、PA-MPJPE、PVE、2D reprojection、acceleration、FPS/latency。
- 整理至少8个失败案例并接入重定向管线。

验收：单位、关节顺序和评测协议有测试；报告准确度、速度、显存和时序稳定性。

### 第6周：LeRobot、BC 和 Diffusion Policy

- 定义 episode schema 和多频率对齐方法。
- 导出 LeRobot 兼容数据和 dataset card。
- 先对10–50个 episode 过拟合 BC，验证数据链路。
- 再运行固定任务的 BC 与 Diffusion Policy 对比。
- 记录成功率、样本数、种子、推理延迟、显存、GPU 小时和失败模式。

验收：验证集按 episode 隔离；checkpoint 可恢复；恢复后的配置和曲线连续。

### 第7周：作品集和报告产物

- 从服务器统一导出指标、图表、失败案例和压缩视频。
- 保证 README、视频、报告和简历使用同一结果源。
- 执行密钥、绝对路径、大文件和许可证检查。
- 提供最终 smoke test 和复现脚本。

### 第8周：冻结、复现和归档

- 冻结 release，只修复阻塞复现、错误数字和安全问题。
- 从干净容器或新快照进行最终复现。
- 输出环境摘要、镜像摘要、配置、数据 manifest 和 checkpoint manifest。
- 清理可重建缓存，保留 release 所需的最小归档。

## 10. 核心验收指标

| 实验 | 最低要求 |
|---|---|
| 仿真静置 | 5分钟无漂移、爆炸、NaN |
| headless 长稳 | 30分钟，资源无持续增长 |
| 关节边界 | 越界目标被拒绝或裁剪，有诊断 |
| IK | 可达测试集成功率不低于95% |
| 滤波 | 同一 bag 比较抖动与滞后，至少3段序列 |
| 重建后端 | MediaPipe/HaMeR，同一输入至少1000帧 |
| 故障恢复 | 至少6类故障，每类至少5次 |
| 策略 | BC/DP 至少20次 rollout，报告样本数与方差 |
| 复现 | 固定环境10分钟内跑完 smoke test |

每个 run 必须包含：

```yaml
run_id: <date>_<task>_<variant>_<seed>
git_commit: <sha>
config: <path>
data_version: <name>@<sha256>
hardware: <gpu_driver_cpu_ram>
metrics: <metric files>
artifacts: <curves_video_events>
decision: keep | reject | rerun
reason: <short explanation>
```

## 11. 与本机 Codex 的交接契约

### 11.1 传输方向

本机到服务器：

- Git commit 和配置。
- 短样例 rosbag、视频或关键点序列。
- `sha256`、schema 版本、采集说明和期望帧数。

服务器到本机：

- `metrics.json/csv`、事件日志摘要和图表。
- 压缩后的演示视频。
- README、环境报告和小体积发布产物。
- checkpoint 只传索引、大小和 hash；实体留在服务器或对象存储。

禁止同步回本地：

- `datasets/raw/`
- `cache/`
- 完整 `runs/`
- 全量 checkpoints
- Isaac Sim 安装目录和容器层

### 11.2 Git 与文件所有权

- 服务器侧工作分支建议使用 `work/server`。
- 本机侧工作分支建议使用 `work/local`。
- 服务器主要负责 `src/sim`、`src/reconstruction`、`src/data`、策略训练和服务器脚本。
- 本机主要负责输入采集、轻量标定、消息定义和本地使用文档。
- `hand_msgs`、`docs/interfaces.md`、坐标系和 schema 属于共享契约；修改前后必须单独提交并通知另一端。
- 大文件不进入普通 Git 历史；使用下载脚本、对象存储或 manifest。

### 11.3 每次交接更新

服务器 Codex维护 `docs/handoff/server_latest.md`：

```text
更新时间：
Git commit：
服务器环境版本：
本次输入及 checksum：
完成内容：
测试和指标：
生成产物：
已知问题：
本机需要配合：
下一步：
```

## 12. 服务器 Codex 的首个任务

收到本文件后，按以下顺序开始：

1. 只读审计服务器 GPU、内存、系统盘、数据盘、驱动、容器和网络。
2. 找出真实持久化数据盘并提出目录/缓存布局。
3. 输出 `docs/server_environment.md` 初稿和风险清单。
4. 如果满足验收条件，创建仓库骨架、数据盘目录和环境配置。
5. 完成容器内 GPU smoke test。
6. 进入第1周最小 Isaac Sim headless 闭环。

如果数据盘不足、驱动异常、GPU 不符或实例关机不保留磁盘，应先报告阻塞和最小修复方案，不要把大型依赖安装到系统盘临时绕过。
