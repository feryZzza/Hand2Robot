# GPU server bootstrap boundary

No server facts have been verified yet. Do not install Isaac Sim, HaMeR/MANO, datasets, or
training environments until the read-only audit proves the GPU, persistent data disk, free
space, container runtime, and recovery model.

On the server, check out the same repository and run:

```bash
git switch work/server
./scripts/server_audit_readonly.sh | tee local_data/server_audit.txt
```

Review the output and populate `docs/handoff/server_latest.md` with measured values. Before any
large install, freeze:

1. the persistent project/data/cache paths and minimum free-space policy;
2. NVIDIA driver, GPU, container runtime, and container GPU access;
3. Isaac Sim version and robot/hand asset names plus licenses;
4. ROS2/bridge compatibility with schema `0.1.0`;
5. snapshot, shutdown persistence, remote access, and artifact transfer behavior.

The first server acceptance target is not training. It is a headless scene that consumes the
committed recorded sequences, replaces the CPU prototype actuator manifest with checked robot
joint names and IK, runs 1000 bounded steps, records state, and survives a five-minute smoke.
