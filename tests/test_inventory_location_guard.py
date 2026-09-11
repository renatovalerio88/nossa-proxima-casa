import unittest

from scripts.update_inventory import limpar_distancia_nao_validada, limpar_documento_localizacao


class InventoryLocationGuardTests(unittest.TestCase):
    def test_unvalidated_distance_is_cleared(self):
        item = {
            "id": "imv_1",
            "hospital": {
                "localizacaoValidada": False,
                "distanciaKm": 2.4,
                "distanciaLinhaRetaKm": 1.8,
                "precisaoLocalizacao": "endereco",
                "fonteDistancia": "legado",
            },
        }
        cleaned = limpar_distancia_nao_validada(item)
        self.assertFalse(cleaned["hospital"]["localizacaoValidada"])
        self.assertIsNone(cleaned["hospital"]["distanciaKm"])
        self.assertIsNone(cleaned["hospital"]["distanciaLinhaRetaKm"])
        self.assertIsNone(cleaned["hospital"]["precisaoLocalizacao"])
        self.assertIsNone(cleaned["hospital"]["fonteDistancia"])
        self.assertEqual(item["hospital"]["distanciaKm"], 2.4)

    def test_missing_validation_is_treated_as_unvalidated(self):
        cleaned = limpar_distancia_nao_validada({"hospital": {"distanciaKm": 4.1}})
        self.assertFalse(cleaned["hospital"]["localizacaoValidada"])
        self.assertIsNone(cleaned["hospital"]["distanciaKm"])

    def test_validated_distance_is_preserved(self):
        item = {
            "hospital": {
                "localizacaoValidada": True,
                "distanciaKm": 3.2,
                "precisaoLocalizacao": "bairro",
            }
        }
        self.assertEqual(limpar_distancia_nao_validada(item), item)

    def test_document_guard_cleans_every_listing(self):
        document = {
            "imoveis": [
                {"id": "a", "hospital": {"distanciaKm": 1.0}},
                {"id": "b", "hospital": {"localizacaoValidada": True, "distanciaKm": 2.0}},
            ]
        }
        cleaned = limpar_documento_localizacao(document)
        self.assertIsNone(cleaned["imoveis"][0]["hospital"]["distanciaKm"])
        self.assertEqual(cleaned["imoveis"][1]["hospital"]["distanciaKm"], 2.0)


if __name__ == "__main__":
    unittest.main()
