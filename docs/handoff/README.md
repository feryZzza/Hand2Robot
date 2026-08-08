# Machine handoff records

- `local_latest.md` is maintained by local-machine work.
- `server_latest.md` is maintained by GPU-server work.

Before cross-machine analysis, verify that Git commit, schema version, input name, and checksum
match. Replace the contents of the relevant latest file after a meaningful handoff; durable
experiment history belongs in `runs/`, commits, and release notes.
