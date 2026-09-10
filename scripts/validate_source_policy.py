from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Set

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

BLOCKED_STATUS = {
    "nao_automatizar_sem_autorizacao",
    "web_crawling_proibido_sem_autorizacao",
    "descoberta_manual_sem_automacao",
    "manual_verificado_sem_automacao",
    "catalogo_publico_confirmado_sem_automacao",
}


def load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def allowed_sources(fontes: Dict) -> Set[str]:
    return {
        row["nome"]
        for row in fontes.get("fontes", [])
        if row.get("coletaAutomatica") is True
    }


def validate_source_flags(fontes: Dict) -> None:
    rows = fontes.get("fontes", [])
    names = [row.get("nome") for row in rows]
    duplicates = sorted({name for name in names if name and names.count(name) > 1})
    if duplicates:
        raise ValueError("Fontes duplicadas: " + ", ".join(duplicates))

    unsafe = [
        row.get("nome")
        for row in rows
        if row.get("coletaAutomatica") is True and row.get("status") in BLOCKED_STATUS
    ]
    if unsafe:
        raise ValueError("Fontes bloqueadas marcadas para automação: " + ", ".join(sorted(unsafe)))

    missing_reason = [
        row.get("nome")
        for row in rows
        if row.get("coletaAutomatica") is False
        and row.get("status") not in {"mesma_operacao_francisco"}
        and not row.get("motivo")
    ]
    if missing_reason:
        raise ValueError("Fontes sem justificativa de política: " + ", ".join(sorted(missing_reason)))


def validate_seed_sources(seeds: Dict, fontes: Dict) -> None:
    allowed = allowed_sources(fontes)
    known = {row.get("nome") for row in fontes.get("fontes", [])}
    configured = {row.get("fonte") for row in seeds.get("urls", [])}
    unknown = {name for name in configured if name and name not in known}
    blocked = {name for name in configured if name and name not in allowed}

    if unknown:
        raise ValueError("Seeds usam fontes não auditadas: " + ", ".join(sorted(unknown)))
    if blocked:
        raise ValueError("Seeds usam fontes sem autorização para coleta automática: " + ", ".join(sorted(blocked)))


def main() -> None:
    fontes = load_json(DATA / "fontes.json")
    seeds = load_json(DATA / "coleta-seeds.json")
    validate_source_flags(fontes)
    validate_seed_sources(seeds, fontes)
    print(
        f"Política de fontes OK: {len(fontes.get('fontes', []))} fontes auditadas, "
        f"{len(seeds.get('urls', []))} seeds em fontes autorizadas/piloto."
    )


if __name__ == "__main__":
    main()
