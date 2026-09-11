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
        parts = [norm_text(item.get("cidade")), norm_text(item.get("bairro")), norm_text(item.get("endereco")), str(item.get("quartos") or ""), str(item.get("areaM2") or ""), str(item.get("aluguel") or "")]
        base = "|".join(parts)
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:24]


def stable_id(item: Dict[str, Any]) -> str:
    return f"imv_{property_fingerprint(item)}"


def tri_state(value: Any) -> Optional[bool]:
    if value is True or value is False or value is None:
        return value
    text = norm_text(str(value))
    if text in {"sim", "yes", "true", "1"}: return True
    if text in {"nao", "não", "no", "false", "0"}: return False
    return None


def clamp(value: float, low: float = 0, high: float = 100) -> float:
    return max(low, min(high, value))


def private_external_area(item: Dict[str, Any]) -> Optional[bool]:
    explicit = tri_state(item.get("areaExternaPrivativa"))
    return explicit if explicit is not None else tri_state(item.get("quintal"))


def score_house(item: Dict[str, Any], cfg: Dict[str, Any]) -> Tuple[Optional[float], List[str], List[str]]:
    c = cfg["criterios"]
    positives, warnings = [], []
    score, complete = 55.0, True
    area = item.get("areaM2")
    if isinstance(area, (int, float)):
        if area >= c["areaMinimaM2"]:
            score += min(15, 7 + (area - c["areaMinimaM2"]) / 12); positives.append(f"{area:g} m²")
        else: complete = False; warnings.append(f"Área abaixo de {c['areaMinimaM2']} m²")
    else: complete = False; warnings.append("Área não informada")
    rooms = item.get("quartos")
    if isinstance(rooms, int):
        if rooms >= c["quartosMinimos"]:
            score += 12 + min(8, (rooms - c["quartosMinimos"]) * 4); positives.append(f"{rooms} quartos")
        else: complete = False; warnings.append(f"Menos de {c['quartosMinimos']} quartos")
    else: complete = False; warnings.append("Quartos não informados")
    min_baths, baths = c.get("banheirosMinimos"), item.get("banheiros")
    if isinstance(min_baths, int):
        if isinstance(baths, int) and baths >= min_baths:
            score += 8 + min(4, (baths - min_baths) * 2); positives.append(f"{baths} banheiros")
        else:
            complete = False; warnings.append("Banheiros não informados" if baths is None else f"Menos de {min_baths} banheiros")
    if c.get("areaExternaPrivativaObrigatoria"):
        ext = private_external_area(item)
        if ext is True: score += 12; positives.append("Área externa privativa")
        else: complete = False; warnings.append("Área externa privativa não confirmada" if ext is None else "Sem área externa privativa")
    for field, label, bonus in [("armarios", "Armários", 8), ("churrasqueira", "Churrasqueira", 4), ("piscina", "Piscina", 4), ("hidromassagem", "Hidromassagem", 3)]:
        val = tri_state(item.get(field))
        if val is True: score += bonus; positives.append(label)
        elif val is None and field == "armarios": warnings.append("Armários: não informado")
    return (round(clamp(score), 1) if complete else None), positives, warnings


def score_cost(item: Dict[str, Any], cfg: Dict[str, Any]) -> Tuple[Optional[float], List[str], List[str]]:
    c, price = cfg["criterios"], item.get("aluguel")
    if not isinstance(price, (int, float)): return None, [], ["Aluguel não informado"]
    if c["aluguelIdealMin"] <= price <= c["aluguelIdealMax"]:
        midpoint = (c["aluguelIdealMin"] + c["aluguelIdealMax"]) / 2
        return round(clamp(96 - abs(price - midpoint) / 55), 1), ["Preço dentro da faixa principal"], []
    if price < c["aluguelIdealMin"]:
        return round(clamp(72 - min(22, (c["aluguelIdealMin"] - price) / 35)), 1), [], ["Preço abaixo da faixa principal; só vale como oportunidade real"]
    if price <= c["aluguelOportunidadeMax"]:
        return round(clamp(76 - (price - c["aluguelIdealMax"]) / 24), 1), [], ["Preço acima da faixa principal; exige oportunidade excepcional"]
    return 0.0, [], ["Preço acima do teto de oportunidade"]


