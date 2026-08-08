# ADR-0002: Use machine integration branches and manifest-based evidence

- Status: Accepted
- Date: 2026-08-08

## Context

Local capture/interface work and server simulation/training work can proceed independently, but
they must not diverge into incompatible projects. Heavy experimental artifacts do not belong in
ordinary Git history.

## Decision

Keep `main` stable, use `work/local` and `work/server` as machine-owned integration branches,
and isolate incomplete work on short-lived feature/fix branches when needed. Shared contract
changes use separate `contract:` commits. Never rewrite shared history.

Track code, configuration, documentation, small fixtures, metrics summaries, and experiment
manifests in Git. Store heavy artifacts externally and reference them by path, size, and SHA256.

## Consequences

Each machine can advance without copying whole working directories. Integration requires an
explicit contract check, and a commit alone cannot claim experimental success without a linked
manifest or test result.
