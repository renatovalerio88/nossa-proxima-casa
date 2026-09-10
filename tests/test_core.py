import unittest

from scripts.core import calculate_match, eligibility, merge_inventory, property_fingerprint, reapply_rules


CFG = {
    "criterios": {
        "areaMinimaM2": 90,
        "quartosMinimos": 3,
        "banheirosMinimos": 2,
        "areaExternaPrivativaObrigatoria": True,
        "aluguelIdealMin": 2000,
        "aluguelIdealMax": 3000,
        "aluguelOportunidadeMax": 3500,
        "oportunidade": {"distanciaHospitalMaxKm": 8, "areaDestaqueM2": 110, "aceitaQuartoExtra": True, "aceitaArmarios": True},
    },
    "pesosMatch": {"casa": 40, "localizacao": 25, "custoBeneficio": 20, "visual": 15},
}


def base_item(**overrides):
    item = {
        "cidade": "Divinópolis", "tipo": "casa", "areaM2": 110, "quartos": 3,
        "banheiros": 2, "quintal": True, "aluguel": 2800,
        "hospital": {"distanciaKm": 4.0},
    }
    item.update(overrides)
    return item


class CoreTests(unittest.TestCase):
    def test_fingerprint_stable_with_source_code(self):
        self.assertEqual(property_fingerprint({"fonte": "Casa Nova", "codigoFonte": "123"}), property_fingerprint({"fonte": " casa nova ", "codigoFonte": 123}))

    def test_eligibility_requires_bathrooms_and_private_external_area(self):
        for field in ("banheiros", "quintal"):
            item = base_item(**{field: None})
            result = eligibility(item, CFG)
            self.assertFalse(result["elegivel"])
            self.assertEqual(result["status"], "pendente")

    def test_private_external_area_false_is_ineligible(self):
        result = eligibility(base_item(quintal=False), CFG)
        self.assertEqual(result["status"], "inelegivel")
        self.assertIn("Sem área externa privativa", result["motivos"])

    def test_missing_mandatory_fields_are_pending_not_eligible(self):
        item = base_item(quartos=None, aluguel=None)
        result = eligibility(item, CFG)
        self.assertFalse(result["elegivel"])
        self.assertEqual(result["status"], "pendente")
        self.assertIn("Quartos não confirmados", result["pendencias"])
        self.assertIn("Aluguel não confirmado", result["pendencias"])

    def test_above_opportunity_ceiling_is_not_eligible(self):
        result = eligibility(base_item(aluguel=5500), CFG)
        self.assertEqual(result["status"], "inelegivel")
        self.assertIn("Acima do teto de oportunidade", result["motivos"])

    def test_price_below_main_range_is_not_automatic_good_match(self):
        weak = base_item(aluguel=1800, areaM2=90, armarios=None, hospital={"distanciaKm": 9})
        result = eligibility(weak, CFG)
        self.assertEqual(result["status"], "inelegivel")
        self.assertIn("Fora da faixa principal sem justificativa de oportunidade forte", result["motivos"])

    def test_price_outside_main_range_can_be_exceptional_opportunity(self):
        item = base_item(aluguel=3300, areaM2=125, hospital={"distanciaKm": 5})
        result = eligibility(item, CFG)
        self.assertTrue(result["elegivel"])
        self.assertIn("Oportunidade excepcional", result["oportunidade"])

    def test_visual_without_real_photos_is_null_not_default_50(self):
        item = base_item(avaliacaoVisual={"nota": 8}, fotos=[])
        match = calculate_match(item, CFG)
        self.assertIsNone(match["visual"])
        self.assertIsNone(match["final"])
        self.assertNotEqual(match.get("visual"), 50)
        self.assertEqual(match["confianca"], "incompleta")

    def test_match_waits_for_location(self):
        item = base_item(hospital={})
        match = calculate_match(item, CFG)
        self.assertIsNone(match["final"])
        self.assertEqual(match["confianca"], "incompleta")

    def test_real_photos_allow_visual_when_assessed(self):
        item = base_item(fotos=["https://example.com/real.jpg"], avaliacaoVisual={"nota": 8})
        match = calculate_match(item, CFG)
        self.assertEqual(match["visual"], 80)
        self.assertEqual(match["confianca"], "alta")

    def test_reapply_rules_updates_legacy_classification_without_losing_history(self):
        document = {"schemaVersion": 1, "atualizadoEm": "2026-09-08", "imoveis": [{"id": "imv_legacy", "fonte": "Casa Nova", "codigoFonte": "1", "cidade": "Divinópolis", "tipo": "casa", "areaM2": 100, "quartos": None, "banheiros": None, "quintal": None, "aluguel": None, "disponivel": False, "historico": [{"data": "2026-09-08", "campo": "disponivel", "de": True, "para": False}], "elegibilidade": {"elegivel": True, "motivos": []}}]}
        updated = reapply_rules(document, CFG); item = updated["imoveis"][0]
        self.assertEqual(item["elegibilidade"]["status"], "pendente")
        self.assertEqual(item["historico"], document["imoveis"][0]["historico"])
        self.assertFalse(item["disponivel"])

    def test_inventory_preserves_first_seen_and_tracks_price(self):
        initial = {"schemaVersion": 1, "atualizadoEm": None, "imoveis": []}
        one = merge_inventory(initial, [{"fonte": "X", "codigoFonte": "1", "aluguel": 2500}], today="2026-09-08")
        two = merge_inventory(one, [{"fonte": "X", "codigoFonte": "1", "aluguel": 2400}], today="2026-09-09")
        item = two["imoveis"][0]
        self.assertEqual(item["primeiroVistoEm"], "2026-09-08")
        self.assertEqual(item["historico"][-1]["para"], 2400)

    def test_missing_from_partial_collection_does_not_mark_unavailable(self):
        initial = merge_inventory({"schemaVersion": 1, "imoveis": []}, [{"fonte": "X", "codigoFonte": "2", "disponivel": True}], today="2026-09-08")
        updated = merge_inventory(initial, [], today="2026-09-09")
        self.assertTrue(updated["imoveis"][0]["disponivel"])
        self.assertEqual(updated["imoveis"][0]["ultimoVistoEm"], "2026-09-08")

    def test_explicit_tombstone_marks_existing_listing_unavailable(self):
        initial = merge_inventory({"schemaVersion": 1, "imoveis": []}, [{"fonte": "X", "codigoFonte": "3", "disponivel": True, "aluguel": 2500}], today="2026-09-08")
        updated = merge_inventory(initial, [{"fonte": "X", "codigoFonte": "3", "disponivel": False}], today="2026-09-09")
        self.assertFalse(updated["imoveis"][0]["disponivel"])

    def test_unknown_tombstone_does_not_create_ghost_listing(self):
        updated = merge_inventory({"schemaVersion": 1, "imoveis": []}, [{"fonte": "X", "codigoFonte": "404", "disponivel": False}], today="2026-09-09")
        self.assertEqual(updated["imoveis"], [])


if __name__ == "__main__": unittest.main()
