from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, Set

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def allowed_sources(fontes: Dict) -> Set[str]:
    return {
        row["nome"]
        for row in fontes.get("fontes", [])
        if row.get("coletaAutomatica") is True
    }


def validate_seed_sources(seeds: Dict, fontes: Dict) -> None:
    allowed = allowed_sources(fontes)
    configured = {row.get("fonte") for row in seeds.get("urls", [])}
    unknown = {name for name in configured if name and name not in {row.get("nome") for row in fontes.get("fontes", [])}}
    blocked = {name for name in configured if name and name not in allowed}

    if unknown:
        raise ValueError("Seeds usam fontes não auditadas: " + ", ".join(sorted(unknown)))
    if blocked:
        raise ValueError("Seeds usam fontes sem autorização para coleta automática: " + ", ".join(sorted(blocked)))


def main() -> None:
    fontes = load_json(DATA / "fontes.json")
    seeds = load_json(DATA / "coleta-seeds.json")
    validate_seed_sources(seeds, fontes)
    print(f"Política de fontes OK: {len(seeds.get('urls', []))} seeds em fontes autorizadas/piloto.")


if __name__ == "__main__":
    main()
