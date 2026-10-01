import ast
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SIMDIFF_PATH = PROJECT_ROOT / 'recbole/model/sequential_recommender/simdiff.py'


def _simdiff_method(name):
    tree = ast.parse(SIMDIFF_PATH.read_text(encoding='utf-8'))
    simdiff = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == 'SimDiff'
    )
    return next(
        node for node in simdiff.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )


class SimDiffExecutionPatchTest(unittest.TestCase):
    def test_full_sort_predict_returns_scores_tensor_contract(self):
        method = _simdiff_method('full_sort_predict')
        returns = [node for node in ast.walk(method) if isinstance(node, ast.Return)]

        self.assertEqual(len(returns), 1)
        self.assertIsInstance(returns[0].value, ast.Name)
        self.assertEqual(returns[0].value.id, 'scores')

    def test_forward_contains_explicit_ablation_modes(self):
        source = ast.unparse(_simdiff_method('forward'))

        self.assertIn("self.noise_mode == 'semantic'", source)
        self.assertIn('top_n_embeds.mean(dim=2)', source)
        self.assertIn('torch.randn_like(seq_emb)', source)
        self.assertIn("self.position_mode == 'confidence'", source)
        self.assertIn('torch.rand_like(max_probs)', source)
        self.assertIn('position_scores[item_seq == 0] = 0', source)

    def test_model_defaults_select_full_modes(self):
        defaults = (
            PROJECT_ROOT / 'recbole/properties/model/SimDiff.yaml'
        ).read_text(encoding='utf-8')

        self.assertIn('noise_mode: semantic', defaults)
        self.assertIn('position_mode: confidence', defaults)


if __name__ == '__main__':
    unittest.main()
