# SimDiffRec upstream provenance

- Paper: *SimDiffRec: Semantic Similarity-Guided Diffusion for Contrastive Sequential Recommendation*
- Official repository: https://github.com/zingyon/SimDiffRec
- Imported commit: `eb6784b2e9741052c5f104847e41b5accc812e7e`
- Upstream commit date: 2025-05-29T17:00:45+09:00
- Import date: 2026-09-30
- License: Apache-2.0; see [`LICENSE`](LICENSE)
- Import method: `git archive` of the exact upstream commit, without upstream `.git` metadata
- Local repository: https://github.com/ArchwingZeroThr/Reproduction4grade1
- Local project path: `projects/SimDiffRec/`

## Local changes at import

- Added this provenance record.
- Added knowledge-base links and monorepo guidance to the upstream README.
- Model code and upstream configuration files were not changed during import.

Future upstream synchronization must record the old and new upstream commits and preserve local patches as reviewable commits. Do not replace this directory with an untracked nested clone.

## Local execution compatibility patch

- In the imported author snapshot `zingyon/SimDiffRec@eb6784b2e9741052c5f104847e41b5accc812e7e`, `SimDiff.full_sort_predict()` returns `(scores, seq_output)`.
- The bundled RecBole `Trainer._full_sort_batch_eval()` expects the standard `Tensor` score contract and immediately calls `scores.view(...)`; the tuple therefore fails at the first full-sort evaluation.
- The local execution patch returns `scores` only. The exact author behavior remains attributable to the immutable imported commit above; this is an evaluation-interface compatibility fix, not a change to score calculation.
