import unittest

from scripts.core import calculate_match, eligibility, merge_inventory, property_fingerprint


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
        match = calculate_match(item, CFG)
        self.assertIn("Quintal: não informado", match["pontosAtencao"])
        self.assertIn("Armários: não informado", match["pontosAtencao"])

    def test_hard_minimums(self):
        item = {"cidade": "Divinópolis", "tipo": "casa", "areaM2": 80, "quartos": 2, "aluguel": 2500}
        result = eligibility(item, CFG)
        self.assertFalse(result["elegivel"])
        self.assertGreaterEqual(len(result["motivos"]), 2)

    def test_above_opportunity_ceiling_is_not_eligible(self):
        item = {"cidade": "Divinópolis", "tipo": "casa", "areaM2": 200, "quartos": 3, "aluguel": 5500}
        result = eligibility(item, CFG)
        self.assertFalse(result["elegivel"])
        self.assertIn("Acima do teto de oportunidade", result["motivos"])

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

    def test_disappeared_listing_is_marked_unavailable(self):
        initial = merge_inventory({"schemaVersion": 1, "imoveis": []}, [{"fonte": "X", "codigoFonte": "2"}], today="2026-09-08")
        updated = merge_inventory(initial, [], today="2026-09-09")
        self.assertFalse(updated["imoveis"][0]["disponivel"])


if __name__ == "__main__":
    unittest.main()
