import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from ingest_verified_candidates import candidate_to_inventory, merge_candidate_documents, merge_candidates


CFG = {
    "criterios": {
        "areaMinimaM2": 90,
        "quartosMinimos": 3,
        "banheirosMinimos": 2,
        "areaExternaPrivativaObrigatoria": True,
        "aluguelIdealMin": 2000,
        "aluguelIdealMax": 3000,
        "aluguelOportunidadeMax": 3500,
        "oportunidade": {
            "distanciaHospitalMaxKm": 8,
            "areaDestaqueM2": 110,
            "aceitaQuartoExtra": True,
            "aceitaArmarios": True,
        },
    },
    "pesosMatch": {"casa": 40, "localizacao": 25, "custoBeneficio": 20, "visual": 15},
}


class VerifiedCandidatesTest(unittest.TestCase):
    def candidate(self):
        return {
            "fonte": "Fonte Teste",
            "codigoFonte": "123",
            "url": "https://example.test/123",
            "observadoEm": "2026-09-09",
            "disponibilidadeObservada": True,
            "tipo": "casa",
            "cidade": "Divinópolis",
            "bairro": "Centro",
            "endereco": None,
            "aluguel": 3200.0,
            "areaM2": 200.0,
            "quartos": 3,
            "banheiros": 2,
            "quintal": True,
            "armarios": True,
            "churrasqueira": True,
            "piscina": True,
            "hidromassagem": None,
            "hospital": {"distanciaKm": 4.0},
            "coletaAutomaticaPermitida": False,
            "notaProveniencia": "Observação humana verificável.",
        }

    def test_candidate_uses_observed_date_not_today(self):
        item = candidate_to_inventory(self.candidate())
        self.assertEqual(item["primeiroVistoEm"], "2026-09-09")
        self.assertEqual(item["ultimoVistoEm"], "2026-09-09")
        self.assertTrue(item["disponivel"])
        self.assertEqual(item["proveniencia"]["modo"], "verificacao_manual")
        self.assertFalse(item["proveniencia"]["coletaAutomaticaPermitida"])

    def test_new_candidate_enters_inventory_with_match(self):
        doc = {"schemaVersion": 1, "atualizadoEm": "2026-09-09", "imoveis": []}
        merged = merge_candidates(doc, {"imoveis": [self.candidate()]}, CFG)
        self.assertEqual(len(merged["imoveis"]), 1)
        item = merged["imoveis"][0]
        self.assertEqual(item["ultimoVistoEm"], "2026-09-09")
        self.assertEqual(item["elegibilidade"]["status"], "elegivel")
        self.assertIn("Oportunidade excepcional", item["elegibilidade"]["oportunidade"])
        self.assertIn("final", item["match"])
        self.assertEqual(item["historico"][0]["campo"], "observacao_verificada")

    def test_older_manual_observation_does_not_overwrite_newer_inventory(self):
        incoming = candidate_to_inventory(self.candidate())
        newer = copy.deepcopy(incoming)
        newer["ultimoVistoEm"] = "2026-09-10"
        newer["aluguel"] = 3000.0
        newer["historico"] = []
        doc = {"schemaVersion": 1, "atualizadoEm": "2026-09-10", "imoveis": [newer]}
        merged = merge_candidates(doc, {"imoveis": [self.candidate()]}, CFG)
        self.assertEqual(merged["imoveis"][0]["aluguel"], 3000.0)
        self.assertEqual(merged["imoveis"][0]["ultimoVistoEm"], "2026-09-10")

    def test_unknown_fields_remain_unknown(self):
        item = candidate_to_inventory(self.candidate())
        self.assertIsNone(item["endereco"])
        self.assertIsNone(item["hidromassagem"])

    def test_multiple_batches_are_merged_incrementally(self):
        first = self.candidate()
        second = copy.deepcopy(first)
        second["codigoFonte"] = "456"
        second["url"] = "https://example.test/456"
        second["bairro"] = "Bom Pastor"
        inventory = {"schemaVersion": 1, "atualizadoEm": "2026-09-09", "imoveis": []}
        merged = merge_candidate_documents(inventory, [{"imoveis": [first]}, {"imoveis": [second]}], CFG)
        self.assertEqual(len(merged["imoveis"]), 2)
        self.assertEqual({item["codigoFonte"] for item in merged["imoveis"]}, {"123", "456"})

    def test_newer_batch_wins_for_same_property(self):
        old = self.candidate()
        newer = copy.deepcopy(old)
        newer["observadoEm"] = "2026-09-10"
        newer["aluguel"] = 3000.0
        inventory = {"schemaVersion": 1, "atualizadoEm": "2026-09-09", "imoveis": []}
        merged = merge_candidate_documents(inventory, [{"imoveis": [old]}, {"imoveis": [newer]}], CFG)
        self.assertEqual(len(merged["imoveis"]), 1)
        self.assertEqual(merged["imoveis"][0]["ultimoVistoEm"], "2026-09-10")
        self.assertEqual(merged["imoveis"][0]["aluguel"], 3000.0)


if __name__ == "__main__":
    unittest.main()
