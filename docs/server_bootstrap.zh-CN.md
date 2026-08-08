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

第一个服务器验收目标不是训练，而是一个 headless 场景：消费仓库内的录制序列，
用经过检查的机器人关节名和 IK 替换 CPU 原型执行器 manifest，运行 1000 个有界步，
记录状态，并通过五分钟 smoke。
