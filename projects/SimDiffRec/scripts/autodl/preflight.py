#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path


REQUIRED_MODULES = (
    "numpy",
    "pandas",
    "scipy",
    "sklearn",
    "yaml",
    "tqdm",
    "colorama",
    "colorlog",
    "tensorboard",
)


def module_version(name: str) -> str:
    module = importlib.import_module(name)
    return str(getattr(module, "__version__", "unknown"))


def git_value(project_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(project_root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--instance-id", required=True)
    parser.add_argument("--require-data", action="store_true")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    storage_root = args.storage_root.resolve()
    sys.path.insert(0, str(project_root))

    required_paths = (
        project_root / "run_recbole.py",
        project_root / "recbole" / "data" / "__init__.py",
        project_root / "recbole" / "model" / "sequential_recommender" / "simdiff.py",
        project_root / "conf",
    )
    missing_paths = [str(path) for path in required_paths if not path.exists()]
    if missing_paths:
        raise SystemExit(f"Missing required project paths: {missing_paths}")

    import torch
    from recbole.model.sequential_recommender.simdiff import SimDiff

    if SimDiff.__name__ != "SimDiff":
        raise SystemExit("Unexpected SimDiff import result")
    if not torch.cuda.is_available():
        raise SystemExit("CUDA is unavailable in PyTorch")

    dataset_root = storage_root / "dataset"
    interaction_files = sorted(str(path) for path in dataset_root.glob("*/*.inter"))
    if args.require_data and not interaction_files:
        raise SystemExit(f"No RecBole .inter files found under {dataset_root}")

    report = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "torch": torch.__version__,
        "torch_cuda": torch.version.cuda,
        "cuda_available": torch.cuda.is_available(),
        "gpu": torch.cuda.get_device_name(0),
        "gpu_count": torch.cuda.device_count(),
        "dependencies": {name: module_version(name) for name in REQUIRED_MODULES},
        "project_root": str(project_root),
        "storage_root": str(storage_root),
        "remote_instance_id": args.instance_id,
        "hostname": platform.node(),
        "interaction_files": interaction_files,
        "git_commit": git_value(project_root, "rev-parse", "HEAD"),
        "git_dirty": bool(git_value(project_root, "status", "--porcelain")),
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
