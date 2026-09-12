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

    def test_below_2000_requires_strong_structured_opportunity(self):
        self.assertIn("function temJustificativaForteAbaixoDoPiso", self.policy)
        self.assertIn("if (preco < 2000)", self.policy)
        self.assertIn("elegibilidade.elegivel === true && temJustificativaForteAbaixoDoPiso(item)", self.policy)
        self.assertIn("oportunidade.forte === true", self.policy)
        self.assertIn("motivos.length >= 2 || justificativa.length >= 80", self.policy)

    def test_above_main_range_requires_confirmed_eligibility_and_opportunity(self):
        self.assertIn("if (preco > 3000)", self.policy)
        self.assertIn("elegibilidade.elegivel === true && temJustificativaOportunidade(item)", self.policy)

    def test_main_price_band_has_ranking_priority_inside_same_eligibility_level(self):
        self.assertIn("function prioridadeFaixaPrincipal", self.policy)
        self.assertIn("preco >= 2000 && preco <= 3000 ? 0 : 1", self.policy)
        self.assertIn("prioridadeCandidato = function prioridadeCandidatoComFaixa", self.policy)
        self.assertIn("nivel + prioridadeFaixaPrincipal(item)", self.policy)
        self.assertIn("const faixa = prioridadeFaixaPrincipal(a) - prioridadeFaixaPrincipal(b)", self.policy)

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

    def test_new_counter_only_counts_visible_undecided_active_candidates(self):
        self.assertIn("const novosVisiveis = candidatos.filter", self.policy)
        self.assertIn("decisao(i.id) === null", self.policy)
        self.assertIn("state.novosIds.has(i.id)", self.policy)
        self.assertIn("Novos (${novosVisiveis})", self.policy)
        self.assertNotIn("Novos (${state.novosIds.size})", self.policy)

    def test_match_is_only_used_when_all_real_components_are_available(self):
        self.assertIn("function matchConfiavel", self.policy)
        self.assertIn("componentes.every(v => Number.isFinite(Number(v)))", self.policy)
        self.assertIn("m.confianca !== 'incompleta'", self.policy)
        self.assertIn("Number.isFinite(Number(m.final))", self.policy)

    def test_default_ranking_prefers_real_information_without_fabricating_score(self):
        self.assertIn("function prioridadeQualidade", self.policy)
        self.assertIn("const temMatch = matchConfiavel(item) ? 0 : 1", self.policy)
        self.assertIn("const temFoto", self.policy)
        self.assertIn("localizacaoValidada === true", self.policy)
        self.assertIn("Não cria nota", self.policy)

    def test_match_order_does_not_promote_incomplete_match(self):
        self.assertIn("if (ordem === 'match')", self.policy)
        self.assertIn("if (aTem !== bTem) return aTem ? -1 : 1", self.policy)
        self.assertIn("if (aTem && bTem)", self.policy)


if __name__ == "__main__":
    unittest.main()
