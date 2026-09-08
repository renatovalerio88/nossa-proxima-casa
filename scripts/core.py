from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def norm_text(value: Optional[str]) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"\s+", " ", value)
    return value


def property_fingerprint(item: Dict[str, Any]) -> str:
    source_code = norm_text(str(item.get("codigoFonte") or ""))
    source = norm_text(item.get("fonte"))
    if source and source_code:
        base = f"source:{source}|code:{source_code}"
    else:
        parts = [
            norm_text(item.get("cidade")),
            norm_text(item.get("bairro")),
            norm_text(item.get("endereco")),
            str(item.get("quartos") or ""),
            str(item.get("areaM2") or ""),
            str(item.get("aluguel") or ""),
        ]
        base = "|".join(parts)
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:24]


def stable_id(item: Dict[str, Any]) -> str:
    return f"imv_{property_fingerprint(item)}"


def tri_state(value: Any) -> Optional[bool]:
    if value is True or value is False or value is None:
        return value
    text = norm_text(str(value))
    if text in {"sim", "yes", "true", "1"}:
        return True
    if text in {"nao", "não", "no", "false", "0"}:
        return False
    return None


def clamp(value: float, low: float = 0, high: float = 100) -> float:
    return max(low, min(high, value))


def score_house(item: Dict[str, Any], cfg: Dict[str, Any]) -> Tuple[float, List[str], List[str]]:
    c = cfg["criterios"]
    score = 50.0
    positives: List[str] = []
    warnings: List[str] = []

    area = item.get("areaM2")
    if isinstance(area, (int, float)):
        if area >= c["areaMinimaM2"]:
            score += min(18, 8 + (area - c["areaMinimaM2"]) / 10)
            positives.append(f"{area:g} m²")
        else:
            score -= min(35, (c["areaMinimaM2"] - area) * 1.5)
            warnings.append(f"Área abaixo de {c['areaMinimaM2']} m²")
    else:
        warnings.append("Área não informada")

    rooms = item.get("quartos")
    if isinstance(rooms, int):
        if rooms >= c["quartosMinimos"]:
            score += 14 + min(8, (rooms - c["quartosMinimos"]) * 4)
            positives.append(f"{rooms} quartos")
        else:
            score -= 35
            warnings.append(f"Menos de {c['quartosMinimos']} quartos")
    else:
        warnings.append("Quartos não informados")

    for field, label, bonus in [
        ("quintal", "Quintal", 12),
        ("armarios", "Armários", 10),
        ("churrasqueira", "Churrasqueira", 4),
        ("piscina", "Piscina", 4),
        ("hidromassagem", "Hidromassagem", 3),
    ]:
        val = tri_state(item.get(field))
        if val is True:
            score += bonus
            positives.append(label)
        elif val is None and field in {"quintal", "armarios"}:
            warnings.append(f"{label}: não informado")
        elif val is False and field in {"quintal", "armarios"}:
            score -= 6
            warnings.append(f"Sem {label.lower()}")

    return round(clamp(score), 1), positives, warnings


def score_cost(item: Dict[str, Any], cfg: Dict[str, Any]) -> Tuple[float, List[str], List[str]]:
    c = cfg["criterios"]
    price = item.get("aluguel")
    positives: List[str] = []
    warnings: List[str] = []
    if not isinstance(price, (int, float)):
        return 35.0, positives, ["Aluguel não informado"]
    if c["aluguelIdealMin"] <= price <= c["aluguelIdealMax"]:
        midpoint = (c["aluguelIdealMin"] + c["aluguelIdealMax"]) / 2
        score = 95 - abs(price - midpoint) / 50
        positives.append("Preço dentro da faixa ideal")
    elif price < c["aluguelIdealMin"]:
        score = 100
        positives.append("Preço abaixo da faixa ideal")
    elif price <= c["aluguelOportunidadeMax"]:
        score = 78 - (price - c["aluguelIdealMax"]) / 20
        warnings.append("Preço na faixa de oportunidade")
    else:
        score = max(5, 45 - (price - c["aluguelOportunidadeMax"]) / 20)
        warnings.append("Preço acima do teto de oportunidade")
    return round(clamp(score), 1), positives, warnings


def score_location(item: Dict[str, Any]) -> Tuple[float, List[str], List[str]]:
    hospital = item.get("hospital") or {}
    minutes = hospital.get("tempoCarroMin")
    km = hospital.get("distanciaKm")
    positives: List[str] = []
    warnings: List[str] = []

    if isinstance(minutes, (int, float)):
        score = 100 - max(0, minutes - 5) * 4
        positives.append(f"Hospital Santa Mônica: ~{minutes:g} min")
    elif isinstance(km, (int, float)):
        score = 95 - max(0, km - 2) * 7
        positives.append(f"Hospital Santa Mônica: ~{km:g} km")
    else:
        score = 55
        warnings.append("Distância ao Hospital Santa Mônica ainda não calculada")

    comercio = (item.get("comercio") or {}).get("nota")
    if isinstance(comercio, (int, float)):
        score = 0.8 * score + 0.2 * clamp(comercio)
    return round(clamp(score), 1), positives, warnings


