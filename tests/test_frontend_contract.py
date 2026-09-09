import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class FrontendContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.js = (ROOT / "app.js").read_text(encoding="utf-8")

    def test_abas_principais_estao_publicadas(self):
        for tab in ("novos", "favoritados", "descartados", "todos"):
            self.assertIn(f'data-tab="{tab}"', self.html)

    def test_controles_essenciais_existem(self):
        for element_id in (
            "statusColeta",
            "resumo",
            "ordenacao",
            "somenteElegiveis",
            "lista",
            "cardTemplate",
        ):
            self.assertRegex(self.html, rf'id="{re.escape(element_id)}"')

    def test_persistencia_das_decisoes_usa_chave_estavel(self):
        self.assertIn("localStorage.getItem('npc-decisoes')", self.js)
        self.assertIn("localStorage.setItem('npc-decisoes'", self.js)
        self.assertIn("'favorito'", self.js)
        self.assertIn("'descartado'", self.js)

    def test_interface_consume_apenas_base_publicada_real(self):
        self.assertIn("fetch('data/imoveis.json'", self.js)
        self.assertIn("fetch('data/status-coleta.json'", self.js)
        self.assertNotIn("imoveisExemplo", self.js)
        self.assertNotIn("mock", self.js.lower())

    def test_campos_desconhecidos_tem_fallback_visual_sem_inventar_valor(self):
        self.assertIn("v === null || v === undefined || v === ''", self.js)
        self.assertIn("Localização a confirmar", self.js)
        self.assertIn("item.aluguel != null", self.js)
        self.assertIn("item.areaM2 != null", self.js)

    def test_link_da_fonte_preserva_url_e_isola_nova_aba(self):
        self.assertIn('target="_blank"', self.html)
        self.assertIn('rel="noopener noreferrer"', self.html)
        self.assertIn("link.href = item.url || '#'", self.js)

    def test_itens_indisponiveis_nao_aparecem_na_lista_ativa(self):
        self.assertIn("state.imoveis.filter(i => i.disponivel !== false)", self.js)

    def test_match_expoe_componentes_quando_existentes(self):
        for componente in (
            "item.match.casa",
            "item.match.localizacao",
            "item.match.custoBeneficio",
            "item.match.visual",
        ):
            self.assertIn(componente, self.js)


if __name__ == "__main__":
    unittest.main()
