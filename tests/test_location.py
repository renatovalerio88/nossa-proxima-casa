import unittest
from unittest.mock import patch

from scripts.enrich_location import (
    clear_untrusted_location,
    geocode_is_plausible,
    haversine_km,
    hospital_reference,
    query_for,
)


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

    def test_hospital_usa_coordenadas_configuradas_sem_rede(self):
        cfg = {
            "endereco": "Rua Pedro Ferreira do Amaral, 33 - Padre Libério, Divinópolis - MG",
            "latitude": -20.120292716318463,
            "longitude": -44.89533733843522,
            "fonteCoordenadas": "https://www2.hapvida.com.br/unidades/hospital-e-maternidade-santa-monica",
        }
        with patch("scripts.enrich_location.geocode") as mocked:
            ref = hospital_reference(cfg, {})
        mocked.assert_not_called()
        self.assertAlmostEqual(ref["latitude"], cfg["latitude"])
        self.assertAlmostEqual(ref["longitude"], cfg["longitude"])
        self.assertEqual(ref["fonte"], cfg["fonteCoordenadas"])

    def test_hospital_faz_fallback_para_endereco_quando_sem_coordenadas(self):
        expected = {"latitude": -20.1, "longitude": -44.8}
        with patch("scripts.enrich_location.geocode", return_value=expected) as mocked:
            ref = hospital_reference({"endereco": "Hospital, Divinópolis"}, {})
        mocked.assert_called_once_with("Hospital, Divinópolis", {})
        self.assertEqual(ref, expected)

    def test_haversine_zero(self):
        self.assertAlmostEqual(haversine_km(-20.0, -44.0, -20.0, -44.0), 0.0, places=6)

    def test_haversine_simetrica(self):
        a = haversine_km(-20.1435, -44.8830, -20.1500, -44.9000)
        b = haversine_km(-20.1500, -44.9000, -20.1435, -44.8830)
        self.assertAlmostEqual(a, b, places=6)
        self.assertGreater(a, 0)

    def test_geocode_divinopolis_mg_proximo_e_aceito(self):
        hospital = {"latitude": -20.1203, "longitude": -44.8953}
        geo = {
            "latitude": -20.1435,
            "longitude": -44.8830,
            "cidade": "Divinópolis",
            "uf": "MG",
        }
        self.assertTrue(geocode_is_plausible(geo, hospital))

    def test_geocode_de_outra_cidade_e_rejeitado(self):
        hospital = {"latitude": -20.1203, "longitude": -44.8953}
        geo = {
            "latitude": -19.9208,
            "longitude": -43.9378,
            "cidade": "Belo Horizonte",
            "uf": "MG",
        }
        self.assertFalse(geocode_is_plausible(geo, hospital))

    def test_geocode_distante_e_rejeitado_mesmo_sem_metadados(self):
        hospital = {"latitude": -20.1203, "longitude": -44.8953}
        geo = {"latitude": -19.9208, "longitude": -43.9378}
        self.assertFalse(geocode_is_plausible(geo, hospital))

    def test_geocode_com_uf_incorreta_e_rejeitado(self):
        hospital = {"latitude": -20.1203, "longitude": -44.8953}
        geo = {
            "latitude": -20.1435,
            "longitude": -44.8830,
            "cidade": "Divinópolis",
            "uf": "SP",
        }
        self.assertFalse(geocode_is_plausible(geo, hospital))

    def test_limpeza_de_localizacao_preserva_desconhecido_como_null(self):
        item = {
            "latitude": -19.0,
            "longitude": -43.0,
            "hospital": {
                "distanciaKm": 120.0,
                "distanciaLinhaRetaKm": 110.0,
                "tempoCarroMin": 130,
                "precisaoLocalizacao": "bairro",
                "fonteLocalizacao": "teste",
            },
        }
        clear_untrusted_location(item)
        self.assertIsNone(item["latitude"])
        self.assertIsNone(item["longitude"])
        self.assertIsNone(item["hospital"]["distanciaKm"])
        self.assertIsNone(item["hospital"]["distanciaLinhaRetaKm"])
        self.assertFalse(item["hospital"]["localizacaoValidada"])


if __name__ == "__main__":
    unittest.main()