def score_location(item: Dict[str, Any]) -> Tuple[Optional[float], List[str], List[str]]:
    hospital = item.get("hospital") or {}
    if hospital.get("localizacaoValidada") is not True:
        return None, [], ["Localização ainda não validada para calcular distância ao Hospital Santa Mônica"]
    km, straight_km = hospital.get("distanciaKm"), hospital.get("distanciaLinhaRetaKm")
    precision = norm_text(hospital.get("precisaoLocalizacao"))
    if isinstance(km, (int, float)):
        score = 95 - max(0, km - 2) * 7; suffix = " (aprox. pelo bairro)" if precision == "bairro" else ""
        positives = [f"Hospital Santa Mônica: ~{km:g} km{suffix}"]
    elif isinstance(straight_km, (int, float)):
        score = 90 - max(0, straight_km - 2) * 7; suffix = " (aprox. pelo bairro)" if precision == "bairro" else " (linha reta)"
        positives = [f"Hospital Santa Mônica: ~{straight_km:g} km{suffix}"]
    else: return None, [], ["Distância ao Hospital Santa Mônica ainda não calculada"]
    comercio = (item.get("comercio") or {}).get("nota")
    if isinstance(comercio, (int, float)): score = 0.8 * score + 0.2 * clamp(comercio)
    return round(clamp(score), 1), positives, []


def score_visual(item: Dict[str, Any]) -> Tuple[Optional[float], List[str], List[str]]:
    photos = item.get("fotos") if isinstance(item.get("fotos"), list) else []
    note = (item.get("avaliacaoVisual") or {}).get("nota")
    if photos and isinstance(note, (int, float)): return round(clamp(note * 10), 1), [f"Avaliação visual: {note:g}/10"], []
    return None, [], ["Avaliação visual indisponível sem fotos reais avaliadas"]


def _hospital_km(item: Dict[str, Any]) -> Optional[float]:
    hospital = item.get("hospital") or {}
    if hospital.get("localizacaoValidada") is not True:
        return None
    for field in ("distanciaKm", "distanciaLinhaRetaKm"):
        value = hospital.get(field)
        if isinstance(value, (int, float)): return float(value)
    return None


def opportunity_justification(item: Dict[str, Any], cfg: Dict[str, Any]) -> Optional[str]:
    c, op = cfg["criterios"], cfg["criterios"].get("oportunidade") or {}
    km = _hospital_km(item); max_km = op.get("distanciaHospitalMaxKm", 8)
    if km is None or km > max_km: return None
    highlights = []
    area = item.get("areaM2")
    if isinstance(area, (int, float)) and area >= op.get("areaDestaqueM2", c["areaMinimaM2"] + 20): highlights.append(f"área de {area:g} m²")
    if op.get("aceitaQuartoExtra") and isinstance(item.get("quartos"), int) and item["quartos"] > c["quartosMinimos"]: highlights.append(f"{item['quartos']} quartos")
    if op.get("aceitaArmarios") and tri_state(item.get("armarios")) is True: highlights.append("armários confirmados")
    return f"Oportunidade excepcional: {highlights[0]} e ~{km:g} km do Hospital Santa Mônica" if highlights else None


