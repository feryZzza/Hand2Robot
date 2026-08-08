[English](README.md) | [简体中文](README.zh-CN.md)

# Experiment provenance

Create one directory per run and commit only `manifest.yaml` and, when useful, `plan.md`. Metrics,
videos, logs, checkpoints, and other large artifacts stay on the server or artifact storage and
are referenced by checksum from the manifest.
