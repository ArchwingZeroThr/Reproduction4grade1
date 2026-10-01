# Reproduction execution configs

These small overlays are local execution-patch configs, not a complete configuration published by the SimDiffRec authors. Model constructor defaults are loaded from `recbole/properties/model/SimDiff.yaml`.

- `beauty_full.yaml`: author-snapshot training logic (`noise_mode: semantic`, `position_mode: confidence`).
- `beauty_wo_k_noise.yaml`: `noise_mode: gaussian` replaces similarity-neighbour embedding noise with `torch.randn_like(seq_emb)`. The paper names the ablation but does not specify executable public-code semantics, so standard Gaussian noise is a minimal paper-semantic assumption rather than an author-released setting.
- `beauty_wo_c_aug.yaml`: `position_mode: random` uses a random score tensor with the same shape as the confidence scores, keeps padding scores at zero like the full path, and selects the same fixed number of positions with `topk`.

All three overlays add `topk: [5, 10]` so the default RecBole metric set reports the paper's HR@5/10 and NDCG@5/10 targets (`Hit` is RecBole's HR key). Checkpoint selection deliberately remains the public code default `MRR@10`, because the paper does not disclose a different selection metric. Dataset, GPU, runtime, seed, and the upstream README model hyperparameters are intentionally not overridden here.

The formal P1/P2 batch also layers:

- `paper_runtime.yaml`: paper-stated 300 epochs, batch size 256, learning rate `1e-4`, GPU 0 and top-k 5/10.
- `amazon_inter_only.yaml` / `yelp_inter_only.yaml`: load only interaction columns because the selected auditable sources do not provide compatible item metadata and SimDiff does not consume it.
- `dropout_05.yaml`: paper-stated dropout for Toys and Sports.
- `ml1m_paper_length.yaml`: paper-stated maximum sequence length 200, overriding the public config's 50.

Beauty dropout remains 0.2 from the public README because the paper does not disclose a distinct value. Checkpoint selection remains RecBole's public default `MRR@10`. These choices are recorded as reconstruction assumptions, not silently described as an exact author configuration.
