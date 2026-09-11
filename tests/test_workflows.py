import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class WorkflowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
        cls.validate = (ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8")
        cls.update = (ROOT / ".github/workflows/atualizar-imoveis.yml").read_text(encoding="utf-8")

    def test_pages_depends_on_successful_validation(self):
        self.assertIn("workflow_run:", self.pages)
        self.assertIn("workflows: ['Validar Nossa Próxima Casa']", self.pages)
        self.assertIn("github.event.workflow_run.conclusion == 'success'", self.pages)

    def test_pages_deploys_the_validated_commit(self):
        self.assertIn("github.event.workflow_run.head_sha", self.pages)
        self.assertIn("actions/deploy-pages@v4", self.pages)

    def test_validation_runs_data_quality_and_tests(self):
        self.assertIn("python scripts/validate_data_quality.py", self.validate)
        self.assertIn("python -m unittest discover -s tests -v", self.validate)

    def test_inventory_update_has_source_gate_and_quality_gate(self):
        self.assertIn("python scripts/validate_source_policy.py", self.update)
        self.assertIn("python scripts/validate_data_quality.py", self.update)
        self.assertIn("python -m unittest discover -s tests -v", self.update)


if __name__ == "__main__":
    unittest.main()
