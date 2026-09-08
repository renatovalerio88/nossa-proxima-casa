import unittest

from scripts.enrich_location import haversine_km, query_for


class LocationTests(unittest.TestCase):
    def test_query_prefere_endereco_exato(self):
        query, precision = query_for({
            "endereco": "Rua Exemplo, 123",
            "bairro": "Centro",
            "cidade": "Divinópolis",
        })
        self.assertEqual(precision, "endereco")
        self.assertIn("Rua Exemplo, 123", query)
        self.assertIn("Divinópolis", query)

    def test_query_cai_para_bairro_sem_inventar_endereco(self):
        query, precision = query_for({"bairro": "Centro", "cidade": "Divinópolis"})
        self.assertEqual(precision, "bairro")
        self.assertEqual(query, "Centro, Divinópolis, MG, Brasil")

    def test_query_sem_localizacao_retorna_none(self):
        self.assertIsNone(query_for({"cidade": "Divinópolis"}))

    def test_haversine_zero(self):
        self.assertAlmostEqual(haversine_km(-20.0, -44.0, -20.0, -44.0), 0.0, places=6)

    def test_haversine_simetrica(self):
        a = haversine_km(-20.1435, -44.8830, -20.1500, -44.9000)
        b = haversine_km(-20.1500, -44.9000, -20.1435, -44.8830)
        self.assertAlmostEqual(a, b, places=6)
        self.assertGreater(a, 0)


if __name__ == "__main__":
    unittest.main()
