from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class HomeUxContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.ux = (ROOT / "ux-v2.js").read_text(encoding="utf-8")

    def test_home_abre_em_todos(self):
        self.assertIn('class="tab ativo" data-tab="todos"', self.index)
        self.assertIn("state.tab = 'todos';", self.ux)
        self.assertIn("b.dataset.tab === 'todos'", self.ux)

    def test_minimos_ok_nao_e_recomendacao(self):
        self.assertIn("el.textContent = 'Mínimos OK';", self.ux)
        self.assertIn('Isso não significa recomendação final.', self.ux)

    def test_match_incompleto_nao_inventa_nota(self):
        self.assertIn("texto.textContent = 'Sem nota';", self.ux)
        self.assertIn('O Match só aparece quando todos os componentes necessários estão disponíveis.', self.ux)

    def test_imobiliarias_explica_cobertura_sem_raspagem_nao_autorizada(self):
        self.assertIn('sem raspagem não autorizada', self.ux)
        self.assertIn('candidatos só entram após verificação individual', self.ux)


if __name__ == '__main__':
    unittest.main()
