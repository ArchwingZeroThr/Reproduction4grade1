#!/usr/bin/env bash
set -euo pipefail

project_root="${1:-/root/autodl-tmp/Reproduction4grade1/projects/SimDiffRec}"
python_bin="${SIMDIFFREC_BASE_PYTHON:-/root/miniconda3/bin/python}"
env_root="${SIMDIFFREC_ENV_ROOT:-/root/autodl-tmp/envs/simdiffrec}"
storage_root="${SIMDIFFREC_STORAGE_ROOT:-/root/autodl-tmp/simdiffrec}"

if [[ ! -f "${project_root}/run_recbole.py" ]]; then
  echo "Project not found: ${project_root}" >&2
  exit 2
fi

if [[ ! -x "${python_bin}" ]]; then
  echo "Python not found or not executable: ${python_bin}" >&2
  exit 2
fi

"${python_bin}" - <<'PY'
import sys

if sys.version_info[:2] != (3, 10):
    raise SystemExit(f"Python 3.10 is required, got {sys.version.split()[0]}")
PY

"${python_bin}" - <<'PY'
import torch

if not torch.cuda.is_available():
    raise SystemExit("The base image cannot access CUDA through PyTorch")
print(f"base_torch={torch.__version__}")
print(f"base_cuda={torch.version.cuda}")
print(f"gpu={torch.cuda.get_device_name(0)}")
PY

if [[ ! -x "${env_root}/bin/python" ]]; then
  "${python_bin}" -m venv --system-site-packages "${env_root}"
fi

"${env_root}/bin/python" -m pip install --disable-pip-version-check \
  --requirement "${project_root}/requirements-autodl.txt"

mkdir -p \
  "${storage_root}/dataset" \
  "${storage_root}/saved" \
  "${storage_root}/logs" \
  "${storage_root}/results" \
  "${storage_root}/run-manifests"

link_storage() {
  local link_path="$1"
  local target_path="$2"

  if [[ -L "${link_path}" ]]; then
    ln -sfn "${target_path}" "${link_path}"
    return
  fi
  if [[ -e "${link_path}" ]]; then
    echo "Refusing to replace existing non-symlink path: ${link_path}" >&2
    exit 3
  fi
  ln -s "${target_path}" "${link_path}"
}

link_storage "${project_root}/dataset" "${storage_root}/dataset"
link_storage "${project_root}/saved" "${storage_root}/saved"
link_storage "${project_root}/logs" "${storage_root}/logs"

"${env_root}/bin/python" "${project_root}/scripts/autodl/preflight.py" \
  --project-root "${project_root}" \
  --storage-root "${storage_root}"

echo "BOOTSTRAP_OK"
echo "environment=${env_root}"
echo "storage=${storage_root}"
