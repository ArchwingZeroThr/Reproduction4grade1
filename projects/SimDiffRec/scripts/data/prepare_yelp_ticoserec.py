#!/usr/bin/env python3
"""Convert TiCoSeRec's published Yelp-A sequences to RecBole atomic format."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


UPSTREAM_REPOSITORY = "https://github.com/KingGugu/TiCoSeRec"
UPSTREAM_COMMIT = "302b2959f27bb16bb77acae5a471de82819bd1bd"
RAW_ROOT = f"https://raw.githubusercontent.com/KingGugu/TiCoSeRec/{UPSTREAM_COMMIT}/data/Yelp-A"
PAPER_TABLE1 = {"users": 30431, "items": 20033, "interactions": 316354}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--item-sequences", type=Path)
    parser.add_argument("--time-sequences", type=Path)
    parser.add_argument("--timeout", type=int, default=60)
    return parser.parse_args()


def sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def download(url: str, destination: Path, timeout: int) -> None:
    if destination.exists():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    part = destination.with_name(destination.name + ".part")
    part.unlink(missing_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "SimDiffRec-reproduction/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response, part.open("wb") as output:
            for chunk in iter(lambda: response.read(1024 * 1024), b""):
                output.write(chunk)
        os.replace(part, destination)
    except BaseException:
        part.unlink(missing_ok=True)
        raise


def write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    part.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(part, path)


def main() -> int:
    args = parse_args()
    root = args.storage_root.resolve()
    raw_dir = root / "raw" / "ticoserec-yelp-a"
    item_source = args.item_sequences.resolve() if args.item_sequences else raw_dir / "Yelp_item_org_rank.txt"
    time_source = args.time_sequences.resolve() if args.time_sequences else raw_dir / "Yelp_time_org_rank.txt"
    if not args.item_sequences:
        download(f"{RAW_ROOT}/Yelp_item_org_rank.txt", item_source, args.timeout)
    if not args.time_sequences:
        download(f"{RAW_ROOT}/Yelp_time_org_rank.txt", time_source, args.timeout)
    if not item_source.is_file() or not time_source.is_file():
        raise SystemExit("Both item and timestamp sequence files are required")

    dataset_id = "yelp"
    output_dir = root / "dataset" / dataset_id
    output_dir.mkdir(parents=True, exist_ok=True)
    inter_path = output_dir / f"{dataset_id}.inter"
    inter_part = inter_path.with_name(inter_path.name + ".part")
    users: Counter[str] = Counter()
    items: Counter[str] = Counter()
    interactions = 0
    minimum_timestamp: int | None = None
    maximum_timestamp: int | None = None

    try:
        with item_source.open("r", encoding="utf-8") as item_stream, time_source.open("r", encoding="utf-8") as time_stream, inter_part.open("w", encoding="utf-8", newline="\n") as output:
            output.write("user_id:token\tbusiness_id:token\tstars:float\tdate:float\n")
            item_lines = iter(item_stream)
            time_lines = iter(time_stream)
            line_number = 0
            while True:
                item_line = next(item_lines, None)
                time_line = next(time_lines, None)
                if item_line is None and time_line is None:
                    break
                line_number += 1
                if item_line is None or time_line is None:
                    raise ValueError("Item and time sequence files have different line counts")
                item_fields = item_line.split()
                time_fields = time_line.split()
                if len(item_fields) < 2 or len(item_fields) != len(time_fields):
                    raise ValueError(f"Invalid or misaligned sequence at line {line_number}")
                user = item_fields[0]
                if user != time_fields[0] or user in users:
                    raise ValueError(f"Mismatched or duplicate user at line {line_number}")
                for item, timestamp_text in zip(item_fields[1:], time_fields[1:]):
                    timestamp = int(timestamp_text)
                    output.write(f"{user}\t{item}\t1\t{timestamp}\n")
                    users[user] += 1
                    items[item] += 1
                    interactions += 1
                    minimum_timestamp = timestamp if minimum_timestamp is None else min(minimum_timestamp, timestamp)
                    maximum_timestamp = timestamp if maximum_timestamp is None else max(maximum_timestamp, timestamp)
    except BaseException:
        inter_part.unlink(missing_ok=True)
        raise

    statistics = {
        "users": len(users),
        "items": len(items),
        "interactions": interactions,
        "minimum_user_interactions": min(users.values(), default=0),
        "minimum_item_interactions": min(items.values(), default=0),
        "minimum_timestamp": minimum_timestamp,
        "maximum_timestamp": maximum_timestamp,
    }
    checks = {key: statistics[key] == value for key, value in PAPER_TABLE1.items()}
    core_check = statistics["minimum_user_interactions"] >= 5 and statistics["minimum_item_interactions"] >= 5
    if not all(checks.values()) or not core_check:
        inter_part.unlink(missing_ok=True)
        raise SystemExit(f"Yelp-A statistics failed: counts={checks}, five_core={core_check}")
    os.replace(inter_part, inter_path)

    item_sha, item_bytes = sha256_file(item_source)
    time_sha, time_bytes = sha256_file(time_source)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    manifest_path = root / "run-manifests" / f"prepare-yelp-{stamp}.json"
    manifest = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "ok",
        "dataset": dataset_id,
        "source": {
            "repository": UPSTREAM_REPOSITORY,
            "commit": UPSTREAM_COMMIT,
            "provenance_note": "TiCoSeRec README identifies Yelp-A as Yelp2020 with 316,354 interactions.",
            "item_sequences": {"path": str(item_source), "sha256": item_sha, "bytes": item_bytes},
            "time_sequences": {"path": str(time_source), "sha256": time_sha, "bytes": time_bytes},
        },
        "output": {"inter_path": str(inter_path)},
        "statistics": statistics,
        "paper_table1": {"target": PAPER_TABLE1, "count_checks": checks, "five_core_check": core_check},
    }
    write_json_atomic(manifest_path, manifest)
    manifest["manifest_path"] = str(manifest_path)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
