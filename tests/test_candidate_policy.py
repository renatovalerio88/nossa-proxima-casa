import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CandidatePolicyContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.policy = (ROOT / "candidate-policy.js").read_text(encoding="utf-8")

    def test_policy_loads_after_app_and_before_gallery(self):
        app_pos = self.html.index('src="app.js"')
        policy_pos = self.html.index('src="candidate-policy.js"')
        gallery_pos = self.html.index('src="gallery.js"')
        self.assertLess(app_pos, policy_pos)
        self.assertLess(policy_pos, gallery_pos)

    def test_above_3500_never_enters_active_candidates(self):
        self.assertIn("if (preco > 3500) return false", self.policy)

    def test_outside_main_range_requires_confirmed_eligibility_and_opportunity(self):
        self.assertIn("preco < 2000 || preco > 3000", self.policy)
        self.assertIn("elegibilidade.elegivel === true && temJustificativaOportunidade(item)", self.policy)

    def test_ineligible_listing_never_enters_active_candidates(self):
        self.assertIn("elegibilidade.status === 'inelegivel'", self.policy)
        self.assertIn("return false", self.policy)

    def test_unknown_price_can_only_stay_as_pending(self):
        self.assertIn("return elegibilidade.status === 'pendente'", self.policy)

    def test_source_availability_is_not_overwritten(self):
        self.assertIn("function disponivelNaFonte", self.policy)
        self.assertNotIn("item.disponivel = false", self.policy)
        self.assertNotIn("delete item", self.policy)

    def test_status_distinguishes_inventory_from_active_candidates(self):
        self.assertIn("anúncios acompanhados", self.policy)
        self.assertIn("candidatos ativos", self.policy)
        self.assertIn("fora do radar ativo", self.policy)


if __name__ == "__main__":
    unittest.main()
