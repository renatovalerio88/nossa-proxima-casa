import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class FrontendContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.js = (ROOT / "app.js").read_text(encoding="utf-8")
        cls.gallery = (ROOT / "gallery.js").read_text(encoding="utf-8")
        cls.css = (ROOT / "style.css").read_text(encoding="utf-8")

    def test_abas_principais_estao_publicadas(self):
        for tab in ("novos", "a-confirmar", "favoritados", "descartados", "todos", "imobiliarias"):
            self.assertIn(f'data-tab="{tab}"', self.html)

    def test_controles_essenciais_existem(self):
        for element_id in (
            "statusColeta", "resumo", "filtros", "ordenacao", "somenteElegiveis",
            "marcarNovosVistos", "lista", "cardTemplate"
        ):
            self.assertRegex(self.html, rf'id="{re.escape(element_id)}"')

    def test_persistencia_das_decisoes_usa_chave_estavel(self):
        self.assertIn("localStorage.getItem('npc-decisoes')", self.js)
        self.assertIn("localStorage.setItem('npc-decisoes'", self.js)
        self.assertIn("'favorito'", self.js)
        self.assertIn("'descartado'", self.js)

    def test_novos_usa_baseline_do_usuario_e_nao_inventario_inicial(self):
        self.assertIn("npc-inventario-conhecido", self.js)
        self.assertIn("state.novosIds", self.js)
        self.assertIn("function inicializarNovos", self.js)
        self.assertIn("function marcarNovosComoVistos", self.js)
        self.assertIn("Nenhum imóvel novo desde sua última revisão", self.js)
        self.assertNotIn("novos em 7 dias", self.js)

    def test_interface_consume_bases_publicadas_reais(self):
        self.assertIn("fetch('data/imoveis.json'", self.js)
        self.assertIn("fetch('data/status-coleta.json'", self.js)
        self.assertIn("fetch('data/fontes.json'", self.js)
        self.assertNotIn("imoveisExemplo", self.js)
        self.assertNotIn("mock", self.js.lower())

    def test_campos_desconhecidos_tem_fallback_sem_inventar_valor(self):
        self.assertIn("v === null || v === undefined || v === ''", self.js)
        self.assertIn("Localização a confirmar", self.js)
        self.assertIn("item.aluguel != null", self.js)
        self.assertIn("item.areaM2 != null", self.js)
        self.assertIn("A confirmar", self.js)

    def test_match_final_exige_todos_componentes_confirmados(self):
        self.assertIn("function matchDisponivel(item)", self.js)
        self.assertIn("m.casa", self.js)
        self.assertIn("m.localizacao", self.js)
        self.assertIn("m.custoBeneficio", self.js)
        self.assertIn("m.visual", self.js)
        self.assertIn("m.confianca !== 'incompleta'", self.js)
        self.assertIn("componentes.every", self.js)
        self.assertIn("Match incompleto", self.js)
        self.assertNotIn("Visual 50", self.js)

    def test_card_prioriza_area_externa_e_hospital(self):
        for termo in ("aluguel", "quartos", "banheiros", "área", "área externa", "Hospital Santa Mônica"):
            self.assertIn(termo, self.js)
        self.assertIn("function areaExternaTexto", self.js)

    def test_distancia_so_aparece_com_localizacao_validada(self):
        self.assertIn("hospital.localizacaoValidada !== true", self.js)
        self.assertIn("hospital.distanciaKm", self.js)
        self.assertIn("hospital.distanciaLinhaRetaKm", self.js)
        self.assertIn("precisaoLocalizacao", self.js)

    def test_visual_sem_fotos_reais_e_indisponivel(self):
        self.assertIn("function fotosConfiaveis(item)", self.js)
        self.assertIn("Sem foto real disponível na fonte", self.js)
        self.assertIn("item.match?.visual == null", self.js)

    def test_galeria_usa_apenas_fotos_reais_do_item(self):
        self.assertIn('id="galeriaModal"', self.html)
        self.assertIn('src="gallery.js"', self.html)
        self.assertIn("fotosConfiaveis(item)", self.gallery)
        self.assertIn("itemDaFoto", self.gallery)
        self.assertNotIn("placeholder", self.gallery.lower())
        self.assertNotIn("unsplash", self.gallery.lower())

    def test_galeria_tem_navegacao_e_acessibilidade(self):
        for termo in ("ArrowLeft", "ArrowRight", "role", "tabindex", "aria-label", "showModal"):
            self.assertIn(termo, self.gallery)

    def test_preco_explicita_faixa_principal_oportunidade_e_teto(self):
        self.assertIn("p >= 2000 && p <= 3000", self.js)
        self.assertIn("p >= 3001 && p <= 3500", self.js)
        self.assertIn("p > 3500", self.js)
        self.assertIn("Oportunidade excepcional", self.js)
        self.assertIn("Abaixo da faixa de referência", self.js)
        self.assertIn("Acima do teto de R$ 3.500", self.js)

    def test_ordenacao_prioriza_elegiveis_e_pendentes(self):
        self.assertIn("function prioridadeCandidato", self.js)
        self.assertIn("prioridadeCandidato(a) - prioridadeCandidato(b)", self.js)

    def test_alertas_sao_condensados(self):
        self.assertIn("Falta confirmar:", self.js)
        self.assertIn("alertas.slice(0, 2)", self.js)
        self.assertNotIn("Requisitos mínimos ainda não confirmados", self.js)

    def test_status_separa_inventario_radar_automacao_e_fotos(self):
        self.assertIn("anúncios acompanhados", self.js)
        self.assertIn("imobiliárias no radar", self.js)
        self.assertIn("automática", self.js)
        self.assertIn("com foto real na coleta atual", self.js)
        self.assertNotIn("capturado(s)", self.js)

    def test_resumo_mostra_fora_dos_criterios(self):
        self.assertIn("fora dos critérios", self.js)
        self.assertIn("anúncios acompanhados", self.js)

    def test_aba_imobiliarias_exibe_acesso_direto_sem_inventar_link(self):
        self.assertIn("function renderImobiliarias", self.js)
        self.assertIn("f.tipo === 'imobiliaria'", self.js)
        self.assertIn("fonte.siteUrl ?", self.js)
        self.assertIn("Site oficial ainda não identificado", self.js)
        self.assertIn('target="_blank"', self.js)
        self.assertIn('rel="noopener noreferrer"', self.js)
        self.assertIn("com acesso direto", self.js)
        self.assertIn("coleta automática autorizada", self.js)

    def test_status_de_fonte_reconhece_catalogos_confirmados_sem_automacao(self):
        self.assertIn("s.includes('sem_automacao')", self.js)
        self.assertIn("s.includes('catalogo_')", self.js)
        self.assertIn("Acesso direto · sem automação", self.js)
        self.assertIn("Acesso direto · no radar", self.js)

    def test_mobile_tabs_nao_dependem_de_scroll_horizontal(self):
        self.assertIn("grid-template-columns:repeat(3,minmax(0,1fr))", self.css)
        self.assertNotIn("scroll-snap-type:x proximity", self.css)

    def test_acoes_mobile_ficam_compactas(self):
        self.assertIn(".acoes{display:grid", self.css)
        self.assertNotIn("flex:1 1 100%", self.css)


if __name__ == "__main__":
    unittest.main()
