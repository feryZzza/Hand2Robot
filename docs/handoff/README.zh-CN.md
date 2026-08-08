[English](README.md) | [简体中文](README.zh-CN.md)

# 机器交接记录

- `local_latest.md` 由本地机器工作维护。
- `server_latest.md` 由 GPU 服务器工作维护。

跨机器分析前，应核对 Git 提交、schema 版本、输入名称和校验和是否一致。完成有意义
的交接后，替换对应 latest 文件的内容；持久实验历史保存在 `runs/`、提交和发布说明中。
