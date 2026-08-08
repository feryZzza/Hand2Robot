# Git workflow

## Branches

- `main`: stable, reviewed integration history and release source.
- `work/local`: integration branch for capture, lightweight calibration, messages, tests, and
  local documentation.
- `work/server`: integration branch for simulation, reconstruction, data, training, and server
  scripts.
- `feature/<area>-<topic>` and `fix/<area>-<topic>`: optional short-lived branches based on the
  appropriate integration branch.

Shared branches are updated with fast-forward pulls. Force-pushes and history rewrites are not
allowed. Cross-machine work enters `main` only after interface compatibility and relevant tests
have been checked.

## Commit policy

Use a short imperative subject in this form:

```text
type(scope): summary
```

Recommended types are `feat`, `fix`, `test`, `docs`, `chore`, `refactor`, and `contract`.
Changes to messages, schema, frames, units, timestamps, or joint ordering use `contract:` and
must include updated examples and tests in the same commit. Dependent implementation follows in
a later commit so either side can adopt the contract independently.

Each commit should represent one reviewable behavior. Generated output and unrelated formatting
must not be mixed with functional changes.

## Sync sequence

Before work:

```bash
git fetch origin --prune
git status --short --branch
git pull --ff-only
```

Before sharing:

```bash
make doctor
git diff --check
git status --short
```

Run the relevant test target once it exists, update `docs/project_memory.md` and the responsible
handoff, commit, then push the current integration branch. Never use `rsync` to synchronize the
Git checkout.

## Large files and experiment evidence

Git tracks source, lock files, configuration, small fixtures, manifests, checksums, metrics
summaries, plots needed by documentation, and compressed release documentation. Bags, datasets,
videos, checkpoints, model files, caches, and ROS build products remain outside Git.

Each experiment has `runs/<run_id>/manifest.yaml` containing at least:

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

## Tags and releases

- Use annotated tags `week-01`, `week-02`, and so on only for verified weekly milestones.
- Use semantic release tags beginning at `v0.1.0`; reserve `v1.0.0` for the final reproducible
  portfolio release.
- A release tag must point to `main` and include test results, environment summary, data/model
  manifests, known limitations, and reproduction steps.
