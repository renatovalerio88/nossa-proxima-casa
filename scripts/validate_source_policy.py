from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Set
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

# Automação é opt-in: qualquer status novo fica bloqueado até ser explicitamente
# revisado e incluído nesta lista. Isso evita que uma simples mudança de rótulo
# habilite coleta sem querer.
ALLOWED_AUTOMATION_STATUS = {
    "piloto_baixa_frequencia",
    "automacao_autorizada",
    "api_oficial",
}


def load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def allowed_sources(fontes: Dict) -> Set[str]:
    return {
        row["nome"]
        for row in fontes.get("fontes", [])
        if row.get("coletaAutomatica") is True
        and row.get("status") in ALLOWED_AUTOMATION_STATUS
    }


def _is_https_url(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    parsed = urlparse(value.strip())
    return parsed.scheme == "https" and bool(parsed.netloc)


def validate_source_flags(fontes: Dict) -> None:
    rows = fontes.get("fontes", [])
    names = [row.get("nome") for row in rows]
    duplicates = sorted({name for name in names if name and names.count(name) > 1})
    if duplicates:
        raise ValueError("Fontes duplicadas: " + ", ".join(duplicates))

    unnamed = [str(index) for index, row in enumerate(rows) if not row.get("nome")]
    if unnamed:
        raise ValueError("Fontes sem nome nos índices: " + ", ".join(unnamed))

    unsafe = [
        row.get("nome")
        for row in rows
        if row.get("coletaAutomatica") is True
        and row.get("status") not in ALLOWED_AUTOMATION_STATUS
    ]
    if unsafe:
        raise ValueError(
            "Fontes sem status explicitamente autorizado marcadas para automação: "
            + ", ".join(sorted(unsafe))
        )

    missing_reason = [
        row.get("nome")
        for row in rows
        if row.get("coletaAutomatica") is False
        and row.get("status") not in {"mesma_operacao_francisco"}
        and not row.get("motivo")
    ]
    if missing_reason:
        raise ValueError("Fontes sem justificativa de política: " + ", ".join(sorted(missing_reason)))

    invalid_urls = [
        row.get("nome")
        for row in rows
        if row.get("siteUrl") is not None and not _is_https_url(row.get("siteUrl"))
    ]
    if invalid_urls:
        raise ValueError(
            "Fontes com siteUrl inválida ou não HTTPS: " + ", ".join(sorted(invalid_urls))
        )


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
