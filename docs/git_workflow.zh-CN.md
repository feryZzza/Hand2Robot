[English](git_workflow.md) | [简体中文](git_workflow.zh-CN.md)

# Git 工作流

## 分支

- `main`：稳定、经过审查的集成历史和发布来源。
- `work/local`：采集、轻量标定、消息、测试和本地文档的集成分支。
- `work/server`：仿真、重建、数据、训练和服务器脚本的集成分支。
- `feature/<area>-<topic>` 与 `fix/<area>-<topic>`：基于对应集成分支创建的可选短期分支。

共享分支通过快进方式更新。禁止强制推送和改写历史。只有检查接口兼容性并通过相关
测试后，跨机器工作才能进入 `main`。

## 提交策略

使用以下格式的简短祈使句主题：

```text
type(scope): summary
```

推荐类型包括 `feat`、`fix`、`test`、`docs`、`chore`、`refactor` 和 `contract`。消息、
schema、坐标系、单位、时间戳或关节顺序的修改使用 `contract:`，并在同一提交中更新
示例和测试。依赖该契约的实现放在后续提交中，便于两侧独立采用契约。

每个提交应只代表一个可审查行为。不得把生成输出或无关格式化混入功能修改。

## 双语文档策略

除原本就是中文的 `doc/` 需求文档外，每份英文 Markdown 文档都要在同目录下提供
`.zh-CN.md` 译本。两个文件都以双向语言链接开头，并且必须同步更新。
`test_documentation_i18n.py` 会强制检查文档配对和语言切换规则。

## 同步顺序

开始工作前：

```bash
git fetch origin --prune
git status --short --branch
git pull --ff-only
```

共享前：

```bash
make doctor
git diff --check
git status --short
```

相关测试目标存在后应执行该目标，更新 `docs/project_memory.md` 和对应交接文件，提交，
再推送当前集成分支。绝不能使用 `rsync` 同步 Git 工作区。

## 大文件与实验证据

Git 跟踪源码、锁文件、配置、小型固定样例、manifest、校验和、指标摘要、文档所需图表
和压缩发布文档。bag、数据集、视频、checkpoint、模型文件、缓存和 ROS 构建产物保留
在 Git 之外。

每次实验在 `runs/<run_id>/manifest.yaml` 中至少记录：

```yaml
run_id: <date>_<task>_<variant>_<seed>
git_commit: <sha>
config: <path>
data_version: <name>@<sha256>
hardware: <summary>
metrics: <paths>
artifacts: <paths_and_hashes>
decision: keep | reject | rerun
reason: <short explanation>
```

## 标签与发布

- 只有已验证的周里程碑才使用注释标签 `week-01`、`week-02` 等。
- 从 `v0.1.0` 开始使用语义化发布标签；`v1.0.0` 保留给最终可复现作品集版本。
- 发布标签必须指向 `main`，并包含测试结果、环境摘要、数据/模型 manifest、已知限制和
  复现步骤。
