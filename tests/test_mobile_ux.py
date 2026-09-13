import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MobileUxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.css = (ROOT / "mobile.css").read_text(encoding="utf-8")
        cls.ux = (ROOT / "ux-v2.css").read_text(encoding="utf-8")

    def test_override_mobile_e_carregado_depois_do_css_base(self):
        base = self.html.index('href="style.css"')
        mobile = self.html.index('href="mobile.css"')
        ux = self.html.index('href="ux-v2.css"')
        self.assertLess(base, mobile)
        self.assertLess(mobile, ux)

    def test_abas_mobile_nao_dependem_de_scroll_horizontal(self):
        self.assertIn("grid-template-columns:repeat(3,minmax(0,1fr))", self.ux)
        self.assertNotIn("overflow-x:auto", self.ux.replace(" ", ""))

    def test_todas_as_abas_criticas_continuam_publicadas(self):
        for label in ("Sugestões", "Novos", "A confirmar", "Favoritos", "Descartados", "Imobiliárias"):
            self.assertIn(f">{label}</button>", self.html)

    def test_cards_mobile_recebem_compactacao_explicita(self):
        for rule in (".card-conteudo", ".titulo", ".metricas", ".detalhes", ".alertas", ".acoes"):
            self.assertIn(rule, self.ux)
        self.assertIn("max-height:185px", self.ux)

    def test_acoes_de_decisao_cabem_no_mobile(self):
        self.assertIn("grid-template-columns:1.25fr 1fr 1fr", self.ux)
        self.assertIn("min-height:40px", self.ux)
        self.assertIn(".acoes .indisponivel", self.ux)


if __name__ == "__main__":
    unittest.main()
