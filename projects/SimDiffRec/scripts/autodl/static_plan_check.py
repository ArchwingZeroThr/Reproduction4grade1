#!/usr/bin/env python3
"""Parse every approved config and dataset without running a model forward pass."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


PLANS = (
    ("Amazon_Beauty", "conf/config_d_Amazon_Beauty.yaml", ("configs/repro/amazon_inter_only.yaml",)),
    ("Amazon_Toys_and_Games", "conf/config_d_Amazon_Toys_and_Games.yaml", ("configs/repro/amazon_inter_only.yaml", "configs/repro/dropout_05.yaml")),
    ("Amazon_Sports_and_Outdoors", "conf/config_d_Amazon_Sports_and_Outdoors.yaml", ("configs/repro/amazon_inter_only.yaml", "configs/repro/dropout_05.yaml")),
    ("yelp", "conf/config_d_yelp.yaml", ("configs/repro/yelp_inter_only.yaml",)),
    ("ml-1m", "conf/config_d_ml-1m.yaml", ("configs/repro/ml1m_paper_length.yaml",)),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--instance-id", required=True)
    return parser.parse_args()


def write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    part.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(part, path)


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    storage_root = args.storage_root.resolve()
    os.chdir(project_root)
    sys.path.insert(0, str(project_root))
    # Prevent RecBole from interpreting this checker's own command-line flags.
    sys.argv = [sys.argv[0]]

    import torch
    from recbole.config import Config
    from recbole.data import create_dataset

    gpu_bytes = torch.cuda.get_device_properties(0).total_memory
    reports = []
    for dataset_id, dataset_config, extras in PLANS:
        config_files = [dataset_config, "configs/repro/paper_runtime.yaml", "configs/repro/full.yaml", *extras]
        config = Config(
            model="SimDiff",
            dataset=dataset_id,
            config_file_list=config_files,
            config_dict={
                "data_path": str(storage_root / "dataset") + "/",
                "checkpoint_dir": str(storage_root / "static-check-checkpoints" / dataset_id),
                "seed": 42,
            },
        )
        dataset = create_dataset(config)
        batch_size = int(config["train_batch_size"])
        max_length = int(config["MAX_ITEM_LIST_LENGTH"])
        item_count = int(dataset.item_num)
        one_dense_tensor_bytes = batch_size * max_length * item_count * 4
        # A conservative static proxy for simultaneous logits/probabilities,
        # semantic-similarity tensors, gradients and temporary buffers.
        working_set_proxy_bytes = one_dense_tensor_bytes * 12
        reports.append({
            "dataset": dataset_id,
            "config_files": config_files,
            "users_in_recbole": int(dataset.user_num),
            "items_in_recbole_including_padding": item_count,
            "interactions_in_recbole": int(dataset.inter_num),
            "train_batch_size": batch_size,
            "max_sequence_length": max_length,
            "epochs": int(config["epochs"]),
            "learning_rate": float(config["learning_rate"]),
            "topk": list(config["topk"]),
            "valid_metric": str(config["valid_metric"]),
            "one_dense_tensor_bytes": one_dense_tensor_bytes,
            "working_set_proxy_bytes": working_set_proxy_bytes,
            "working_set_proxy_fraction_of_gpu": working_set_proxy_bytes / gpu_bytes,
            "static_resource_check": working_set_proxy_bytes < gpu_bytes,
        })

    if not all(report["static_resource_check"] for report in reports):
        raise SystemExit("Static resource proxy exceeds GPU memory for at least one dataset")
    payload = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "ok",
        "check_type": "config_and_dataset_parse_only_no_model_forward",
        "instance_id": args.instance_id,
        "gpu_name": torch.cuda.get_device_name(0),
        "gpu_total_bytes": gpu_bytes,
        "resource_proxy_note": "12 dense [batch,max_length,item_count] float32 tensors; heuristic, not a measured peak.",
        "datasets": reports,
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = storage_root / "run-manifests" / f"static-plan-check-{args.instance_id}-{stamp}.json"
    write_json_atomic(output, payload)
    payload["manifest_path"] = str(output)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
