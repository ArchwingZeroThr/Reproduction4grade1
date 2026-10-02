#!/usr/bin/env bash
set -uo pipefail

usage() {
  printf '%s\n' 'Usage: run_approved_plan.sh --project-root DIR --storage-root DIR --python PATH [--seeds 42,43,44] [--attempt N]'
}

project_root=""
storage_root=""
python_bin=""
seeds_csv="42,43,44"
attempt="1"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-root) project_root="$2"; shift 2 ;;
    --storage-root) storage_root="$2"; shift 2 ;;
    --python) python_bin="$2"; shift 2 ;;
    --seeds) seeds_csv="$2"; shift 2 ;;
    --attempt) attempt="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ -d "$project_root" ]] || { echo "Invalid --project-root" >&2; exit 2; }
[[ -d "$storage_root/dataset" ]] || { echo "Missing dataset root" >&2; exit 2; }
[[ -x "$python_bin" ]] || { echo "Invalid --python" >&2; exit 2; }
[[ "$seeds_csv" =~ ^[0-9]+(,[0-9]+)*$ ]] || { echo "Invalid --seeds" >&2; exit 2; }
[[ "$attempt" =~ ^[1-9][0-9]*$ ]] || { echo "Invalid --attempt" >&2; exit 2; }

IFS=',' read -r -a seeds <<<"$seeds_csv"
batch_id="simdiffrec-p1p2-$(date -u +%Y%m%dT%H%M%SZ)"
artifact_root="$storage_root/runs/$batch_id"
checkpoint_root="$storage_root/checkpoints/$batch_id"
mkdir -p "$artifact_root" "$checkpoint_root"
plan_file="$artifact_root/plan.tsv"
status_file="$artifact_root/batch.status"
printf 'run_id\tdataset\tvariant\tseed\n' >"$plan_file"
for seed in "${seeds[@]}"; do
  printf 'simdiffrec-Amazon_Beauty-full-s%s-a%s\tAmazon_Beauty\tfull\t%s\n' "$seed" "$attempt" "$seed" >>"$plan_file"
  printf 'simdiffrec-Amazon_Toys_and_Games-full-s%s-a%s\tAmazon_Toys_and_Games\tfull\t%s\n' "$seed" "$attempt" "$seed" >>"$plan_file"
  printf 'simdiffrec-Amazon_Sports_and_Outdoors-full-s%s-a%s\tAmazon_Sports_and_Outdoors\tfull\t%s\n' "$seed" "$attempt" "$seed" >>"$plan_file"
  printf 'simdiffrec-yelp-full-s%s-a%s\tyelp\tfull\t%s\n' "$seed" "$attempt" "$seed" >>"$plan_file"
  printf 'simdiffrec-ml-1m-full-s%s-a%s\tml-1m\tfull\t%s\n' "$seed" "$attempt" "$seed" >>"$plan_file"
  printf 'simdiffrec-Amazon_Beauty-beauty_wo_k_noise-s%s-a%s\tAmazon_Beauty\tbeauty_wo_k_noise\t%s\n' "$seed" "$attempt" "$seed" >>"$plan_file"
  printf 'simdiffrec-Amazon_Beauty-beauty_wo_c_aug-s%s-a%s\tAmazon_Beauty\tbeauty_wo_c_aug\t%s\n' "$seed" "$attempt" "$seed" >>"$plan_file"
done

summarize() {
  "$python_bin" "$project_root/scripts/results/summarize_runs.py" --batch-dir "$artifact_root" || true
}

fail_batch() {
  printf 'failed\n' >"$status_file"
  summarize
  exit 1
}

run_one() {
  local dataset="$1" variant="$2" seed="$3" dataset_config="$4" extra_configs="$5"
  local run_id="simdiffrec-${dataset}-${variant}-s${seed}-a${attempt}"
  local configs="$dataset_config configs/repro/paper_runtime.yaml configs/repro/${variant}.yaml"
  if [[ -n "$extra_configs" ]]; then
    configs="$configs $extra_configs"
  fi
  mkdir -p "$checkpoint_root/$run_id"
  (
    cd "$project_root" || exit 2
    bash scripts/autodl/run_batch.sh --output-dir "$artifact_root" --run-id "$run_id" -- \
      "$python_bin" run_recbole.py --model=SimDiff --dataset="$dataset" \
      --config_files="$configs" --seed="$seed" \
      --data_path="$storage_root/dataset/" --checkpoint_dir="$checkpoint_root/$run_id"
  )
}

printf 'running\n' >"$status_file"
for seed in "${seeds[@]}"; do
  run_one Amazon_Beauty full "$seed" conf/config_d_Amazon_Beauty.yaml configs/repro/amazon_inter_only.yaml || fail_batch
  run_one Amazon_Toys_and_Games full "$seed" conf/config_d_Amazon_Toys_and_Games.yaml 'configs/repro/amazon_inter_only.yaml configs/repro/dropout_05.yaml' || fail_batch
  run_one Amazon_Sports_and_Outdoors full "$seed" conf/config_d_Amazon_Sports_and_Outdoors.yaml 'configs/repro/amazon_inter_only.yaml configs/repro/dropout_05.yaml' || fail_batch
  run_one yelp full "$seed" conf/config_d_yelp.yaml configs/repro/yelp_inter_only.yaml || fail_batch
  run_one ml-1m full "$seed" conf/config_d_ml-1m.yaml configs/repro/ml1m_paper_length.yaml || fail_batch
  run_one Amazon_Beauty beauty_wo_k_noise "$seed" conf/config_d_Amazon_Beauty.yaml configs/repro/amazon_inter_only.yaml || fail_batch
  run_one Amazon_Beauty beauty_wo_c_aug "$seed" conf/config_d_Amazon_Beauty.yaml configs/repro/amazon_inter_only.yaml || fail_batch
done
printf 'completed\n' >"$status_file"
summarize