def score_visual(item: Dict[str, Any]) -> Tuple[float, List[str], List[str]]:
    visual = item.get("avaliacaoVisual") or {}
    note = visual.get("nota")
    if isinstance(note, (int, float)):
        score = clamp(note * 10)
        return round(score, 1), [f"Avaliação visual: {note:g}/10"], []
    return 50.0, [], ["Avaliação visual ainda não disponível"]


def calculate_match(item: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    casa, p1, w1 = score_house(item, cfg)
    custo, p2, w2 = score_cost(item, cfg)
    loc, p3, w3 = score_location(item)
    visual, p4, w4 = score_visual(item)
    weights = cfg["pesosMatch"]
    final = (
        casa * weights["casa"]
        + loc * weights["localizacao"]
        + custo * weights["custoBeneficio"]
        + visual * weights["visual"]
    ) / sum(weights.values())
    return {
        "casa": casa,
        "localizacao": loc,
        "custoBeneficio": custo,
        "visual": visual,
        "final": round(clamp(final), 1),
        "motivosPositivos": p1 + p2 + p3 + p4,
        "pontosAtencao": w1 + w2 + w3 + w4,
    }


def eligibility(item: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    c = cfg["criterios"]
    reasons: List[str] = []
    missing: List[str] = []
    hard_fail = False

    if norm_text(item.get("cidade")) not in {"divinópolis", "divinopolis"}:
        hard_fail = True
        reasons.append("Fora de Divinópolis")
    if norm_text(item.get("tipo")) not in {"casa", "sobrado", "casa residencial"}:
        hard_fail = True
        reasons.append("Tipo diferente de casa")

    rooms = item.get("quartos")
    area = item.get("areaM2")
    price = item.get("aluguel")

    if not isinstance(rooms, int):
        missing.append("Quartos não confirmados")
    elif rooms < c["quartosMinimos"]:
        hard_fail = True
        reasons.append("Quartos abaixo do mínimo")

    if not isinstance(area, (int, float)):
        missing.append("Área não confirmada")
    elif area < c["areaMinimaM2"]:
        hard_fail = True
        reasons.append("Área abaixo do mínimo")

    if not isinstance(price, (int, float)):
        missing.append("Aluguel não confirmado")
    elif price > c["aluguelOportunidadeMax"]:
        hard_fail = True
        reasons.append("Acima do teto de oportunidade")

    if hard_fail:
        status = "inelegivel"
        eligible = False
    elif missing:
        status = "pendente"
        eligible = False
    else:
        status = "elegivel"
        eligible = True

    return {
        "elegivel": eligible,
        "status": status,
        "motivos": reasons,
        "pendencias": missing,
    }


def merge_inventory(existing: Dict[str, Any], incoming: Iterable[Dict[str, Any]], today: Optional[str] = None) -> Dict[str, Any]:
    today = today or date.today().isoformat()
    current = {x["id"]: deepcopy(x) for x in existing.get("imoveis", []) if x.get("id")}
    seen_ids = set()

    for raw in incoming:
        item = deepcopy(raw)
        item["fingerprint"] = item.get("fingerprint") or property_fingerprint(item)
        item["id"] = item.get("id") or stable_id(item)
        pid = item["id"]
        seen_ids.add(pid)
        old = current.get(pid)
        if old is None:
            item["primeiroVistoEm"] = item.get("primeiroVistoEm") or today
            item["ultimoVistoEm"] = today
            item["disponivel"] = item.get("disponivel", True)
            item.setdefault("historico", [])
            current[pid] = item
            continue

        previous_price = old.get("aluguel")
        new_price = item.get("aluguel")
        history = old.setdefault("historico", [])
        if new_price is not None and previous_price != new_price:
            history.append({"data": today, "campo": "aluguel", "de": previous_price, "para": new_price})

        first_seen = old.get("primeiroVistoEm") or today
        merged = deepcopy(old)
        for key, value in item.items():
            if value is not None:
                merged[key] = value
        merged["primeiroVistoEm"] = first_seen
        merged["ultimoVistoEm"] = today
        merged["disponivel"] = item.get("disponivel", True)
        merged["historico"] = history
        current[pid] = merged

    for pid, item in current.items():
        if pid not in seen_ids and item.get("disponivel") is True:
            item.setdefault("historico", []).append({"data": today, "campo": "disponivel", "de": True, "para": False})
            item["disponivel"] = False

    return {
        "schemaVersion": existing.get("schemaVersion", 1),
        "atualizadoEm": today,
        "imoveis": sorted(current.values(), key=lambda x: (x.get("primeiroVistoEm") or "", x.get("match", {}).get("final", 0)), reverse=True),
    }
