# Hand2Robot 具身智能实习项目：本机 Codex 执行指南

版本：1.0  
日期：2026-08-08  
适用环境：本机 Ubuntu 22.04  
项目周期：8 周

## 1. 使用方式

本文件是本机后续 Codex 工作的长期约束和执行清单。开始任何项目任务前先读取本文件，并以当前磁盘、环境和服务器交接状态为准。

本机的核心定位是“薄客户端 + 采集端 + 轻量 ROS2 测试端”，不是第二台训练服务器。

工作原则：

1. 计算留在4090服务器，交互和短数据采集留在本机。
2. 根分区空间保护优先于安装便利。
3. 代码通过 Git 同步，数据通过带校验的 rsync/rclone 同步。
4. 默认先使用短 rosbag 离线联调，后期才增加实时网关。
5. 不把本地和服务器发展成两个不兼容项目；统一接口、单位、坐标系和 schema。
6. 本机 Codex 不应未经用户明确同意执行 sudo、卸载软件、删除个人数据或修改分区。

## 2. 当前本机环境快照

检查日期：2026-08-08。每次开始大型任务前重新检查，因为数值可能变化。

| 项目 | 当前状态 | 项目判断 |
|---|---|---|
| Ubuntu | 22.04.5 LTS | 与 ROS2 Humble 匹配 |
| 根分区 `/` | 47 GB，总体使用约91%，剩余约4.2 GB | 红线，只允许轻量工作 |
| `/home` | 90 GB，剩余约23 GB | 项目新增内容最多8 GB |
| 内存 | 16 GB | 适合轻量 ROS2/MediaPipe，不适合 Isaac Sim |
| CPU | 20逻辑核 | 足够做编译、测试和轻量处理 |
| ROS2 | Humble 已安装 | 不重复安装 |
| 工具 | Git、SSH、rsync、ffmpeg、colcon 已安装 | 满足基本远程开发 |
| VS Code | Snap 版和 Remote SSH 扩展可用 | 作为远程编辑入口 |
| Cursor | 系统软件包已卸载 | 用户配置暂时保留 |
| Docker/Podman | 未安装 | 本机不安装 |
| Conda | Anaconda 已存在，约14 GB | 不再创建大型环境 |
| 摄像头 | 检查时没有 `/dev/video*` | 第2周前排查或先用录制/合成输入 |
| 本地 NVIDIA | `nvidia-smi` 无法连接驱动 | 不承担 GPU 主线 |

仍存在但尚未处理的低风险根分区候选：

- apt 下载缓存约714 MB。
- `/var/log` 约429 MB，主要是 Edge 重复日志。
- WPS 崩溃转储约77 MB。
- 旧 VS Code/Foxglove Snap 修订约663 MB。

清理脚本位于 `/home/fery/文档/root_cleanup_low_risk.sh`。只有用户在本机终端明确执行 `sudo bash` 时才运行；Codex 不自动尝试获取或处理用户密码。

## 3. 本机硬性边界

### 3.1 允许做

- VS Code Remote SSH 和终端 SSH。
- Git 分支、提交、代码审查和小型测试。
- ROS2 消息、topic、QoS、TF、状态机和诊断开发。
- 本地摄像头采集、MediaPipe 实时基线和短 rosbag。
- 坐标标定、尺度归一化、滤波、限幅和小型 IK 测试。
- CPU smoke test、指标绘图、报告和压缩视频预览。
- 上传样例数据、下载指标和压缩产物。

### 3.2 禁止做

- 本地安装 Isaac Sim。
- 本地安装 Docker/Podman 作为项目依赖。
- 新装完整 CUDA、TensorRT 或 GPU 训练环境。
- 下载 HaMeR、大型 VA 模型或完整公开数据集到本机。
- 将 checkpoints、完整 runs 或服务器缓存同步回本机。
- 在根分区空间不足时运行系统大升级。
- 将大文件写入 `/tmp`；本机 `/tmp` 与根分区共用文件系统。
- 将原始 ROS2 DDS 直接暴露到公网。

## 4. 本地空间和停止线

根分区规则：

| `/` 可用空间 | 动作 |
|---:|---|
| 大于6 GB | 可进行已有环境下的常规轻量开发 |
| 4–6 GB | 当前状态；禁止系统级安装和大型更新 |
| 3–4 GB | 暂停下载、Snap 更新和本地大编译 |
| 2–3 GB | 暂停本地项目进程，处理日志或缓存 |
| 小于2 GB | 停止项目工作，优先恢复系统空间 |

`/home` 规则：始终至少保留15 GB可用空间。项目新增总量上限为8 GB：

| 内容 | 上限 |
|---|---:|
| Git 仓库、ROS2 build/install/log | 1.5 GB |
| 唯一一个轻量 Python venv | 1.5 GB |
| 当前短 rosbag/样例 | 2 GB |
| 指标、图片、压缩视频、报告 | 2 GB |
| 临时文件和缓存 | 1 GB |

