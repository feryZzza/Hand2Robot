[English](server_bootstrap.md) | [简体中文](server_bootstrap.zh-CN.md)

# GPU 服务器启动边界

目前没有任何服务器事实经过验证。在只读审计确认 GPU、持久化数据盘、可用空间、
容器运行时和恢复模型前，不得安装 Isaac Sim、HaMeR/MANO、数据集或训练环境。

在服务器上检出同一仓库并运行：

```bash
git switch work/server
./scripts/server_audit_readonly.sh | tee local_data/server_audit.txt
```

审查输出，并用实测值填写 `docs/handoff/server_latest.md`。任何大型安装前必须冻结：

1. 持久化项目/数据/缓存路径及最小可用空间策略；
2. NVIDIA 驱动、GPU、容器运行时及容器 GPU 访问；
3. Isaac Sim 版本、机器人/手部资产名称及许可证；
4. ROS2/bridge 与 schema `0.1.0` 的兼容性；
5. 快照、关机持久性、远程访问和产物传输行为。

## 摄像头/视频输入切换

服务器开始重建集成时不再强制要求连接实体摄像头。两种视觉来源发布相同的原始图像
topic：

```bash
# 已连接摄像头
ros2 launch hand_pipeline visual_input.launch.py \
  visual_input_mode:=camera camera_device:=0

# 服务器持久盘中的测试视频
ros2 launch hand_pipeline visual_input.launch.py \
  visual_input_mode:=video \
  video_path:=/persistent/data/hand_input.mp4 \
  loop_video:=true
```

连接 MediaPipe 或 HaMeR 前先运行 `make smoke-video-input`。随后让重建适配器在两种模式
下都订阅 `/visual/input/image_raw` 并发布 `/hand/observation/raw`。视频必须保存在持久
数据盘，并在运行 manifest 中记录 SHA256，绝不能加入 Git；还必须一同记录视频来源
摄像头及其匹配标定。

第一个服务器验收目标不是训练，而是一个 headless 场景：消费仓库内的录制序列，
用经过检查的机器人关节名和 IK 替换 CPU 原型执行器 manifest，运行 1000 个有界步，
记录状态，并通过五分钟 smoke。
