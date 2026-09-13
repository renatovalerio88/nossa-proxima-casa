from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class HomeUxContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.ux = (ROOT / "ux-v2.js").read_text(encoding="utf-8")
        cls.css = (ROOT / "ux-v2.css").read_text(encoding="utf-8")

    def test_home_abre_em_sugestoes(self):
        self.assertIn('class="tab ativo" data-tab="todos">Sugestões</button>', self.index)
        self.assertIn("state.tab = 'todos';", self.ux)
        self.assertIn("disponivelParaSugestao", self.ux)
        self.assertIn("item.elegibilidade?.elegivel === true", self.ux)

    def test_minimos_ok_nao_vira_match_artificial(self):
        self.assertIn("el.textContent = 'Mínimos OK';", self.ux)
        self.assertIn("document.querySelectorAll('.match-pendente')", self.ux)
        self.assertIn("el.hidden = true", self.ux)
        self.assertIn("avaliação visual ainda não calculada", self.ux)
        self.assertIn("el.remove()", self.ux)

    def test_decisoes_separam_favorito_descarte_e_indisponibilidade(self):
        self.assertIn("['favorito','descartado','indisponivel']", self.ux)
        self.assertIn('class="indisponivel"', self.index)
        self.assertIn('⌂ Alugado', self.index)
        self.assertIn("state.tab === 'descartados'", self.ux)
        self.assertIn("Alugado / indisponível", self.ux)

    def test_novos_usa_data_real_e_vistos_persistentes(self):
        self.assertIn('const DIAS_NOVO = 7;', self.ux)
        self.assertIn('item.primeiroVistoEm', self.ux)
        self.assertIn("const CHAVE_VISTOS = 'npc-novos-vistos';", self.ux)
        self.assertNotIn("npc-inventario-conhecido", self.ux)

    def test_compartilhamento_sincroniza_escolhas_entre_aparelhos(self):
        self.assertIn('id="compartilharEscolhas"', self.index)
        self.assertIn('Sincronizar celulares', self.index)
        self.assertIn("params.get('escolhas')", self.ux)
        self.assertIn('Celular sincronizado', self.ux)
        self.assertIn('navigator.share', self.ux)
        self.assertIn('vistos:[...vistosNovos]', self.ux)

    def test_imobiliarias_ficam_compactas_e_com_acesso_direto(self):
        self.assertIn('imobiliárias no radar', self.ux)
        self.assertIn('Abrir site', self.ux)
        self.assertIn('Sem candidato ativo', self.ux)

    def test_arte_reduz_texto_tecnico_e_prioriza_decisao(self):
        self.assertIn('Casas que valem abrir em Divinópolis.', self.index)
        self.assertIn("texto.replace(/^Falta confirmar", self.ux)
        self.assertIn("'Sem foto'", self.ux)
        self.assertIn('.proveniencia-secundaria{display:none!important}', self.css)
        self.assertIn('grid-template-columns:repeat(3,minmax(0,1fr))', self.css)

    def test_estados_vazios_explicam_cada_aba(self):
        self.assertIn('Sem sugestões confirmadas agora.', self.ux)
        self.assertIn('Nada novo por aqui.', self.ux)
        self.assertIn('Nada pendente agora.', self.ux)
        self.assertIn('Nenhum favorito ainda.', self.ux)
        self.assertIn('Nada descartado.', self.ux)


if __name__ == '__main__':
    unittest.main()