建议本机布局：

```text
/home/fery/文档/hand2robot/
├── src/
├── ros2_ws/
├── configs/
├── tests/
├── scripts/
├── docs/
├── local_data/
│   ├── samples/             # 当前短样例，最大2 GB
│   ├── artifacts/           # 指标和压缩结果
│   └── tmp/                 # 不使用根分区 /tmp
└── .venv/                   # 仅在确有需要时创建
```

如果需要本地 Python 包：

- 首选系统已有包或单一 `venv`，不新建 Conda 大环境。
- 临时目录指向 `/home/fery/文档/hand2robot/local_data/tmp`。
- pip 使用 `--no-cache-dir`，避免 wheel 和安装副本同时占空间。
- 遇到需要 CUDA、编译大型原生依赖或下载模型的包，改在服务器安装。

## 5. 每次本机工作前检查

Codex开始任务时至少确认：

```bash
df -hT / /home
du -sh /home/fery/文档/hand2robot 2>/dev/null || true
git -C /home/fery/文档/hand2robot status --short 2>/dev/null || true
pgrep -af microsoft-edge || true
find /dev -maxdepth 1 -name 'video*' -print
```

判断规则：

- 根分区低于3 GB时，不开始安装、下载或长时间采集。
- `/home` 低于15 GB时，先上传/归档本地样例和产物。
- Edge 持续运行且 syslog 增长时，提醒用户改用 Firefox或处理日志源。
- 工作区有未知未提交修改时，先识别归属，不覆盖用户改动。

## 6. 本机负责的统一接口

本机必须与服务器使用同一接口：

| 接口 | 最小字段 | 本机重点验证 |
|---|---|---|
| `HandObservation` | timestamp、handedness、2D/3D joints、confidence、frame_id | 时间单调、关节顺序、单位、低置信度 |
| `RobotTarget` | ee pose、finger joints、velocity limits、valid | 坐标系、限幅、无效目标行为 |
| `SystemStatus` | state、latency、drop rate、last_error | 至少1 Hz、故障可定位 |
| `EpisodeRecord` | observation、action、task、success、timestamps | schema 版本、多频率对齐和缺帧 mask |

所有单位、坐标、消息字段和关节顺序统一写入 `docs/interfaces.md` 和 `docs/frames.md`，不得散落在代码中。

## 7. 本机八周执行路线

### 准备阶段：薄客户端和交接通道

- 获取服务器 Codex 的 `docs/server_environment.md`。
- 确认服务器数据盘、Git 仓库路径和 SSH 入口。
- 建立本地 `hand2robot` 仓库骨架和 `work/local` 分支。
- 验证 SSH、Git、rsync 和1个小文件的 checksum 往返。
- 不在本机安装服务器环境。

### 第1周：接口和远程最小闭环支持

本机任务：

- 定义 `hand_msgs`、topic 名称、时间戳和 frame 规则。
- 实现合成 `HandObservation` 发布器和最小订阅测试。
- 编写 CPU 可运行的消息/配置测试。
- 接收服务器基线视频、topic 表和 metrics，检查格式。

本机交付：接口文档、合成输入样例、CPU 单元测试和 `local_latest.md`。

### 第2周：摄像头、MediaPipe 和 rosbag

- 排查摄像头权限、隐私开关或外接摄像头；若仍不可用，先用录制视频和合成输入。
- 实现实时相机、录制序列和合成输入三个适配器。
- 接入 MediaPipe，输出21关键点和置信度。
- 统计频率、掉帧、时间戳倒退和本地处理延迟。
- 录制20–30秒短 bag，不长期保存原始视频。
- 生成 checksum、schema 版本和 manifest 后上传服务器。

验收：三种输入只改配置；同一 bag 两次回放帧数一致；CPU 最小测试可运行。

### 第3周：标定、坐标和滤波

- 定义 camera、human_wrist、robot_base、robot_ee 等 frame。
- 编写外参配置加载、尺度归一化和左右手处理。
- 对 TF 链、单位、关节映射、限幅和 IK 边界写单元测试。
- 在3段短序列比较原始、低通和 One Euro 输出。
- 将标定文件、滤波配置和测试序列 manifest 交给服务器。

### 第4周：状态机和故障测试输入

- 实现或验证本地 `system_monitor`、heartbeat 和输入侧 watchdog。
- 生成时间戳倒退、掉帧、低置信度、输入中断等故障样例。
- 检查服务器回传的状态转换、恢复时间和延迟分解。
- 协助整理完整演示的输入侧画面和说明。

### 第5周：HaMeR/MANO 结果检查

本机不安装 HaMeR/MANO。只负责：

