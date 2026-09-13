from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class HomeUxContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.ux = (ROOT / "ux-v2.js").read_text(encoding="utf-8")

    def test_home_abre_em_sugestoes(self):
        self.assertIn('class="tab ativo" data-tab="todos">Sugestões</button>', self.index)
        self.assertIn("state.tab = 'todos';", self.ux)
        self.assertIn("disponivelParaSugestao", self.ux)

    def test_minimos_ok_nao_vira_match_artificial(self):
        self.assertIn("el.textContent = 'Mínimos OK';", self.ux)
        self.assertIn("document.querySelectorAll('.match-pendente')", self.ux)
        self.assertIn("el.hidden = true", self.ux)

    def test_decisoes_separam_favorito_descarte_e_indisponibilidade(self):
        self.assertIn("['favorito','descartado','indisponivel']", self.ux)
        self.assertIn('class="indisponivel"', self.index)
        self.assertIn('Já alugado', self.index)
        self.assertIn("state.tab === 'descartados'", self.ux)

    def test_novos_usa_data_real_e_nao_depende_do_navegador(self):
        self.assertIn('const DIAS_NOVO = 7;', self.ux)
        self.assertIn('item.primeiroVistoEm', self.ux)
        self.assertNotIn("npc-inventario-conhecido", self.ux)

    def test_compartilhamento_sincroniza_escolhas_entre_aparelhos(self):
        self.assertIn('id="compartilharEscolhas"', self.index)
        self.assertIn("params.get('escolhas')", self.ux)
        self.assertIn('Escolhas sincronizadas neste aparelho', self.ux)
        self.assertIn('navigator.share', self.ux)

    def test_imobiliarias_ficam_compactas_e_com_acesso_direto(self):
        self.assertIn('imobiliárias no radar', self.ux)
        self.assertIn('Abrir site', self.ux)
        self.assertIn('Sem candidato ativo agora', self.ux)


if __name__ == '__main__':
    unittest.main()
