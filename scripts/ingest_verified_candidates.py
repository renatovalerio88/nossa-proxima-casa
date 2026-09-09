from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

from core import DATA_DIR, calculate_match, eligibility, load_json, property_fingerprint, save_json, stable_id

CANDIDATES_PATH = DATA_DIR / "candidatos-verificados.json"
INVENTORY_PATH = DATA_DIR / "imoveis.json"
CONFIG_PATH = DATA_DIR / "config.json"


def candidate_to_inventory(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Converte uma observação humana/verificada em registro de inventário.

    A data canônica é ``observadoEm``. Este processo nunca usa a data atual para
    ``ultimoVistoEm`` porque a fonte não está sendo coletada automaticamente.
    """
    observed = candidate.get("observadoEm")
    if not observed:
        raise ValueError("Candidato verificado sem observadoEm")

    item = deepcopy(candidate)
    available = item.pop("disponibilidadeObservada", None)
    item.pop("observadoEm", None)
    item["disponivel"] = available
    item["primeiroVistoEm"] = observed
    item["ultimoVistoEm"] = observed
    item["fingerprint"] = item.get("fingerprint") or property_fingerprint(item)
    item["id"] = item.get("id") or stable_id(item)
    item["proveniencia"] = {
        "modo": "verificacao_manual",
        "observadoEm": observed,
        "coletaAutomaticaPermitida": bool(item.get("coletaAutomaticaPermitida")),
        "nota": item.get("notaProveniencia"),
    }
    return item


def merge_candidates(
    inventory: Dict[str, Any], candidates_doc: Dict[str, Any], cfg: Dict[str, Any]
) -> Dict[str, Any]:
    """Inclui/atualiza observações verificadas sem sobrescrever dados mais novos."""
    result = deepcopy(inventory)
    current = {item.get("id"): item for item in result.get("imoveis", []) if item.get("id")}

    for raw in candidates_doc.get("imoveis", []):
        incoming = candidate_to_inventory(raw)
        pid = incoming["id"]
        old = current.get(pid)

        if old is None:
            incoming["historico"] = [
                {
                    "data": incoming["ultimoVistoEm"],
                    "campo": "observacao_verificada",
                    "fonte": incoming.get("fonte"),
                    "url": incoming.get("url"),
                }
            ]
            incoming["elegibilidade"] = eligibility(incoming, cfg)
            incoming["match"] = calculate_match(incoming, cfg)
            current[pid] = incoming
            continue

        old_last = old.get("ultimoVistoEm") or ""
        incoming_last = incoming.get("ultimoVistoEm") or ""
        if old_last > incoming_last:
            continue

        merged = deepcopy(old)
        for key, value in incoming.items():
            if value is not None and key not in {"primeiroVistoEm", "historico"}:
                merged[key] = value
        merged["primeiroVistoEm"] = old.get("primeiroVistoEm") or incoming["primeiroVistoEm"]
        merged["ultimoVistoEm"] = incoming_last
        history = deepcopy(old.get("historico") or [])
        event = {
            "data": incoming_last,
            "campo": "observacao_verificada",
            "fonte": incoming.get("fonte"),
            "url": incoming.get("url"),
        }
        if not history or history[-1] != event:
            history.append(event)
        merged["historico"] = history
        merged["elegibilidade"] = eligibility(merged, cfg)
        merged["match"] = calculate_match(merged, cfg)
        current[pid] = merged

    result["imoveis"] = sorted(
        current.values(),
        key=lambda x: (x.get("primeiroVistoEm") or "", x.get("match", {}).get("final", 0)),
        reverse=True,
    )
    return result


def main() -> None:
    if not CANDIDATES_PATH.exists():
        print("Sem arquivo de candidatos verificados; nada a fazer.")
        return

    cfg = load_json(CONFIG_PATH)
    inventory = load_json(INVENTORY_PATH)
    candidates = load_json(CANDIDATES_PATH)
    merged = merge_candidates(inventory, candidates, cfg)
    save_json(INVENTORY_PATH, merged)
    print(f"Candidatos verificados processados: {len(candidates.get('imoveis', []))}")


if __name__ == "__main__":
    main()
