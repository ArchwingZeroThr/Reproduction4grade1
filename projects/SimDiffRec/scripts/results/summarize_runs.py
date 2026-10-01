#!/usr/bin/env python3
"""Summarize a SimDiffRec batch from run_batch.sh artifacts."""

from __future__ import annotations

import argparse
import ast
import csv
import json
import math
import re
import statistics
from pathlib import Path


ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-dir", type=Path, required=True)
    return parser.parse_args()


def parse_result_line(log_path: Path, label: str) -> dict[str, float] | None:
    if not log_path.is_file():
        return None
    match_value = None
    for raw_line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = ANSI.sub("", raw_line)
        match = re.search(rf"{re.escape(label)}\s*:\s*(\{{.*\}})\s*$", line, re.IGNORECASE)
        if match:
            match_value = match.group(1)
    if match_value is None:
        return None
    value = ast.literal_eval(match_value)
    if not isinstance(value, dict):
        raise ValueError(f"{label} in {log_path} is not a mapping")
    return {str(key).lower(): float(metric) for key, metric in value.items()}


def read_text(path: Path) -> str | None:
    return path.read_text(encoding="utf-8").strip() if path.is_file() else None


def main() -> int:
    args = parse_args()
    batch_dir = args.batch_dir.resolve()
    plan_path = batch_dir / "plan.tsv"
    if not plan_path.is_file():
        raise SystemExit(f"Missing plan: {plan_path}")

    rows: list[dict] = []
    with plan_path.open("r", encoding="utf-8", newline="") as stream:
        for planned in csv.DictReader(stream, delimiter="\t"):
            run_id = planned["run_id"]
            exit_text = read_text(batch_dir / f"{run_id}.exit-code")
            log_path = batch_dir / f"{run_id}.log"
            rows.append({
                **planned,
                "exit_code": int(exit_text) if exit_text is not None else None,
                "started_at": read_text(batch_dir / f"{run_id}.started-at"),
                "ended_at": read_text(batch_dir / f"{run_id}.ended-at"),
                "valid": parse_result_line(log_path, "best valid"),
                "test": parse_result_line(log_path, "test result"),
                "log_path": str(log_path),
            })

    metric_names = sorted({metric for row in rows for metric in (row["test"] or {})})
    flat_rows = []
    for row in rows:
        flat = {key: row[key] for key in ("run_id", "dataset", "variant", "seed", "exit_code", "started_at", "ended_at")}
        for metric in metric_names:
            flat[metric] = (row["test"] or {}).get(metric)
        flat_rows.append(flat)

    csv_path = batch_dir / "run_results.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(flat_rows[0]) if flat_rows else ["run_id"])
        writer.writeheader()
        writer.writerows(flat_rows)

    aggregate_rows = []
    for dataset, variant in sorted({(row["dataset"], row["variant"]) for row in rows}):
        group = [row for row in rows if row["dataset"] == dataset and row["variant"] == variant]
        aggregate = {
            "dataset": dataset,
            "variant": variant,
            "planned_runs": len(group),
            "successful_runs": sum(row["exit_code"] == 0 and row["test"] is not None for row in group),
        }
        for metric in metric_names:
            values = [(row["test"] or {}).get(metric) for row in group]
            values = [value for value in values if value is not None and math.isfinite(value)]
            aggregate[f"{metric}_mean"] = statistics.fmean(values) if values else None
            aggregate[f"{metric}_std"] = statistics.stdev(values) if len(values) > 1 else (0.0 if values else None)
        aggregate_rows.append(aggregate)

    aggregate_path = batch_dir / "aggregate.csv"
    with aggregate_path.open("w", encoding="utf-8", newline="") as stream:
        fields = list(aggregate_rows[0]) if aggregate_rows else ["dataset", "variant"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(aggregate_rows)

    payload = {"batch_dir": str(batch_dir), "runs": rows, "aggregates": aggregate_rows}
    (batch_dir / "run_results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    completed = sum(row["exit_code"] is not None for row in rows)
    successful = sum(row["exit_code"] == 0 and row["test"] is not None for row in rows)
    failed = [row["run_id"] for row in rows if row["exit_code"] not in (None, 0) or (row["exit_code"] == 0 and row["test"] is None)]
    lines = [
        "# SimDiffRec batch summary", "",
        f"- Planned runs: {len(rows)}",
        f"- Finished runs: {completed}",
        f"- Successful runs with parsed test metrics: {successful}",
        f"- Failed or incomplete metric runs: {len(failed)}",
        f"- Failed run IDs: {', '.join(failed) if failed else 'none'}", "",
        "Machine-readable files: `run_results.json`, `run_results.csv`, and `aggregate.csv`.",
    ]
    (batch_dir / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"planned": len(rows), "finished": completed, "successful": successful, "failed": failed}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
