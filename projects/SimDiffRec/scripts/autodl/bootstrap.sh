#!/usr/bin/env bash
set -euo pipefail

project_root="${1:-/root/autodl-tmp/Reproduction4grade1/projects/SimDiffRec}"
python_bin="${SIMDIFFREC_BASE_PYTHON:-/root/miniconda3/bin/python}"
conda_bin="${SIMDIFFREC_CONDA_BIN:-/root/miniconda3/bin/conda}"
env_root="${SIMDIFFREC_ENV_ROOT:-/root/autodl-tmp/envs/simdiffrec}"
storage_root="${SIMDIFFREC_STORAGE_ROOT:-/root/autodl-tmp/simdiffrec}"
instance_id="${SIMDIFFREC_REMOTE_INSTANCE_ID:-}"
torch_version="${SIMDIFFREC_TORCH_VERSION:-2.1.2}"
torch_index_url="${SIMDIFFREC_TORCH_INDEX_URL:-https://download.pytorch.org/whl/cu118}"

if [[ -z "${instance_id}" ]]; then
  echo "SIMDIFFREC_REMOTE_INSTANCE_ID must identify this paper-specific AutoDL instance" >&2
  exit 2
fi
if [[ ! "${instance_id}" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "SIMDIFFREC_REMOTE_INSTANCE_ID contains unsupported characters: ${instance_id}" >&2
  exit 2
fi

if [[ ! -f "${project_root}/run_recbole.py" ]]; then
  echo "Project not found: ${project_root}" >&2
  exit 2
fi

if [[ ! -x "${python_bin}" || ! -x "${conda_bin}" ]]; then
  echo "Base Python or Conda is unavailable: ${python_bin}, ${conda_bin}" >&2
  exit 2
fi

if [[ ! -x "${env_root}/bin/python" ]]; then
  if "${python_bin}" -c 'import sys; raise SystemExit(sys.version_info[:2] != (3, 10))'; then
    "${python_bin}" -m venv --system-site-packages "${env_root}"
  else
    "${conda_bin}" create --yes --prefix "${env_root}" python=3.10 pip
  fi
fi

env_python="${env_root}/bin/python"
"${env_python}" -c 'import sys; raise SystemExit(sys.version_info[:2] != (3, 10))'

if ! "${env_python}" -c 'import torch' >/dev/null 2>&1; then
  "${env_python}" -m pip install --disable-pip-version-check \
    --index-url "${torch_index_url}" \
    "torch==${torch_version}"
fi

"${env_root}/bin/python" -m pip install --disable-pip-version-check \
  --requirement "${project_root}/requirements-autodl.txt"

"${env_python}" - <<'PY'
import torch

if not torch.cuda.is_available():
    raise SystemExit("The isolated environment cannot access CUDA through PyTorch")
print(f"torch={torch.__version__}")
print(f"torch_cuda={torch.version.cuda}")
print(f"gpu={torch.cuda.get_device_name(0)}")
PY

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

preflight_report="${storage_root}/run-manifests/preflight-${instance_id}.json"
"${env_python}" "${project_root}/scripts/autodl/preflight.py" \
  --project-root "${project_root}" \
  --storage-root "${storage_root}" \
  --instance-id "${instance_id}" | tee "${preflight_report}"

echo "BOOTSTRAP_OK"
echo "instance_id=${instance_id}"
echo "environment=${env_root}"
echo "storage=${storage_root}"
echo "preflight_report=${preflight_report}"
