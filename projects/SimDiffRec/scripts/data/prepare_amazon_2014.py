#!/usr/bin/env python3
"""Download and convert the Amazon 2014 5-core subsets for SimDiffRec."""

from __future__ import annotations

import argparse
import ast
import gzip
import hashlib
import json
import math
import os
import re
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SOURCE_PAGE = "https://cseweb.ucsd.edu/~jmcauley/datasets/amazon/links.html"
SOURCE_ROOT = "https://snap.stanford.edu/data/amazon/productGraph/categoryFiles"
DATASETS: dict[str, dict[str, Any]] = {
    "Beauty": {
        "dataset_id": "Amazon_Beauty",
        "filename": "reviews_Beauty_5.json.gz",
        "sha256": "e5925ec99023f1dc9c7d3dff7ef34cfeacd40d1b981b5525e1e4ba9c8abc18fe",
        "table1": {
            "users": 22363,
            "items": 12101,
            "interactions": 198502,
            "average_length": 8.8,
            "sparsity_percent": 99.93,
        },
    },
    "Toys_and_Games": {
        "dataset_id": "Amazon_Toys_and_Games",
        "filename": "reviews_Toys_and_Games_5.json.gz",
        "sha256": None,
        "table1": {
            "users": 19412,
            "items": 11924,
            "interactions": 167597,
            "average_length": 8.6,
            "sparsity_percent": 99.93,
        },
    },
    "Sports_and_Outdoors": {
        "dataset_id": "Amazon_Sports_and_Outdoors",
        "filename": "reviews_Sports_and_Outdoors_5.json.gz",
        "sha256": None,
        "table1": {
            "users": 35598,
            "items": 18357,
            "interactions": 296337,
            "average_length": 8.3,
            "sparsity_percent": 99.95,
        },
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download an official Amazon 2014 5-core review subset and stream it "
            "to a RecBole .inter file."
        )
    )
    parser.add_argument("--dataset", choices=sorted(DATASETS), default="Beauty")
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument(
        "--source-file",
        type=Path,
        help="Use an existing .json.gz instead of downloading (useful for an audited mirror).",
    )
    parser.add_argument(
        "--expected-sha256",
        help="Expected compressed-file SHA256; defaults to the known Beauty digest when available.",
    )
    parser.add_argument("--force-download", action="store_true")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument(
        "--allow-stat-mismatch",
        action="store_true",
        help="Publish output despite a Table 1 or 5-core mismatch (default: reject it).",
    )
    args = parser.parse_args()
    if args.source_file and args.force_download:
        parser.error("--source-file and --force-download cannot be used together")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if args.expected_sha256:
        args.expected_sha256 = args.expected_sha256.lower()
        if not re.fullmatch(r"[0-9a-f]{64}", args.expected_sha256):
            parser.error("--expected-sha256 must contain exactly 64 hexadecimal characters")
    return args


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def download(url: str, destination: Path, timeout: int, force: bool) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not force:
        return {"downloaded": False, "resolved_url": url, "headers": {}}

    part = destination.with_name(destination.name + ".part")
    part.unlink(missing_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "SimDiffRec-reproduction/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response, part.open("wb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
            metadata = {
                "downloaded": True,
                "resolved_url": response.geturl(),
                "headers": {
                    key: value
                    for key, value in response.headers.items()
                    if key.lower() in {"content-length", "content-type", "etag", "last-modified"}
                },
            }
        os.replace(part, destination)
        return metadata
    except BaseException:
        part.unlink(missing_ok=True)
        raise


def parse_record(raw_line: str, line_number: int) -> tuple[dict[str, Any], str]:
    try:
        record = json.loads(raw_line)
        parser_name = "json"
    except json.JSONDecodeError:
        try:
            record = ast.literal_eval(raw_line)
            parser_name = "python_literal"
        except (SyntaxError, ValueError) as error:
            raise ValueError(f"Unable to parse source line {line_number}: {error}") from error
    if not isinstance(record, dict):
        raise ValueError(f"Source line {line_number} is not an object")
    return record, parser_name


def clean_token(value: Any, field: str, line_number: int) -> str:
    token = str(value)
    if not token or any(character in token for character in "\t\r\n"):
        raise ValueError(f"Invalid {field} at source line {line_number}")
    return token


def convert(source: Path, temporary_output: Path) -> dict[str, Any]:
    users: Counter[str] = Counter()
    items: Counter[str] = Counter()
    parsers: Counter[str] = Counter()
    interactions = 0
    blank_lines = 0
    output_digest = hashlib.sha256()

    temporary_output.parent.mkdir(parents=True, exist_ok=True)
    temporary_output.unlink(missing_ok=True)
    try:
        with gzip.open(source, "rt", encoding="utf-8") as input_stream, temporary_output.open("wb") as output:
            header = b"user_id:token\titem_id:token\trating:float\ttimestamp:float\n"
            output.write(header)
            output_digest.update(header)
            for line_number, raw_line in enumerate(input_stream, start=1):
                if not raw_line.strip():
                    blank_lines += 1
                    continue
                record, parser_name = parse_record(raw_line, line_number)
                try:
                    user = clean_token(record["reviewerID"], "reviewerID", line_number)
                    item = clean_token(record["asin"], "asin", line_number)
                    rating = float(record["overall"])
                    timestamp = int(record["unixReviewTime"])
                except (KeyError, TypeError, ValueError) as error:
                    raise ValueError(f"Invalid required field at source line {line_number}: {error}") from error
                if not math.isfinite(rating):
                    raise ValueError(f"Non-finite rating at source line {line_number}")

                row = f"{user}\t{item}\t{rating:g}\t{timestamp}\n".encode("utf-8")
                output.write(row)
                output_digest.update(row)
                users[user] += 1
                items[item] += 1
                parsers[parser_name] += 1
                interactions += 1
    except BaseException:
        temporary_output.unlink(missing_ok=True)
        raise

    user_count = len(users)
    item_count = len(items)
    sparsity = 100.0 * (1.0 - interactions / (user_count * item_count))
    return {
        "interactions": interactions,
        "users": user_count,
        "items": item_count,
        "minimum_user_interactions": min(users.values(), default=0),
        "minimum_item_interactions": min(items.values(), default=0),
        "average_sequence_length": interactions / user_count,
        "sparsity_percent": sparsity,
        "blank_source_lines": blank_lines,
        "parser_counts": dict(sorted(parsers.items())),
        "inter_sha256": output_digest.hexdigest(),
        "inter_bytes": temporary_output.stat().st_size,
    }


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def main() -> int:
    args = parse_args()
    storage_root = args.storage_root.resolve()
    spec = DATASETS[args.dataset]
    dataset_id = spec["dataset_id"]
    source_url = f"{SOURCE_ROOT}/{spec['filename']}"

    if args.source_file:
        source_path = args.source_file.resolve()
        if not source_path.is_file():
            raise SystemExit(f"Source file does not exist: {source_path}")
        download_metadata = {"downloaded": False, "resolved_url": None, "headers": {}}
    else:
        source_path = storage_root / "raw" / "amazon-2014-5core" / spec["filename"]
        download_metadata = download(source_url, source_path, args.timeout, args.force_download)

    source_sha256, source_bytes = sha256_file(source_path)
    expected_sha256 = args.expected_sha256 or spec["sha256"]
    source_sha_match = None if expected_sha256 is None else source_sha256 == expected_sha256
    if source_sha_match is False:
        raise SystemExit(
            f"Compressed source SHA256 mismatch: expected {expected_sha256}, got {source_sha256}"
        )

    dataset_dir = storage_root / "dataset" / dataset_id
    inter_path = dataset_dir / f"{dataset_id}.inter"
    temporary_inter = inter_path.with_name(inter_path.name + ".part")
    statistics = convert(source_path, temporary_inter)

    target = spec["table1"]
    exact_checks = {
        key: statistics[key] == target[key] for key in ("users", "items", "interactions")
    }
    display_checks = {
        # Table 1 truncates average length to one decimal (e.g. Beauty 8.876 -> 8.8).
        "average_length": (
            math.floor(statistics["average_sequence_length"] * 10) / 10
            == target["average_length"]
        ),
        "sparsity_percent": (
            round(statistics["sparsity_percent"], 2) == target["sparsity_percent"]
        ),
    }
    core_check = (
        statistics["minimum_user_interactions"] >= 5
        and statistics["minimum_item_interactions"] >= 5
    )
    table1_match = all(exact_checks.values()) and all(display_checks.values()) and core_check
    publish = table1_match or args.allow_stat_mismatch
    if publish:
        os.replace(temporary_inter, inter_path)
    else:
        temporary_inter.unlink(missing_ok=True)

    run_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    manifest_path = storage_root / "run-manifests" / f"prepare-{dataset_id}-{run_stamp}.json"
    manifest = {
        "schema_version": 1,
        "created_at_utc": utc_now(),
        "status": "ok" if table1_match else ("published_with_mismatch" if publish else "rejected"),
        "dataset": args.dataset,
        "recbole_dataset_id": dataset_id,
        "source": {
            "dataset_version": "Amazon Reviews 2014 5-core",
            "source_page": SOURCE_PAGE,
            "requested_url": source_url if not args.source_file else None,
            "resolved_url": download_metadata["resolved_url"],
            "local_path": str(source_path),
            "downloaded_this_run": download_metadata["downloaded"],
            "response_headers": download_metadata["headers"],
            "sha256": source_sha256,
            "expected_sha256": expected_sha256,
            "sha256_match": source_sha_match,
            "bytes": source_bytes,
        },
        "output": {
            "path": str(inter_path),
            "published": publish,
            "format": "RecBole atomic interaction file",
            "columns": ["user_id:token", "item_id:token", "rating:float", "timestamp:float"],
        },
        "statistics": statistics,
        "paper_table1": {
            "target": target,
            "exact_count_checks": exact_checks,
            "display_value_checks": display_checks,
            "average_length_display_rule": "truncate to one decimal",
            "sparsity_display_rule": "round to two decimals",
            "five_core_check": core_check,
            "strict_match": table1_match,
        },
    }
    write_json_atomic(manifest_path, manifest)
    manifest["manifest_path"] = str(manifest_path)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if table1_match else 3


if __name__ == "__main__":
    raise SystemExit(main())
