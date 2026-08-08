[English](reproduction.md) | [简体中文](reproduction.zh-CN.md)

# 本地 CPU 原型复现

## 前置条件

- Ubuntu 22.04，已安装 ROS2 Humble 和 `colcon`；
- 仓库检出到可写路径，且 `/home` 至少有 15 GiB 可用空间；
- 不需要摄像头、GPU、模型下载、Python 虚拟环境或服务器访问。

先运行只读环境检查：

```bash
make doctor
```

## 完整验证

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

预期原型证据：

- 59 项无外部依赖的单元/契约/文档测试通过；
- 三个 ROS2 包全部构建成功；
- 合成模式产生 20 条包含有效有界目标的完整配对记录；
- 录制模式产生序列 0–4，共五条完整配对记录；
- 数据源中断产生恰好一个 `STALE_INPUT`、`valid=false` 目标；
- 每个 episode 脚本打印 JSONL 路径和 SHA256。

生成的日志、bag 和 episode 保留在被忽略的 `local_data/` 下。Git 只提交校验和、
指标、配置和 run manifest。

## 手动启动

```bash
source /opt/ros/humble/setup.bash
source ros2_ws/install/setup.bash
export ROS_LOCALHOST_ONLY=1
ros2 launch hand_pipeline prototype_pipeline.launch.py \
  input_mode:=synthetic \
  expected_steps:=100 \
  episode_output_path:="$PWD/local_data/artifacts/manual_episode.jsonl"
```

记录器以排他创建方式打开输出，拒绝覆盖已有 episode。每次运行应选择新路径。回放
历史数据时使用 `input_mode:=recorded`，并同时设置 `enforce_capture_age:=false`。

## 沙箱传输警告

即使设置 `ROS_LOCALHOST_ONLY=1`，网络隔离沙箱也可能让 Fast DDS 报告 `getifaddrs` 或
UDP socket 警告。已验证的本地测试仍通过可用本地传输完成通信。在沙箱外，如果完全
没有 topic，应把它视为真实 DDS 配置问题，并检查 `ROS_DOMAIN_ID`、RMW 选择和本机
限制设置。
