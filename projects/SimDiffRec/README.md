# SimDiffRec



fork by https://github.com/Tokkiu/ECL

## Introduction

SimDiffRec: Semantic Similarity-Guided Diffusion for Contrastive Sequential Recommendation
The code is implemented based on DDPM, ECL-SR and CaDiRec.
Thank you for their valuable studies:)

Environment Dependencies
- Python
- Pytorch

## Dataset

Beauty, Toys and Sports(http://jmcauley.ucsd.edu/data/amazon/)

Yelp(https://www.yelp.com/dataset)

MovieLens(https://grouplens.org/datasets/movielen

## Run

```bash
python run_recbole.py --model=SimDiff --n_layers=2 --n_heads=2 --hidden_size=64 --inner_size=256 --hidden_act=gelu --initializer_range=0.02 --layer_norm_eps=1e-12 --attn_dropout_prob=0.2 --hidden_dropout_prob=0.2 --loss_type=CE --neg_sampling=None --mask_strategy=sample --mask_ratio=0.2 --encoder_loss_weight=1 --contrastive_loss_weight=0.001 --generate_loss_weight=0.2 --n_embedding=2 --n_sampling=5 --dataset=ml-1m --config_files=conf/config_d_ml-1m.yaml --gpu_id=1
```

### Hyperparameter

Hyperparameters for the proposed method are detailed in the paper, dataset-specific configurations are available in the `conf` directory, and all other parameters adhere to the default settings of the Recbole framework.

## Local Reproduction Project

- Research notes: [`Note.md`](../../../recsys-firstgrade/knowledge_base/paper/diffusion/SimDiffRec/Note.md)
- Reproduction plan: [`实验复现.md`](../../../recsys-firstgrade/knowledge_base/paper/diffusion/SimDiffRec/实验复现.md)
- Project status: [`STATUS.md`](../../../recsys-firstgrade/knowledge_base/paper/diffusion/SimDiffRec/STATUS.md)
- Upstream provenance: [`UPSTREAM.md`](UPSTREAM.md)

This directory is a source snapshot managed by the `Reproduction4grade1` monorepo. Do not initialize a nested Git repository here. Data, checkpoints, logs, and large artifacts are excluded by the monorepo `.gitignore`.

## AutoDL

AutoDL environment setup and the non-training deployment entry point are documented in [`AUTO_DL.md`](AUTO_DL.md). The bootstrap is idempotent and keeps datasets, checkpoints, logs, and results under `/root/autodl-tmp/`.
