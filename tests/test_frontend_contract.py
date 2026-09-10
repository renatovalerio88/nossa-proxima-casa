import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class FrontendContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.js = (ROOT / "app.js").read_text(encoding="utf-8")
        cls.css = (ROOT / "style.css").read_text(encoding="utf-8")

    def test_abas_principais_estao_publicadas(self):
        for tab in ("novos", "a-confirmar", "favoritados", "descartados", "todos"):
            self.assertIn(f'data-tab="{tab}"', self.html)

    def test_controles_essenciais_existem(self):
        for element_id in (
            "statusColeta", "resumo", "ordenacao", "somenteElegiveis", "lista", "cardTemplate"
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

    def test_campos_desconhecidos_tem_fallback_sem_inventar_valor(self):
        self.assertIn("v === null || v === undefined || v === ''", self.js)
        self.assertIn("Localização a confirmar", self.js)
        self.assertIn("item.aluguel != null", self.js)
        self.assertIn("item.areaM2 != null", self.js)

    def test_link_da_fonte_preserva_url_e_isola_nova_aba(self):
        self.assertIn('target="_blank"', self.html)
        self.assertIn('rel="noopener noreferrer"', self.html)
        self.assertIn("link.href = item.url || '#'", self.js)

    def test_itens_indisponiveis_nao_aparecem_na_lista_ativa(self):
        self.assertIn("function ativo(item)", self.js)
        self.assertIn("state.imoveis.filter(ativo)", self.js)
        self.assertIn("state.imoveis.filter(ativo)", self.js)

    def test_novos_dependem_de_primeiro_visto_e_janela_temporal(self):
        self.assertIn("function ehNovo(item)", self.js)
        self.assertIn("item.primeiroVistoEm", self.js)
        self.assertIn("7 * 86400000", self.js)
        self.assertIn("state.tab === 'novos'", self.js)
        self.assertIn("ehNovo(i)", self.js)
        self.assertIn("return false", self.js)

    def test_pendentes_tem_aba_propria_e_match_incompleto(self):
        self.assertIn("function precisaConfirmacao(item)", self.js)
        self.assertIn("state.tab === 'a-confirmar'", self.js)
        self.assertIn("Match incompleto", self.js)
        self.assertIn('data-tab="a-confirmar"', self.html)

    def test_match_final_so_aparece_quando_numerico(self):
        self.assertIn("function matchDisponivel(item)", self.js)
        self.assertIn("Number.isFinite(Number(item.match?.final))", self.js)
        self.assertIn("item.match.final", self.js)
        self.assertNotIn("Visual 50", self.js)

    def test_visual_sem_fotos_reais_e_indisponivel(self):
        self.assertIn("function fotosConfiaveis(item)", self.js)
        self.assertIn("Avaliação visual indisponível · sem fotos reais", self.js)
        self.assertIn("item.match?.visual == null", self.js)

    def test_preco_explicita_faixa_principal_e_oportunidades(self):
        self.assertIn("p >= 2000 && p <= 3000", self.js)
        self.assertIn("p >= 3001 && p <= 3500", self.js)
        self.assertIn("Oportunidade acima da faixa", self.js)
        self.assertIn("Oportunidade abaixo da faixa", self.js)

    def test_card_prioriza_campos_essenciais(self):
        for termo in ("aluguel", "quartos", "banheiros", "área", "Área externa privativa", "Hospital Santa Mônica"):
            self.assertIn(termo, self.js)

    def test_distancia_do_hospital_prioriza_quilometros(self):
        self.assertIn("hospital.distanciaKm", self.js)
        self.assertIn("hospital.distanciaLinhaRetaKm", self.js)
        self.assertIn("precisaoLocalizacao", self.js)
        self.assertIn(" km", self.js)
        self.assertNotIn("tempoCarroMin", self.js)

    def test_status_da_coleta_mostra_inventario_e_fontes_em_vez_de_so_capturados(self):
        self.assertIn("imóveis ativos", self.js)
        self.assertIn("fontesComSucesso", self.js)
        self.assertIn("fontesTentadas", self.js)
        self.assertNotIn("capturado(s)", self.js)

    def test_mobile_tabs_tem_scroll_horizontal_sem_corte(self):
        self.assertIn("overflow-x:auto", self.css)
        self.assertIn("scroll-snap-type:x proximity", self.css)
        self.assertIn("scroll-padding-inline", self.css)


if __name__ == "__main__":
    unittest.main()
