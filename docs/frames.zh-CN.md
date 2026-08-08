[English](frames.md) | [简体中文](frames.zh-CN.md)

# 坐标系

状态：M1 已接受，坐标系契约版本 `0.1.0`。

## 记号与坐标轴

`T_A_B` 把坐标系 `B` 中表达的坐标映射到坐标系 `A`：

```text
p_A = T_A_B * p_B
T_A_C = T_A_B * T_B_C
```

在 TF2 中，发布时以 `A` 为父坐标系、`B` 为子坐标系。存储的标定键使用相同的
`parent_frame`、`child_frame` 和 `T_parent_child` 方向；逆变换必须显式计算，不能从
文件名猜测。

所有三维坐标系均为右手系，所有平移均使用米。机器人/世界坐标系遵循 ROS REP-103
机体轴：`x` 向前、`y` 向左、`z` 向上。摄像头光学坐标系遵循 ROS 光学约定：`x` 在
图像中向右、`y` 向下、`z` 沿镜头向前。ROS 消息中的旋转使用单位四元数，配置和
计算中的角度使用弧度。

二维图像坐标不是 TF 坐标系。原点位于左上角像素中心，`x` 向右增长、`y` 向下增长，
不得进行隐式图像镜像。

## 坐标系树

```text
world
└── robot_base
    ├── camera_optical_frame
    │   └── human_wrist
    └── robot_ee
        └── robot_hand_base
            └── <robot finger link frames>
```

| 坐标系 | 父坐标系 | 变换 | 所有者 |
|---|---|---|---|
| `world` | 无 | 固定仿真参考 | 仿真器 |
| `robot_base` | `world` | 每个场景固定 | 仿真器/资产配置 |
| `camera_optical_frame` | `robot_base` | 在一次标定运行中固定 | 标定模块 |
| `human_wrist` | `camera_optical_frame` | 动态观测 | 重建适配器 |
| `robot_ee` | `robot_base` | 动态正运动学 | 机器人/仿真器 |
| `robot_hand_base` | `robot_ee` | 由所选资产固定 | 机器人清单 |
| 手指 link 坐标系 | `robot_hand_base` 层级 | 动态运动学 | 机器人/仿真器 |

以上名称是规范逻辑名称。只有通过经过检查的配置映射才能使用机器人专用别名；接口
消息仍应标识实际配置的坐标系。

## 重定向变换

手部三维点从 `camera_optical_frame` 输入。标定提供
`T_robot_base_camera_optical`，因此直接腕部目标按以下顺序计算：

```text
p_robot_base = T_robot_base_camera_optical * p_camera_optical
```

手指重定向首先根据 `docs/interfaces.md` 中固定的关节顺序构建解剖学手掌局部基，随后
去除全局腕部平移/旋转并应用配置的手部尺度。最终机器人命令始终在 `robot_base` 中
表达。

## 左右手与镜像

`LEFT` 和 `RIGHT` 表示人的解剖学左右手。摄像头预览镜像必须在输入适配器边界撤销。
把人的左手映射到机器人的右手时，必须使用具名、可配置的反射/映射步骤并添加诊断
注释，绝不能隐藏在通用变换中。

## 标定记录

每个摄像头到机器人的标定文件必须包含：

```yaml
schema_version: 0.1.0
parent_frame: robot_base
child_frame: camera_optical_frame
translation_m: [x, y, z]
quaternion_xyzw: [x, y, z, w]
method: <method name>
source: <input/calibration asset>
created_at: <ISO-8601 timestamp>
residual_translation_m: <value>
residual_rotation_rad: <value>
```

消费者应拒绝非单位四元数、非有限值、未知坐标系、反向父子坐标系、不支持的 schema，
或超出声明有效条件的标定。

仓库中的 `synthetic_camera_to_robot_v0.1.json` 是单元测试固定样例，不是实测摄像头
标定。真实标定文件必须使用不同的数据源和实测残差。

## 必需测试

- `T_A_B` 的单位变换、逆变换和组合顺序；
- TF 链在配置平移/旋转容差内闭合；
- 检测米/毫米和弧度/角度混用；
- 四元数归一化和右手坐标基；
- 左右手关节标签映射；
- 摄像头像素约定不受预览镜像影响。
