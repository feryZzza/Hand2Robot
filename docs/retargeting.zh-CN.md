[English](retargeting.md) | [简体中文](retargeting.zh-CN.md)

# CPU 原型重定向

本地原型无需依赖 ROS2、NumPy、仿真器或 GPU 模型，就能把通过校验的 21 关节
`HandObservation` 转换成有界 `RobotTarget`。它是安全与集成目标，不代表物理机器人
或 Isaac Sim 资产已经投产。

## 几何与尺度

腕点是手掌局部原点。局部 x 轴从小指 MCP 指向食指 MCP；y 轴为经过正交化的腕点到
中指 MCP 方向；z 轴为 `x cross y`。坐标先除以食指 MCP 到小指 MCP 的距离，再按
配置的原型掌宽重新缩放。退化手掌和缺少必需关节都会以关闭方式失败。

左右手观测使用相同的解剖关节顺序。每个核心结果都会为左右手映射命名，例如
`left_to_right_anatomical`；手掌法线反射绝不会隐藏在通用摄像头变换中。

## 滤波与安全目标策略

One Euro 滤波器使用采集时间戳处理标定后的腕点。非递增时间戳会被拒绝。输出策略
随后执行以下检查：

1. 拒绝未来或过期输入；
2. 拒绝坐标系/标定不匹配和无效手掌几何；
3. 拒绝超出配置三维工作空间的腕点；
4. 根据源时间间隔限制已接受的笛卡尔和手指步长；
5. 单调 watchdog 到期时产生一个无效 `STALE_INPUT` 目标。

实时适配器执行采集到目标的年龄检查。离线回放保留历史采集时间，因此
`prototype_pipeline.launch.py input_mode:=recorded enforce_capture_age:=false` 只关闭跨
时钟年龄比较；时间戳顺序、基于源时间的速率限制和单调到达 watchdog 仍保持启用。

五个 `prototype_*_flexion` 关节组成所选本地 CPU 测试清单。它们是以弧度表示的有界
屈曲代理，不是 Panda、Allegro 或任何真实资产的命令。仿真或硬件执行前，服务器
适配器必须使用经过检查的机器人专用名称、限制、IK 和碰撞验证替换该清单。

规范配置：`configs/retargeting/cpu_prototype_v0.1.json`。确定性证据可通过以下命令
复现：

```bash
python3 scripts/evaluate_cpu_retargeting.py
make test-unit
```
