[English](README.md) | [简体中文](README.zh-CN.md)

# Hand2Robot

Hand2Robot 是一个为期八周的具身智能工程项目：将视觉人手观测转换为安全的机械臂
和灵巧手目标，在仿真中验证，并记录可复现的训练 episode。

```text
摄像头 / 录制数据 / 合成输入
                 -> 手部重建
                 -> 标定与重定向
                 -> IK 与安全限幅
                 -> ROS2 与 Isaac Sim
                 -> 版本化 episode 数据
```

## 当前状态

仓库目前已经具备经过验证的**本地 CPU 原型**。合成或录制的 21 关节输入会依次经过
校验、标定、手掌/尺度归一化、One Euro 滤波、工作空间与速度安全检查、
`RobotTarget` 发布、watchdog 降级，以及版本化 `EpisodeRecord` 持久化。本地机器有意
不安装 Isaac Sim、大型模型、数据集或训练环境。

从以下命令开始：

```bash
git clone https://github.com/feryZzza/Hand2Robot.git
cd Hand2Robot
make doctor
```

`make doctor` 是只读检查，会报告本地磁盘限制、ROS2 可用性、仓库状态和已连接的
摄像头设备。

构建并验证当前 CPU 基线：

```bash
make test-unit
make build-ros
make smoke-local
make smoke-recorded
make smoke-bag
make smoke-prototype
make smoke-prototype-recorded
make smoke-prototype-watchdog
```

基础 smoke 会启动确定性的 21 关节数据源和校验器，验证接收观测与 `RUNNING` 状态，
随后注入低置信度观测并验证 `DEGRADED` 诊断。默认使用仅限本机的 ROS2 domain 72；
如果该 domain 已被占用，可通过 `HAND2ROBOT_ROS_DOMAIN_ID` 覆盖。

`make smoke-recorded` 使用仓库内的五帧固定样例，通过同一校验器检查精确序列号、
数据源、有效数、无效数和丢帧数。

常规运行入口可以切换适配器，而不改变下游节点：

```bash
ros2 launch hand_pipeline input_pipeline.launch.py input_mode:=synthetic
ros2 launch hand_pipeline input_pipeline.launch.py input_mode:=recorded
```

`make smoke-bag` 会把原始固定样例录制成临时 SQLite3 rosbag，确认 bag 中恰好有五条
消息，再通过两个全新的校验器实例各回放一次。bag 和日志保存在被忽略的
`local_data/tmp/` 下。

三个原型 smoke 覆盖完整 CPU 链路：普通合成检查写入并验证 20 步 JSONL episode；
录制模式通过同一组下游节点精确产生序列 0–4；watchdog 检查会停止输入源，并要求
恰好产生一个无效的 `STALE_INPUT` 目标。预期输出见[本地复现指南](docs/reproduction.zh-CN.md)。

初始原型运行入口：

```bash
source /opt/ros/humble/setup.bash
source ros2_ws/install/setup.bash
ros2 launch hand_pipeline prototype_pipeline.launch.py input_mode:=synthetic
```

`/robot/target` 当前使用五个屈曲自由度的 CPU 测试清单。它刻意不充当真实的
Panda/Allegro 命令接口；服务器资产选择、IK、碰撞检查和 Isaac Sim 执行仍受服务器
审计门槛约束。

## 项目记录

- [当前项目记忆](docs/project_memory.zh-CN.md)
- [路线图与验收门槛](docs/roadmap.zh-CN.md)
- [Git 工作流](docs/git_workflow.zh-CN.md)
- [接口契约](docs/interfaces.zh-CN.md)
- [坐标系契约](docs/frames.zh-CN.md)
- [当前架构](docs/architecture.zh-CN.md)
- [录制序列格式](docs/recorded_sequence.zh-CN.md)
- [标定基础](docs/calibration.zh-CN.md)
- [CPU 重定向与安全](docs/retargeting.zh-CN.md)
- [本地复现](docs/reproduction.zh-CN.md)
- [服务器启动边界](docs/server_bootstrap.zh-CN.md)
- [架构决策](docs/decisions/README.zh-CN.md)
- [本地/服务器交接](docs/handoff/README.zh-CN.md)

原始中文执行指南和详细八周清单保留在 `doc/` 下，作为项目需求。

## 范围边界

本地 Ubuntu 22.04 机器负责 Git、采集、轻量 ROS2、MediaPipe 基线、短 bag 和 CPU
smoke。RTX 4090 服务器负责 Isaac Sim、HaMeR/MANO、数据集、训练、长时间集成测试和
大型产物。两侧共享相同的消息、坐标系、单位、schema 版本和 Git 历史。
