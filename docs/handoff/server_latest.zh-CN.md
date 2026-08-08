[English](server_latest.md) | [简体中文](server_latest.zh-CN.md)

# 服务器交接

- 更新时间：尚未提供
- Git 提交：尚未提供
- 服务器环境版本：尚未验证
- 输入与校验和：无

## 已完成

尚未收到经过验证的服务器工作交接。

## 测试与指标

等待只读服务器审计。

## 生成产物

尚未报告任何产物。

## 已知问题

服务器 GPU、RAM、磁盘、驱动、容器运行时、持久性、网络和恢复行为均未验证。

## 本地所需行动

在收到环境审计前无需行动。

## 已准备的审计入口

仓库已经包含 `scripts/server_audit_readonly.sh` 和 `docs/server_bootstrap.md`，它们不会
执行安装或配置修改。应在真实服务器上运行该脚本，并且只用实测输出替换此占位内容。

仓库还准备了带 `visual_input_mode:=camera|video` 的 `visual_input.launch.py`。本地视频
传输已验证，但这不代表服务器重建已经成功。在服务器运行 `make smoke-video-input`，
再让 MediaPipe 或 HaMeR 只连接一次 `/visual/input/image_raw`；代表性视频应留在持久
存储，并在此记录其校验和与匹配标定。

## 下一步

运行服务器指南中的只读审计，用实测值和风险替换本文件。
