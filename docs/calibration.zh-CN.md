[English](calibration.md) | [简体中文](calibration.zh-CN.md)

# 标定基础

状态：M4 CPU 基础；尚未声称完成真实摄像头标定。

`hand2robot_core.geometry.RigidTransform` 实现 `docs/frames.md` 固定的方向约定：
`T_A_B` 把点从坐标系 `B` 映射到 `A`。它会验证平移为有限值、四元数为单位四元数，
支持点变换和求逆，并且只允许组合坐标系匹配的变换链。

`load_calibration` 读取包含坐标系契约所需字段的版本化 JSON 记录。它会拒绝不支持的
schema、与预期相反的坐标系、非单位四元数、不带时区的时间戳、无效残差，以及超出
配置工作空间界限的平移。该界限也能捕获常见的“把毫米当米”错误。

`configs/calibration/synthetic_camera_to_robot_v0.1.json` 仅为确定性测试固定样例：单位
旋转加 `[0.5, 0.0, 0.8]` 米平移。它不是实测硬件数据，绝不能作为真实机器人标定。
应用到录制腕点 `[0.0, 0.06, 0.45]` 后，会在 `robot_base` 中得到
`[0.5, 0.06, 1.25]`。

标定边界会变换所有有效三维点，并为被 mask 的点返回零值。下游 CPU 原型已经加入
尺度归一化、手掌基、滤波、工作空间与速率限制，以及 `RobotTarget` 发布。真实摄像头
标定、资产专用 IK 和碰撞验证仍待完成。