- 检查服务器回传的2D reprojection、mesh 叠加和失败案例。
- 对比 MediaPipe 与 HaMeR 输出接口是否一致。
- 整理遮挡、模糊、出画、左右手混淆和尺度问题。
- 将人工检查结果写入 `failure_cases.md`。

### 第6周：数据契约和策略报告

本机不保存完整训练数据和 checkpoint。只负责：

- 审查 episode schema、时间对齐图和 dataset card。
- 检查 train/val 是否按 episode 隔离。
- 汇总 BC/DP 曲线、成功率、样本数、显存和 GPU 小时。
- 生成报告所需图表和小体积视频。

### 第7周：作品集

- README 首屏、架构图、TF树、状态机图和指标表。
- 压缩2–3分钟演示视频。
- 5–8页技术报告。
- 系统/仿真版和算法/VA版简历材料。
- 扫描密钥、绝对路径和误提交大文件。

### 第8周：冻结和面试材料

- 基于固定短样例运行本地 CPU smoke test。
- 冻结接口、配置和报告数字。
- 整理问题库、岗位化讲稿和投递跟踪表。
- 本机只保留 release、短样例和最终压缩产物，其余留在服务器/对象存储。

## 8. 本地数据采集与传输规则

采集策略：

- 默认720p或更低，先验证再提高分辨率。
- 每次只录制20–60秒小样本。
- rosbag 输出明确写入 `/home/fery/文档/hand2robot/local_data/samples`，不使用 `/tmp`。
- 上传成功且服务器 checksum 一致后，只保留当前回归样例。
- 本地活动样例总量不得超过2 GB。

每个上传样例附带 manifest：

```yaml
name: <sample_name>
schema_version: <version>
source: camera | recorded | synthetic
duration_s: <seconds>
expected_frames: <count>
topics: <list>
frames: <coordinate frames>
units: <m/rad/pixel>
sha256: <hash>
notes: <lighting_occlusion_known_issues>
```

传输规则：

- 代码与配置只用 Git，不用 rsync 覆盖整个仓库。
- 样例使用支持断点续传的 rsync，并在两端验证 SHA256。
- 服务器结果只下载 `artifacts`、metrics、压缩视频和文档。
- 不使用 `rsync --delete`，除非用户明确批准并已检查目标路径。

## 9. 与服务器 Codex 的协作契约

建议分支：

- 本机：`work/local`
- 服务器：`work/server`
- 稳定集成：`main`

文件责任：

- 本机主责：`src/input`、轻量 `src/calibration`、`hand_msgs`、本地采集脚本和输入侧文档。
- 服务器主责：`src/sim`、`src/reconstruction`、`src/data`、训练、服务器启动脚本。
- 共享：`docs/interfaces.md`、`docs/frames.md`、消息定义、schema 和公共配置。

共享契约发生变化时：

1. 单独提交接口变化。
2. 在 commit message 中标明 `contract:`。
3. 更新样例与测试。
4. 另一侧合并契约提交后再继续依赖开发。

本机 Codex维护 `docs/handoff/local_latest.md`：

```text
更新时间：
Git commit：
根分区和 /home 余量：
本次采集输入：
完成内容：
本地测试：
上传文件及 checksum：
服务器需要执行：
已知问题：
下一步：
```

读取服务器的 `docs/handoff/server_latest.md` 后，先确认 Git commit、schema 和输入 checksum 是否匹配，再分析服务器结果。

## 10. 本机最低验收

| 项目 | 通过标准 |
|---|---|
| 磁盘 | 根分区不低于任务开始值，`/home` 至少15 GB可用 |
| 输入切换 | 实时、录制、合成输入只改配置 |
| 时间戳 | 单调，异常能被检测和记录 |
| 回放 | 同一 bag 两次回放帧数和主要输出一致 |
| 坐标 | 单位、关节顺序和 TF 链测试通过 |
| 安全 | 越界、低置信度和无效目标不产生危险命令 |
| CPU smoke | 不依赖本地 GPU，10分钟内完成 |
| 数据交接 | manifest、schema、checksum 完整 |

## 11. 本机 Codex 的首个任务

收到本文件后按以下顺序开展：

1. 检查 `/`、`/home`、工作区状态和服务器交接文件。
2. 不安装新系统软件。
3. 如果仓库尚不存在，创建轻量仓库骨架，但不下载模型和数据集。
4. 建立 `docs/interfaces.md`、`docs/frames.md` 和 handoff 模板。
5. 等服务器返回环境审计与最小仿真接口后，完成本地合成输入和消息测试。
6. 摄像头不可用时不阻塞主线，先使用录制或合成输入。

如果任务会让根分区下降、需要 sudo、需要新建大型环境或需要把服务器数据拉回本机，必须先报告预计占用和替代方案，获得用户明确同意后才能执行。
