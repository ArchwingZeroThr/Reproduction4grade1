# AutoDL deployment

This project uses an AutoDL instance only after the reproduction plan and batch are approved.

## Paper-specific instance binding

This deployment belongs only to SimDiffRec. Do not reuse its host, port, environment, storage paths, tmux sessions, or budget as defaults for another paper. A different paper may use a different AutoDL instance; even when two papers share one physical instance, each project must receive its own instance binding, environment, storage root, preflight report, run IDs, and budget record.

Every new or replaced instance must use a new `InstanceId` and rerun bootstrap/preflight. Connection parameters are supplied per deployment and are not committed. Passwords, private keys, and API tokens must never be written to a profile or manifest.

## Recommended instance

- GPU: one RTX 4090.
- Image: PyTorch 2.1.2, Python 3.10, CUDA 11.8.
- Persistent working root: `/root/autodl-tmp/`.
- Configure SSH public-key login. Do not save a password, API token, or private key in this repository.

## Layout

```text
/root/autodl-tmp/
  Reproduction4grade1/
  envs/simdiffrec/
  simdiffrec/
    dataset/
    saved/
    logs/
    results/
    run-manifests/
```

`bootstrap.sh` creates an isolated Python 3.10 environment and installs the pinned Python dependencies. With the recommended Python 3.10 image it reuses the image's CUDA-enabled PyTorch. If the rented image exposes another Python version, it creates a Conda environment on the data disk and installs PyTorch 2.1.2 with the CUDA 11.8 wheel instead of modifying the image's base environment. It then links large or generated directories to the persistent data disk.

## Deploy from Windows

After adding the local SSH public key to AutoDL and pushing this repository revision:

```powershell
powershell -ExecutionPolicy Bypass -File .\projects\SimDiffRec\scripts\autodl\deploy.ps1 `
  -HostName '<host from AutoDL SSH command>' `
  -Port <port from AutoDL SSH command> `
  -InstanceId 'simdiffrec-autodl-4090-01' `
  -IdentityFile "$env:USERPROFILE\.ssh\id_ed25519_autodl_simdiffrec"
```

The deploy script requires an explicit identity file and uses key-based, non-interactive SSH. It clones the repository if absent, otherwise performs a fast-forward-only pull, and runs the idempotent bootstrap. The preflight report is saved as `simdiffrec/run-manifests/preflight-<InstanceId>.json`. It does not download datasets or start training.

## Preflight with data

After approved datasets have been converted to RecBole atomic files under `simdiffrec/dataset/<dataset-id>/`:

```bash
/root/autodl-tmp/envs/simdiffrec/bin/python \
  /root/autodl-tmp/Reproduction4grade1/projects/SimDiffRec/scripts/autodl/preflight.py \
  --project-root /root/autodl-tmp/Reproduction4grade1/projects/SimDiffRec \
  --storage-root /root/autodl-tmp/simdiffrec \
  --instance-id 'simdiffrec-autodl-4090-01' \
  --require-data
```

Formal run commands are added only after the final plan version, seeds, resource cap, and batches are approved.

## B1 data preparation

The converter streams the compressed source, records compressed and converted
SHA256 digests and byte counts, checks the 5-core invariant, and requires the
paper Table 1 counts to match before publishing the `.inter` file. The Beauty
source also has a pinned known SHA256. Raw data, converted data, and the JSON
manifest remain under the persistent storage root.

```bash
cd /root/autodl-tmp/Reproduction4grade1/projects/SimDiffRec
/root/autodl-tmp/envs/simdiffrec/bin/python \
  scripts/data/prepare_amazon_2014.py \
  --dataset Beauty \
  --storage-root /root/autodl-tmp/simdiffrec
```

`--dataset` also accepts `Toys_and_Games` and `Sports_and_Outdoors`.

Prepare the other two sources with their audited converters:

```bash
/root/autodl-tmp/envs/simdiffrec/bin/python scripts/data/prepare_yelp_ticoserec.py \
  --storage-root /root/autodl-tmp/simdiffrec
/root/autodl-tmp/envs/simdiffrec/bin/python scripts/data/prepare_ml1m.py \
  --storage-root /root/autodl-tmp/simdiffrec
```

## Audited command wrapper

`run_batch.sh` does not add a training or evaluation loop. It wraps exactly the
provided command and saves its combined log, exit code, UTC start/end times,
and one `nvidia-smi` CSV snapshot at each boundary. Use a unique run ID and keep
the output directory on the persistent data disk.

```bash
bash scripts/autodl/run_batch.sh \
  --output-dir /root/autodl-tmp/simdiffrec/logs/b1 \
  --run-id example-static-approved-command \
  -- <approved-command> <approved-arguments>
```

## Formal P1/P2 batch

After all dataset manifests and static checks pass, launch the approved
three-seed P1/P2 plan as a server-side background job:

```bash
/root/autodl-tmp/envs/simdiffrec/bin/python scripts/autodl/static_plan_check.py \
  --project-root /root/autodl-tmp/Reproduction4grade1/projects/SimDiffRec \
  --storage-root /root/autodl-tmp/simdiffrec \
  --instance-id simdiffrec-694c4b90df-57cbe2fb
```

This parses all approved configs and datasets and records a conservative
tensor-size proxy; it does not construct the model or run a forward pass.

```bash
nohup bash scripts/autodl/run_approved_plan.sh \
  --project-root /root/autodl-tmp/Reproduction4grade1/projects/SimDiffRec \
  --storage-root /root/autodl-tmp/simdiffrec \
  --python /root/autodl-tmp/envs/simdiffrec/bin/python \
  --seeds 42,43,44 \
  > /root/autodl-tmp/simdiffrec/logs/approved-plan-launch.log 2>&1 </dev/null &
```

The plan runs one job at a time and stops at the first non-zero exit. It does
not poll the GPU periodically. Each run still writes its command, combined
log, true exit code, UTC start/end times, checkpoint directory, and start/end
GPU snapshots. Raw data, checkpoints, and full logs stay outside Git.
