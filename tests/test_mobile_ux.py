import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MobileUxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.css = (ROOT / "mobile.css").read_text(encoding="utf-8")

    def test_override_mobile_e_carregado_depois_do_css_base(self):
        base = self.html.index('href="style.css"')
        mobile = self.html.index('href="mobile.css"')
        self.assertLess(base, mobile)

    def test_abas_mobile_nao_sao_cortadas_por_ellipsis(self):
        self.assertIn("grid-template-columns: repeat(2, minmax(0, 1fr))", self.css)
        self.assertIn("text-overflow: clip", self.css)
        self.assertIn("overflow: visible", self.css)
        self.assertIn("white-space: nowrap", self.css)
        self.assertNotIn("text-overflow: ellipsis", self.css)

    def test_todas_as_abas_criticas_continuam_publicadas(self):
        for label in ("Novos", "A confirmar", "Favoritados", "Descartados", "Todos", "Imobiliárias"):
            self.assertIn(f">{label}</button>", self.html)

    def test_cards_mobile_recebem_compactacao_explicita(self):
        for rule in (
            ".card-conteudo",
            ".titulo",
            ".metricas",
            ".detalhes",
            ".alertas",
            ".proveniencia",
            ".acoes",
        ):
            self.assertIn(rule, self.css)

    def test_acoes_em_tela_muito_estreita_priorizam_anuncio(self):
        self.assertIn("@media (max-width: 390px)", self.css)
        self.assertIn("grid-template-columns: 1fr 1fr", self.css)
        self.assertIn("grid-column: 1 / -1", self.css)
        self.assertIn("min-height: 38px", self.css)


if __name__ == "__main__":
    unittest.main()
