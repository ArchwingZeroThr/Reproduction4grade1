#!/usr/bin/env python3
"""Prepare the official GroupLens MovieLens 1M archive for RecBole."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.request
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


SOURCE_PAGE = "https://grouplens.org/datasets/movielens/1m/"
SOURCE_URL = "https://files.grouplens.org/datasets/movielens/ml-1m.zip"
ARCHIVE_SHA256 = "a6898adb50b9ca05aa231689da44c217cb524e7ebd39d264c56e2832f2c54e20"
PAPER_TABLE1 = {"users": 6040, "items": 3953, "interactions": 1000209}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--source-file", type=Path)
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


def download(destination: Path, timeout: int) -> None:
    if destination.exists():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    part = destination.with_name(destination.name + ".part")
    part.unlink(missing_ok=True)
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "SimDiffRec-reproduction/1.0"})
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
    source = args.source_file.resolve() if args.source_file else root / "raw" / "ml-1m" / "ml-1m.zip"
    if not args.source_file:
        download(source, args.timeout)
    if not source.is_file():
        raise SystemExit(f"Source file does not exist: {source}")
    archive_sha, archive_bytes = sha256_file(source)
    if archive_sha != ARCHIVE_SHA256:
        raise SystemExit(f"Archive SHA256 mismatch: expected {ARCHIVE_SHA256}, got {archive_sha}")

    dataset_id = "ml-1m"
    output_dir = root / "dataset" / dataset_id
    output_dir.mkdir(parents=True, exist_ok=True)
    inter_path = output_dir / f"{dataset_id}.inter"
    item_path = output_dir / f"{dataset_id}.item"
    inter_part = inter_path.with_name(inter_path.name + ".part")
    item_part = item_path.with_name(item_path.name + ".part")
    users: Counter[str] = Counter()
    rated_items: Counter[str] = Counter()
    movie_ids: set[str] = set()
    interactions = 0

    try:
        with zipfile.ZipFile(source) as archive, archive.open("ml-1m/ratings.dat") as ratings, inter_part.open("w", encoding="utf-8", newline="\n") as output:
            output.write("user_id:token\titem_id:token\trating:float\ttimestamp:float\n")
            for line_number, raw in enumerate(ratings, start=1):
                fields = raw.decode("latin-1").rstrip("\r\n").split("::")
                if len(fields) != 4:
                    raise ValueError(f"Invalid ratings.dat line {line_number}")
                user, item, rating, timestamp = fields
                output.write(f"{user}\t{item}\t{rating}\t{timestamp}\n")
                users[user] += 1
                rated_items[item] += 1
                interactions += 1

        with zipfile.ZipFile(source) as archive, archive.open("ml-1m/movies.dat") as movies, item_part.open("w", encoding="utf-8", newline="\n") as output:
            output.write("item_id:token\tgenre:token_seq\n")
            for line_number, raw in enumerate(movies, start=1):
                fields = raw.decode("latin-1").rstrip("\r\n").split("::")
                if len(fields) != 3:
                    raise ValueError(f"Invalid movies.dat line {line_number}")
                item, _title, genres = fields
                movie_ids.add(item)
                output.write(f"{item}\t{' '.join(genres.split('|'))}\n")
    except BaseException:
        inter_part.unlink(missing_ok=True)
        item_part.unlink(missing_ok=True)
        raise

    exact_source_checks = {
        "users": len(users) == PAPER_TABLE1["users"],
        "interactions": interactions == PAPER_TABLE1["interactions"],
    }
    if not all(exact_source_checks.values()):
        inter_part.unlink(missing_ok=True)
        item_part.unlink(missing_ok=True)
        raise SystemExit(f"Official archive statistics failed: {exact_source_checks}")
    os.replace(inter_part, inter_path)
    os.replace(item_part, item_path)

    statistics = {
        "users_in_ratings": len(users),
        "items_in_ratings": len(rated_items),
        "movie_metadata_rows": len(movie_ids),
        "maximum_movie_id": max(map(int, movie_ids)),
        "interactions": interactions,
        "minimum_user_interactions": min(users.values()),
        "minimum_item_interactions": min(rated_items.values()),
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    manifest_path = root / "run-manifests" / f"prepare-ml-1m-{stamp}.json"
    manifest = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "ok_with_documented_item_count_convention_gap",
        "dataset": dataset_id,
        "source": {
            "source_page": SOURCE_PAGE,
            "requested_url": SOURCE_URL,
            "local_path": str(source),
            "sha256": archive_sha,
            "expected_sha256": ARCHIVE_SHA256,
            "bytes": archive_bytes,
        },
        "output": {"inter_path": str(inter_path), "item_path": str(item_path)},
        "statistics": statistics,
        "paper_table1": {
            "target": PAPER_TABLE1,
            "exact_source_checks": exact_source_checks,
            "item_count_note": (
                "The paper reports 3,953 items. The official archive contains 3,883 movie metadata rows, "
                "3,706 items with ratings, and a maximum movie id of 3,952. The converter does not "
                "invent missing ids; the discrepancy is preserved for result interpretation."
            ),
        },
    }
    write_json_atomic(manifest_path, manifest)
    manifest["manifest_path"] = str(manifest_path)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
