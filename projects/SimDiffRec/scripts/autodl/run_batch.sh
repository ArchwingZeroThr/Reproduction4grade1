#!/usr/bin/env bash
set -uo pipefail

usage() {
  printf '%s\n' \
    'Usage:' \
    '  run_batch.sh --output-dir DIR [--run-id ID] -- COMMAND [ARG ...]' \
    '' \
    'Runs one command while recording its combined log, exit code, UTC start/end' \
    'times, and one nvidia-smi snapshot at both the start and the end.'
}

output_dir=""
run_id=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir)
      [[ $# -ge 2 ]] || { echo "--output-dir requires a value" >&2; exit 2; }
      output_dir="$2"
      shift 2
      ;;
    --run-id)
      [[ $# -ge 2 ]] || { echo "--run-id requires a value" >&2; exit 2; }
      run_id="$2"
      shift 2
      ;;
    --)
      shift
      break
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

[[ -n "${output_dir}" ]] || { echo "--output-dir is required" >&2; exit 2; }
[[ $# -gt 0 ]] || { echo "A command is required after --" >&2; exit 2; }
command -v nvidia-smi >/dev/null 2>&1 || { echo "nvidia-smi is unavailable" >&2; exit 2; }

if [[ -z "${run_id}" ]]; then
  run_id="$(date -u +%Y%m%dT%H%M%SZ)-$$"
fi
[[ "${run_id}" =~ ^[A-Za-z0-9._-]+$ ]] || {
  echo "--run-id may contain only letters, digits, dot, underscore, and hyphen" >&2
  exit 2
}

mkdir -p "${output_dir}"
log_file="${output_dir}/${run_id}.log"
command_file="${output_dir}/${run_id}.command.txt"
exit_file="${output_dir}/${run_id}.exit-code"
started_file="${output_dir}/${run_id}.started-at"
ended_file="${output_dir}/${run_id}.ended-at"
gpu_start_file="${output_dir}/${run_id}.gpu-start.csv"
gpu_end_file="${output_dir}/${run_id}.gpu-end.csv"

for artifact in "${log_file}" "${command_file}" "${exit_file}" "${started_file}" \
  "${ended_file}" "${gpu_start_file}" "${gpu_end_file}"; do
  [[ ! -e "${artifact}" ]] || { echo "Refusing to overwrite: ${artifact}" >&2; exit 3; }
done

command_status=""
finalize() {
  local wrapper_status=$?
  trap - EXIT INT TERM
  nvidia-smi \
    --query-gpu=timestamp,index,uuid,name,utilization.gpu,memory.used,memory.total,power.draw,temperature.gpu \
    --format=csv >"${gpu_end_file}" 2>>"${log_file}" || true
  date -u +%Y-%m-%dT%H:%M:%SZ >"${ended_file}"
  if [[ -n "${command_status}" ]]; then
    printf '%s\n' "${command_status}" >"${exit_file}"
    exit "${command_status}"
  fi
  printf '%s\n' "${wrapper_status}" >"${exit_file}"
  exit "${wrapper_status}"
}
trap finalize EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

command_args=("$@")
printf '%q ' "${command_args[@]}" >"${command_file}"
printf '\n' >>"${command_file}"
date -u +%Y-%m-%dT%H:%M:%SZ >"${started_file}"
if ! nvidia-smi \
  --query-gpu=timestamp,index,uuid,name,utilization.gpu,memory.used,memory.total,power.draw,temperature.gpu \
  --format=csv >"${gpu_start_file}" 2>>"${log_file}"; then
  printf '%s\n' 'Initial nvidia-smi snapshot failed' | tee -a "${log_file}" >&2
  exit 4
fi

printf 'run_id=%s\nlog=%s\n' "${run_id}" "${log_file}"
"${command_args[@]}" 2>&1 | tee "${log_file}"
pipeline_status=("${PIPESTATUS[@]}")
command_status="${pipeline_status[0]}"
exit "${command_status}"
