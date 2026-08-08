[English](0001-local-server-separation.md) | [简体中文](0001-local-server-separation.zh-CN.md)

# ADR-0001：分离本地交互与服务器计算

- 状态：已接受
- 日期：2026-08-08

## 背景

本地 Ubuntu 机器已安装 ROS2 Humble，CPU 资源足够，但 `/` 只有约 4.1 GiB 可用，
`/home` 约有 24 GiB 可用，没有可工作的本地 GPU 路径，初始审计也未检测到摄像头。
项目还需要 Isaac Sim、HaMeR/MANO、数据集和策略训练。

## 决策

本地机器负责 Git、SSH、采集、轻量 ROS2、合成/录制输入、条件允许时的 MediaPipe、
短 bag、标定测试、报告和 CPU smoke。RTX 4090 服务器的持久化数据盘负责仿真、大型
模型、数据集、训练、长时间测试、缓存和 checkpoint。

两侧通过 Git 跟踪的契约和校验和验证的小型数据传输连接。不得向公网暴露原始 ROS2
DDS。

## 后果

摄像头或服务器暂时不可用时，项目仍可继续。消息、坐标系、schema 和交接需要投入
更多版本管理工作，但也更容易复现故障，并形成更强的工程证据。
