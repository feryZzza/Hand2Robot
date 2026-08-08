[English](AGENTS.md) | [简体中文](AGENTS.zh-CN.md)

# Hand2Robot 仓库操作说明

本文件是面向贡献者和编码代理的持久操作契约。

## 修改项目前必须阅读

1. 阅读 `docs/project_memory.md`，了解已经验证的当前状态。
2. 根据本地或服务器任务，阅读 `doc/` 中对应的执行指南。
3. 修改共享契约前，阅读 `docs/interfaces.md` 和 `docs/frames.md`。
4. 进行跨机器工作前，阅读 `docs/handoff/` 中最新的交接文件。

本地规范工作区为 `/home/fery/Hand2Robot`。旧规划文档中的路径仅为示例，不能覆盖
实际检出位置。

## 工程边界

- 本地计算机的定位是薄客户端、采集端和 CPU ROS2 测试端。
- Isaac Sim、HaMeR/MANO、训练、完整数据集、checkpoint 和大型缓存必须放在 GPU
  服务器的持久化数据盘上。
- 未经用户明确批准，不得使用 `sudo`、安装系统包、向公网暴露 ROS2 DDS，或在本地
  下载大型依赖。
- `/home` 至少保留 15 GB 空间。如果 `/` 可用空间低于 3 GB，应停止本地项目进程并
  报告存储状态。
- 消息字段、单位、关节顺序、坐标系、时间戳和 schema 版本均视为共享契约。修改
  契约必须同时更新文档和测试。

## Git 工作流

- `main` 是稳定集成分支。
- `work/local` 是本地机器集成分支。
- `work/server` 是 GPU 服务器集成分支。
- 无法在一个小型集成提交中完成并验证的改动，应使用短期
  `feature/<area>-<topic>` 或 `fix/<area>-<topic>` 分支。
- 共享分支只能通过快进方式拉取。不得强制推送或改写共享历史。
- 提交主题遵循 Conventional Commits 风格。共享契约修改使用独立的 `contract:`
  类型提交，不得与依赖实现混在一起。
- 不得提交凭据、机器专用 `.env`、bag、数据集、视频、checkpoint、模型权重、ROS
  构建产物或生成缓存。
- 只推送内聚且经过验证的里程碑，并在对应交接文件中记录已推送的提交。
- 除原本就是中文的 `doc/` 需求文档外，每份英文 Markdown 项目文档都必须在同目录下
  提供 `.zh-CN.md` 译本。语言切换入口保持在首行，两个版本在同一提交中同步更新。

详细分支和发布规则见 `docs/git_workflow.md`。

## 持久项目记忆协议

完成有意义的任务后：

1. 在 `docs/project_memory.md` 中更新已验证状态、风险和下一步行动。
2. 架构决策发生变化时，在 `docs/decisions/` 中新增或取代 ADR。
3. 更新对应机器的 `docs/handoff/*_latest.md`。
4. 将实验来源记录到受 Git 跟踪的 `runs/<run_id>/manifest.yaml`；大型产物保留在
   Git 之外。
5. 运行相关测试和 `make doctor`，然后检查 `git diff` 与 `git status`。

不得把猜测写成事实。未解决事项放在“待验证”部分，并注明明确的验证动作。
