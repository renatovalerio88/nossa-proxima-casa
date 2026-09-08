import unittest

from scripts.core import calculate_match, eligibility, merge_inventory, property_fingerprint, reapply_rules


CFG = {
    "criterios": {
        "areaMinimaM2": 90,
        "quartosMinimos": 3,
        "aluguelIdealMin": 2000,
        "aluguelIdealMax": 3000,
        "aluguelOportunidadeMax": 3500,
    },
    "pesosMatch": {"casa": 40, "localizacao": 25, "custoBeneficio": 20, "visual": 15},
}


class CoreTests(unittest.TestCase):
    def test_fingerprint_stable_with_source_code(self):
        a = {"fonte": "Casa Nova", "codigoFonte": "123"}
        b = {"fonte": " casa nova ", "codigoFonte": 123}
        self.assertEqual(property_fingerprint(a), property_fingerprint(b))

    def test_unknown_quintal_armarios_do_not_disqualify(self):
        item = {"cidade": "Divinópolis", "tipo": "casa", "areaM2": 100, "quartos": 3, "aluguel": 2800}
        result = eligibility(item, CFG)
        self.assertTrue(result["elegivel"])
        self.assertEqual(result["status"], "elegivel")
        match = calculate_match(item, CFG)
        self.assertIn("Quintal: não informado", match["pontosAtencao"])
        self.assertIn("Armários: não informado", match["pontosAtencao"])

    def test_missing_mandatory_fields_are_pending_not_eligible(self):
        item = {"cidade": "Divinópolis", "tipo": "casa", "areaM2": 100, "quartos": None, "aluguel": None}
        result = eligibility(item, CFG)
        self.assertFalse(result["elegivel"])
        self.assertEqual(result["status"], "pendente")
        self.assertIn("Quartos não confirmados", result["pendencias"])
        self.assertIn("Aluguel não confirmado", result["pendencias"])

    def test_hard_minimums(self):
        item = {"cidade": "Divinópolis", "tipo": "casa", "areaM2": 80, "quartos": 2, "aluguel": 2500}
        result = eligibility(item, CFG)
        self.assertFalse(result["elegivel"])
        self.assertEqual(result["status"], "inelegivel")
        self.assertGreaterEqual(len(result["motivos"]), 2)

    def test_above_opportunity_ceiling_is_not_eligible(self):
        item = {"cidade": "Divinópolis", "tipo": "casa", "areaM2": 200, "quartos": 3, "aluguel": 5500}
        result = eligibility(item, CFG)
        self.assertFalse(result["elegivel"])
        self.assertEqual(result["status"], "inelegivel")
        self.assertIn("Acima do teto de oportunidade", result["motivos"])

    def test_reapply_rules_updates_legacy_classification_without_losing_history(self):
        document = {
            "schemaVersion": 1,
            "atualizadoEm": "2026-09-08",
            "imoveis": [
                {
                    "id": "imv_legacy",
                    "fonte": "Casa Nova",
                    "codigoFonte": "1",
                    "cidade": "Divinópolis",
                    "tipo": "casa",
                    "areaM2": 100,
                    "quartos": None,
                    "aluguel": None,
                    "disponivel": False,
                    "historico": [{"data": "2026-09-08", "campo": "disponivel", "de": True, "para": False}],
                    "elegibilidade": {"elegivel": True, "motivos": []},
                }
            ],
        }
        updated = reapply_rules(document, CFG)
        item = updated["imoveis"][0]
        self.assertFalse(item["elegibilidade"]["elegivel"])
        self.assertEqual(item["elegibilidade"]["status"], "pendente")
        self.assertEqual(item["historico"], document["imoveis"][0]["historico"])
        self.assertFalse(item["disponivel"])

    def test_inventory_preserves_first_seen_and_tracks_price(self):
        initial = {"schemaVersion": 1, "atualizadoEm": None, "imoveis": []}
        incoming = [{"fonte": "X", "codigoFonte": "1", "cidade": "Divinópolis", "tipo": "casa", "aluguel": 2500}]
        one = merge_inventory(initial, incoming, today="2026-09-08")
        changed = [{"fonte": "X", "codigoFonte": "1", "cidade": "Divinópolis", "tipo": "casa", "aluguel": 2400}]
        two = merge_inventory(one, changed, today="2026-09-09")
        item = two["imoveis"][0]
        self.assertEqual(item["primeiroVistoEm"], "2026-09-08")
        self.assertEqual(item["ultimoVistoEm"], "2026-09-09")
        self.assertEqual(item["historico"][-1]["campo"], "aluguel")
        self.assertEqual(item["historico"][-1]["para"], 2400)

    def test_missing_from_partial_collection_does_not_mark_unavailable(self):
        initial = merge_inventory(
            {"schemaVersion": 1, "imoveis": []},
            [{"fonte": "X", "codigoFonte": "2", "disponivel": True}],
            today="2026-09-08",
        )
        updated = merge_inventory(initial, [], today="2026-09-09")
        self.assertTrue(updated["imoveis"][0]["disponivel"])
        self.assertEqual(updated["imoveis"][0]["ultimoVistoEm"], "2026-09-08")

    def test_explicit_tombstone_marks_existing_listing_unavailable(self):
        initial = merge_inventory(
            {"schemaVersion": 1, "imoveis": []},
            [{"fonte": "X", "codigoFonte": "3", "disponivel": True, "aluguel": 2500}],
            today="2026-09-08",
        )
        updated = merge_inventory(
            initial,
            [{"fonte": "X", "codigoFonte": "3", "disponivel": False}],
            today="2026-09-09",
        )
        item = updated["imoveis"][0]
        self.assertFalse(item["disponivel"])
        self.assertEqual(item["historico"][-1], {"data": "2026-09-09", "campo": "disponivel", "de": True, "para": False})

    def test_unknown_tombstone_does_not_create_ghost_listing(self):
        updated = merge_inventory(
            {"schemaVersion": 1, "imoveis": []},
            [{"fonte": "X", "codigoFonte": "404", "disponivel": False}],
            today="2026-09-09",
        )
        self.assertEqual(updated["imoveis"], [])


if __name__ == "__main__":
    unittest.main()
