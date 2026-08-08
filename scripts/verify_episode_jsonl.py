#!/usr/bin/env python3
"""Validate the finite local EpisodeRecord JSONL artifact."""

import json
from pathlib import Path
import sys


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: verify_episode_jsonl.py PATH EXPECTED_COUNT")
    path = Path(sys.argv[1])
    expected_count = int(sys.argv[2])
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    if len(records) != expected_count:
        raise ValueError(f"expected {expected_count} records, found {len(records)}")
    if [record["step_index"] for record in records] != list(range(expected_count)):
        raise ValueError("step indexes are not contiguous")
    if any(record["observation_missing"] or record["action_missing"] for record in records):
        raise ValueError("normal smoke contains a missing observation or action")
    if any(
        record["observation"]["sequence"] != record["action"]["sequence"]
        for record in records
    ):
        raise ValueError("observation/action sequence mismatch")
    if any(not record["action"]["valid"] for record in records):
        raise ValueError("normal smoke contains an invalid action")
    if not records[-1]["episode_complete"] or not records[-1]["success"]:
        raise ValueError("final record does not mark a successful completed episode")
    print(
        json.dumps(
            {
                "episode_id": records[0]["episode_id"],
                "record_count": len(records),
                "first_sequence": records[0]["observation"]["sequence"],
                "last_sequence": records[-1]["observation"]["sequence"],
                "final_complete": records[-1]["episode_complete"],
                "final_success": records[-1]["success"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
