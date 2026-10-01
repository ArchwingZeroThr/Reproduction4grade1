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

`bootstrap.sh` creates an isolated virtual environment that reuses the image's CUDA-enabled PyTorch and installs the pinned Python dependencies. It then links large or generated directories to the persistent data disk.

## Deploy from Windows

After adding the local SSH public key to AutoDL and pushing this repository revision:

```powershell
powershell -ExecutionPolicy Bypass -File .\projects\SimDiffRec\scripts\autodl\deploy.ps1 `
  -HostName '<host from AutoDL SSH command>' `
  -Port <port from AutoDL SSH command> `
  -InstanceId 'simdiffrec-autodl-4090-01'
```

The deploy script uses key-based, non-interactive SSH. It clones the repository if absent, otherwise performs a fast-forward-only pull, and runs the idempotent bootstrap. The preflight report is saved as `simdiffrec/run-manifests/preflight-<InstanceId>.json`. It does not download datasets or start training.

## Preflight with data

After approved datasets have been converted to RecBole atomic files under `simdiffrec/dataset/<dataset-id>/`:

```bash
/root/autodl-tmp/envs/simdiffrec/bin/python \
  /root/autodl-tmp/Reproduction4grade1/projects/SimDiffRec/scripts/autodl/preflight.py \
  --project-root /root/autodl-tmp/Reproduction4grade1/projects/SimDiffRec \
  --storage-root /root/autodl-tmp/simdiffrec \
  --require-data
```

Formal run commands are added only after the final plan version, seeds, resource cap, and batches are approved.