def eligibility(item: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    c, reasons, missing, hard_fail = cfg["criterios"], [], [], False
    if norm_text(item.get("cidade")) not in {"divinópolis", "divinopolis"}: hard_fail = True; reasons.append("Fora de Divinópolis")
    if norm_text(item.get("tipo")) not in {"casa", "sobrado", "casa residencial"}: hard_fail = True; reasons.append("Tipo diferente de casa")
    for field, minimum, label in [("quartos", c["quartosMinimos"], "Quartos"), ("banheiros", c.get("banheirosMinimos"), "Banheiros"), ("areaM2", c["areaMinimaM2"], "Área")]:
        if minimum is None: continue
        value = item.get(field)
        if not isinstance(value, (int, float)) or isinstance(value, bool): missing.append(f"{label} não confirmados" if label != "Área" else "Área não confirmada")
        elif value < minimum: hard_fail = True; reasons.append(f"{label} abaixo do mínimo")
    if c.get("areaExternaPrivativaObrigatoria"):
        ext = private_external_area(item)
        if ext is None: missing.append("Área externa privativa não confirmada")
        elif ext is False: hard_fail = True; reasons.append("Sem área externa privativa")
    price, opportunity = item.get("aluguel"), None
    if not isinstance(price, (int, float)): missing.append("Aluguel não confirmado")
    elif price > c["aluguelOportunidadeMax"]: hard_fail = True; reasons.append("Acima do teto de oportunidade")
    elif price < c["aluguelIdealMin"] or price > c["aluguelIdealMax"]:
        opportunity = opportunity_justification(item, cfg)
        if opportunity is None: hard_fail = True; reasons.append("Fora da faixa principal sem justificativa de oportunidade forte")
    status = "inelegivel" if hard_fail else "pendente" if missing else "elegivel"
    return {"elegivel": status == "elegivel", "status": status, "motivos": reasons, "pendencias": missing, "oportunidade": opportunity}


def calculate_match(item: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    casa, p1, w1 = score_house(item, cfg); custo, p2, w2 = score_cost(item, cfg); loc, p3, w3 = score_location(item); visual, p4, w4 = score_visual(item)
    result, weights = eligibility(item, cfg), cfg["pesosMatch"]
    components = {"casa": casa, "localizacao": loc, "custoBeneficio": custo, "visual": visual}
    available_weight = sum(weights[k] for k, v in components.items() if v is not None); total_weight = sum(weights.values())
    all_confirmed = all(value is not None for value in components.values())
    final = None
    if result["elegivel"] and all_confirmed and total_weight:
        final = round(clamp(sum(components[k] * weights[k] for k in components) / total_weight), 1)
    coverage = round(available_weight / total_weight * 100, 1) if total_weight else 0.0
    confidence = "alta" if final is not None and coverage == 100 else "incompleta"
    return {**components, "final": final, "confianca": confidence, "coberturaPesoPct": coverage, "motivosPositivos": p1+p2+p3+p4, "pontosAtencao": w1+w2+w3+w4}


def reapply_rules(document: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    updated = deepcopy(document); rows = []
    for raw in updated.get("imoveis", []):
        row = deepcopy(raw); row["elegibilidade"] = eligibility(row, cfg); row["match"] = calculate_match(row, cfg); rows.append(row)
    updated["imoveis"] = sorted(rows, key=lambda x: (x.get("primeiroVistoEm") or "", x.get("match", {}).get("final") or -1), reverse=True)
    return updated


def _append_history(history: List[Dict[str, Any]], event: Dict[str, Any]) -> None:
    if not history or history[-1] != event: history.append(event)


def merge_inventory(existing: Dict[str, Any], incoming: Iterable[Dict[str, Any]], today: Optional[str] = None) -> Dict[str, Any]:
    today = today or date.today().isoformat(); current = {x["id"]: deepcopy(x) for x in existing.get("imoveis", []) if x.get("id")}
    for raw in incoming:
        item = deepcopy(raw); item["fingerprint"] = item.get("fingerprint") or property_fingerprint(item); item["id"] = item.get("id") or stable_id(item); pid = item["id"]; old = current.get(pid)
        if old is None and item.get("disponivel") is False: continue
        if old is None:
            item["primeiroVistoEm"] = item.get("primeiroVistoEm") or today; item["ultimoVistoEm"] = today; item["disponivel"] = item.get("disponivel", True); item.setdefault("historico", []); current[pid] = item; continue
        history = deepcopy(old.get("historico") or []); previous_price, new_price = old.get("aluguel"), item.get("aluguel")
        if new_price is not None and previous_price != new_price: _append_history(history, {"data": today, "campo": "aluguel", "de": previous_price, "para": new_price})
        previous_availability = old.get("disponivel", True); new_availability = item.get("disponivel", previous_availability)
        if new_availability is not previous_availability: _append_history(history, {"data": today, "campo": "disponivel", "de": previous_availability, "para": new_availability})
        merged = deepcopy(old)
        for key, value in item.items():
            if value is not None: merged[key] = value
        merged["historico"] = history; merged["primeiroVistoEm"] = old.get("primeiroVistoEm") or today; merged["ultimoVistoEm"] = today
        current[pid] = merged
    return {**existing, "atualizadoEm": today, "imoveis": list(current.values())}