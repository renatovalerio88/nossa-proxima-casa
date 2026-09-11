import unittest

from scripts.validate_source_policy import (
    allowed_sources,
    validate_seed_sources,
    validate_source_flags,
)


class SourcePolicyTests(unittest.TestCase):
    def setUp(self):
        self.fontes = {
            "fontes": [
                {"nome": "Permitida", "status": "piloto_baixa_frequencia", "coletaAutomatica": True},
                {
                    "nome": "Bloqueada",
                    "status": "nao_automatizar_sem_autorizacao",
                    "coletaAutomatica": False,
                    "siteUrl": "https://example.com/",
                    "motivo": "Termos não autorizam automação.",
                },
            ]
        }

    def test_allowed_sources_only_returns_automatic_with_explicit_status(self):
        self.assertEqual(allowed_sources(self.fontes), {"Permitida"})
        fontes = {
            "fontes": [
                {"nome": "Status novo", "status": "novo_status", "coletaAutomatica": True},
            ]
        }
        self.assertEqual(allowed_sources(fontes), set())

    def test_validate_accepts_allowed_source(self):
        validate_seed_sources({"urls": [{"fonte": "Permitida"}]}, self.fontes)

    def test_validate_rejects_blocked_source(self):
        with self.assertRaisesRegex(ValueError, "sem autorização"):
            validate_seed_sources({"urls": [{"fonte": "Bloqueada"}]}, self.fontes)

    def test_validate_rejects_unknown_source(self):
        with self.assertRaisesRegex(ValueError, "não auditadas"):
            validate_seed_sources({"urls": [{"fonte": "Desconhecida"}]}, self.fontes)

    def test_rejects_non_allowlisted_status_marked_as_automatic(self):
        fontes = {
            "fontes": [
                {
                    "nome": "OLX",
                    "status": "web_crawling_proibido_sem_autorizacao",
                    "coletaAutomatica": True,
                    "motivo": "Web crawling proibido.",
                }
            ]
        }
        with self.assertRaisesRegex(ValueError, "sem status explicitamente autorizado"):
            validate_source_flags(fontes)

    def test_rejects_unknown_future_status_marked_as_automatic(self):
        fontes = {
            "fontes": [
                {
                    "nome": "Fonte futura",
                    "status": "status_novo_ainda_nao_auditado",
                    "coletaAutomatica": True,
                }
            ]
        }
        with self.assertRaisesRegex(ValueError, "sem status explicitamente autorizado"):
            validate_source_flags(fontes)

    def test_rejects_blocked_source_without_reason(self):
        fontes = {
            "fontes": [
                {
                    "nome": "Portal",
                    "status": "nao_automatizar_sem_autorizacao",
                    "coletaAutomatica": False,
                }
            ]
        }
        with self.assertRaisesRegex(ValueError, "sem justificativa"):
            validate_source_flags(fontes)

    def test_rejects_duplicate_source_names(self):
        fontes = {
            "fontes": [
                {"nome": "Duplicada", "status": "piloto_baixa_frequencia", "coletaAutomatica": True},
                {
                    "nome": "Duplicada",
                    "status": "nao_automatizar_sem_autorizacao",
                    "coletaAutomatica": False,
                    "motivo": "Sem automação.",
                },
            ]
        }
        with self.assertRaisesRegex(ValueError, "duplicadas"):
            validate_source_flags(fontes)

    def test_rejects_source_without_name(self):
        fontes = {
            "fontes": [
                {"status": "piloto_baixa_frequencia", "coletaAutomatica": True},
            ]
        }
        with self.assertRaisesRegex(ValueError, "sem nome"):
            validate_source_flags(fontes)

    def test_accepts_https_official_site(self):
        fontes = {
            "fontes": [
                {
                    "nome": "Imobiliária",
                    "status": "manual_verificado_sem_automacao",
                    "coletaAutomatica": False,
                    "siteUrl": "https://imobiliaria.example/",
                    "motivo": "Acesso direto confirmado.",
                }
            ]
        }
        validate_source_flags(fontes)

    def test_rejects_http_or_malformed_site_url(self):
        for url in ("http://example.com/", "example.com", ""):
            fontes = {
                "fontes": [
                    {
                        "nome": "Imobiliária",
                        "status": "manual_verificado_sem_automacao",
                        "coletaAutomatica": False,
                        "siteUrl": url,
                        "motivo": "Acesso direto confirmado.",
                    }
                ]
            }
            with self.subTest(url=url):
                with self.assertRaisesRegex(ValueError, "siteUrl inválida"):
                    validate_source_flags(fontes)


if __name__ == "__main__":
    unittest.main()
