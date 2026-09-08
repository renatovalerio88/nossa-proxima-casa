from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class QualityError(RuntimeError):
    pass


def load(name: str) -> Dict[str, Any]:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def fail(errors: List[str], message: str) -> None:
    errors.append(message)


def valid_date(value: Any) -> bool:
    return value is None or (isinstance(value, str) and DATE_RE.match(value) is not None)


def validate_inventory(document: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    items = document.get("imoveis")
    if not isinstance(items, list):
        return ["data/imoveis.json: campo 'imoveis' deve ser uma lista"]

    seen_ids: set[str] = set()
    seen_fingerprints: set[str] = set()
    seen_source_codes: set[Tuple[str, str]] = set()

    for index, item in enumerate(items):
        prefix = f"imoveis[{index}]"
        if not isinstance(item, dict):
            fail(errors, f"{prefix}: registro deve ser objeto")
            continue

        source = item.get("fonte")
        url = item.get("url")
        code = item.get("codigoFonte")
        if not isinstance(source, str) or not source.strip():
            fail(errors, f"{prefix}: fonte ausente")
        if not isinstance(url, str) or not url.startswith(("https://", "http://")):
            fail(errors, f"{prefix}: URL de origem ausente ou inválida")

        item_id = item.get("id")
        if item_id:
            if item_id in seen_ids:
                fail(errors, f"{prefix}: id duplicado {item_id}")
            seen_ids.add(item_id)

        fingerprint = item.get("fingerprint")
        if fingerprint:
            if fingerprint in seen_fingerprints:
                fail(errors, f"{prefix}: fingerprint duplicado {fingerprint}")
            seen_fingerprints.add(fingerprint)

        if source and code is not None:
            key = (str(source).strip().lower(), str(code).strip())
            if key in seen_source_codes:
                fail(errors, f"{prefix}: fonte/codigoFonte duplicado {source}/{code}")
            seen_source_codes.add(key)

        first_seen = item.get("primeiroVistoEm")
        last_seen = item.get("ultimoVistoEm")
        if not valid_date(first_seen):
            fail(errors, f"{prefix}: primeiroVistoEm inválido")
        if not valid_date(last_seen):
            fail(errors, f"{prefix}: ultimoVistoEm inválido")
        if item.get("disponivel") is True and (not first_seen or not last_seen):
            fail(errors, f"{prefix}: imóvel disponível sem primeiro/último visto")
        if first_seen and last_seen and first_seen > last_seen:
            fail(errors, f"{prefix}: primeiroVistoEm posterior ao ultimoVistoEm")

        history = item.get("historico", [])
        if not isinstance(history, list):
            fail(errors, f"{prefix}: historico deve ser lista")
        else:
            for hidx, event in enumerate(history):
                if not isinstance(event, dict):
                    fail(errors, f"{prefix}.historico[{hidx}]: evento inválido")
                    continue
                if not valid_date(event.get("data")) or not event.get("data"):
                    fail(errors, f"{prefix}.historico[{hidx}]: data inválida")
                if not event.get("campo"):
                    fail(errors, f"{prefix}.historico[{hidx}]: campo ausente")

        eligibility = item.get("elegibilidade") or {}
        if eligibility.get("elegivel") is True:
            if eligibility.get("status") != "elegivel":
                fail(errors, f"{prefix}: elegivel=true com status diferente de elegivel")
            mandatory = {
                "cidade": item.get("cidade"),
                "tipo": item.get("tipo"),
                "areaM2": item.get("areaM2"),
                "quartos": item.get("quartos"),
                "aluguel": item.get("aluguel"),
            }
            missing = [name for name, value in mandatory.items() if value is None]
            if missing:
                fail(errors, f"{prefix}: imóvel elegível com dados obrigatórios ausentes: {', '.join(missing)}")
            if str(item.get("cidade", "")).strip().lower() not in {"divinópolis", "divinopolis"}:
                fail(errors, f"{prefix}: imóvel elegível fora de Divinópolis")
            if str(item.get("tipo", "")).strip().lower() != "casa":
                fail(errors, f"{prefix}: imóvel elegível não é casa")

        hospital = item.get("hospital") or {}
        if hospital.get("distanciaKm") is not None:
            if hospital.get("tempoCarroMin") is None:
                fail(errors, f"{prefix}: distância por rota sem tempo de carro")
            if not hospital.get("fonteRota"):
                fail(errors, f"{prefix}: distância por rota sem fonte")
            if not hospital.get("referencia"):
                fail(errors, f"{prefix}: distância por rota sem referência do hospital")

    return errors


def validate_collection_status(status: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    if status.get("estado") not in {"ok", "parcial", "indisponivel"}:
        fail(errors, "data/status-coleta.json: estado inválido")
    for field in ("coletados", "indisponiveisConfirmados", "erros"):
        value = status.get(field)
        if not isinstance(value, int) or value < 0:
            fail(errors, f"data/status-coleta.json: {field} deve ser inteiro >= 0")
    sources = status.get("fontes")
    if not isinstance(sources, dict):
        fail(errors, "data/status-coleta.json: fontes deve ser objeto")
    if status.get("estado") == "ok" and status.get("erros", 0) != 0:
        fail(errors, "data/status-coleta.json: estado ok não pode ter erros")
    return errors


def main() -> None:
    inventory = load("imoveis.json")
    status = load("status-coleta.json")
    errors = validate_inventory(inventory) + validate_collection_status(status)
    if errors:
        message = "Falhas de qualidade:\n- " + "\n- ".join(errors)
        raise QualityError(message)
    print(
        "Qualidade OK | "
        f"imóveis={len(inventory.get('imoveis', []))} | "
        f"coletados={status.get('coletados', 0)} | "
        f"estado={status.get('estado')}"
    )


if __name__ == "__main__":
    main()
