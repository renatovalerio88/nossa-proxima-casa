import unittest

from scripts.validate_source_policy import allowed_sources, validate_seed_sources


class SourcePolicyTests(unittest.TestCase):
    def setUp(self):
        self.fontes = {
            "fontes": [
                {"nome": "Permitida", "coletaAutomatica": True},
                {"nome": "Bloqueada", "coletaAutomatica": False},
            ]
        }

    def test_allowed_sources_only_returns_automatic(self):
        self.assertEqual(allowed_sources(self.fontes), {"Permitida"})

    def test_validate_accepts_allowed_source(self):
        validate_seed_sources({"urls": [{"fonte": "Permitida"}]}, self.fontes)

    def test_validate_rejects_blocked_source(self):
        with self.assertRaisesRegex(ValueError, "sem autorização"):
            validate_seed_sources({"urls": [{"fonte": "Bloqueada"}]}, self.fontes)

    def test_validate_rejects_unknown_source(self):
        with self.assertRaisesRegex(ValueError, "não auditadas"):
            validate_seed_sources({"urls": [{"fonte": "Desconhecida"}]}, self.fontes)


if __name__ == "__main__":
    unittest.main()
