[English](AGENTS.md) | [简体中文](AGENTS.zh-CN.md)

# Hand2Robot repository instructions

This file is the persistent operating contract for contributors and coding agents.

## Read before changing the project

1. Read `docs/project_memory.md` for the verified current state.
2. Read the relevant guide in `doc/` for local or server work.
3. Read `docs/interfaces.md` and `docs/frames.md` before changing a shared contract.
4. Read the latest file in `docs/handoff/` before work that crosses machines.

The canonical local workspace is `/home/fery/Hand2Robot`. Paths shown in older planning
documents are examples and must not override the actual checkout location.

## Engineering boundaries

- The local computer is a thin client, capture endpoint, and CPU ROS2 test endpoint.
- Keep Isaac Sim, HaMeR/MANO, training, full datasets, checkpoints, and large caches on
  the GPU server's persistent data disk.
- Do not use `sudo`, install system packages, expose ROS2 DDS to the public internet, or
  download large dependencies locally without explicit user approval.
- Keep at least 15 GB free on `/home`. If `/` falls below 3 GB free, stop local project
  processes and report the storage condition.
- Treat message fields, units, joint ordering, coordinate frames, timestamps, and schema
  versions as shared contracts. Contract changes require documentation and tests.

## Git workflow

- `main` is the stable integration branch.
- `work/local` is the local-machine integration branch.
- `work/server` is the GPU-server integration branch.
- Use short-lived `feature/<area>-<topic>` or `fix/<area>-<topic>` branches when a change
  cannot be completed and tested as one small integration commit.
- Pull shared branches with fast-forward-only behavior. Never force-push or rewrite shared
  history.
- Use Conventional Commit-style subjects. Shared-contract commits use the `contract:`
  type and must remain separate from dependent implementation changes.
- Do not commit credentials, machine-specific `.env` files, bags, datasets, videos,
  checkpoints, model weights, ROS build products, or generated caches.
- Push only coherent, verified milestones. Record the pushed commit in the appropriate
  handoff file.
- Every English Markdown project document outside the already-Chinese `doc/` requirements must
  have a same-directory `.zh-CN.md` translation. Keep the language switch on line 1 and update
  both versions in the same commit.

See `docs/git_workflow.md` for detailed branch and release rules.

## Persistent memory protocol

After a meaningful task:

1. Update verified state, risks, and next actions in `docs/project_memory.md`.
2. Add or supersede an ADR in `docs/decisions/` when an architectural decision changes.
3. Update the responsible machine's `docs/handoff/*_latest.md`.
4. Store experiment provenance in a tracked `runs/<run_id>/manifest.yaml`; keep heavy
   artifacts outside Git.
5. Run the relevant tests and `make doctor`, then inspect `git diff` and `git status`.

Do not write guesses as facts. Put unresolved items under “Pending verification” with a
clear validation action.
