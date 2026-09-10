from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HTTP_RE = re.compile(r"^https?://", re.IGNORECASE)


class QualityError(RuntimeError):
    pass


def load(name: str) -> Dict[str, Any]:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def fail(errors: List[str], message: str) -> None:
    errors.append(message)


def valid_date(value: Any) -> bool:
    return value is None or (isinstance(value, str) and DATE_RE.match(value) is not None)


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def reliable_photos(item: Dict[str, Any]) -> List[str]:
    raw: List[Any] = [item.get("fotoUrl"), item.get("imagemUrl")]
    for field in ("fotos", "imagens"):
        value = item.get(field)
        if isinstance(value, list):
            raw.extend(value)
    return [str(url) for url in raw if isinstance(url, str) and url.startswith("https://")]


def validate_inventory(document: Dict[str, Any], config: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    items = document.get("imoveis")
    if not isinstance(items, list):
        return ["data/imoveis.json: campo 'imoveis' deve ser uma lista"]

    criteria = config.get("criterios") or {}
    min_area = criteria.get("areaMinimaM2", 90)
    min_bedrooms = criteria.get("quartosMinimos", 3)
    min_bathrooms = criteria.get("banheirosMinimos", 2)
    external_required = criteria.get("areaExternaPrivativaObrigatoria", True)
    price_min = criteria.get("aluguelIdealMin", 2000)
    price_max = criteria.get("aluguelIdealMax", 3000)
    opportunity_max = criteria.get("aluguelOportunidadeMax", 3500)

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

        # Fonte/URL desconhecidas devem permanecer null; quando informadas, precisam ser válidas.
        if source is not None and (not isinstance(source, str) or not source.strip()):
            fail(errors, f"{prefix}: fonte deve ser string não vazia ou null")
        if url is not None and (not isinstance(url, str) or HTTP_RE.match(url) is None):
            fail(errors, f"{prefix}: URL de origem deve ser http(s) válida ou null")

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
        status = eligibility.get("status")
        eligible = eligibility.get("elegivel") is True
        pending = eligibility.get("pendencias") or []
        opportunity = eligibility.get("oportunidade")

        if status not in {"elegivel", "pendente", "inelegivel"}:
            fail(errors, f"{prefix}: status de elegibilidade inválido")
        if eligible and status != "elegivel":
            fail(errors, f"{prefix}: elegivel=true com status diferente de elegivel")
        if status == "elegivel" and not eligible:
            fail(errors, f"{prefix}: status=elegivel sem elegivel=true")
        if status == "pendente" and not pending:
            fail(errors, f"{prefix}: status pendente sem pendências explícitas")

        area = item.get("areaM2")
        bedrooms = item.get("quartos")
        bathrooms = item.get("banheiros")
        price = item.get("aluguel")
        external = item.get("areaExternaPrivativa") is True or item.get("quintal") is True

        if eligible:
            mandatory = {
                "cidade": item.get("cidade"),
                "tipo": item.get("tipo"),
                "areaM2": area,
                "quartos": bedrooms,
                "banheiros": bathrooms,
                "aluguel": price,
            }
            missing = [name for name, value in mandatory.items() if value is None]
            if external_required and not external:
                missing.append("areaExternaPrivativa")
            if missing:
                fail(errors, f"{prefix}: imóvel elegível com requisitos obrigatórios ausentes: {', '.join(missing)}")

            if str(item.get("cidade", "")).strip().lower() not in {"divinópolis", "divinopolis"}:
                fail(errors, f"{prefix}: imóvel elegível fora de Divinópolis")
            if str(item.get("tipo", "")).strip().lower() != "casa":
                fail(errors, f"{prefix}: imóvel elegível não é casa")
            if is_number(area) and area < min_area:
                fail(errors, f"{prefix}: imóvel elegível com área abaixo do mínimo")
            if is_number(bedrooms) and bedrooms < min_bedrooms:
                fail(errors, f"{prefix}: imóvel elegível com quartos abaixo do mínimo")
            if is_number(bathrooms) and bathrooms < min_bathrooms:
                fail(errors, f"{prefix}: imóvel elegível com banheiros abaixo do mínimo")
            if is_number(price):
                if price > opportunity_max:
                    fail(errors, f"{prefix}: imóvel elegível acima do teto de oportunidade")
                if (price < price_min or price > price_max) and not opportunity:
                    fail(errors, f"{prefix}: imóvel fora da faixa principal elegível sem justificativa objetiva de oportunidade")

        # Campos mínimos desconhecidos nunca podem resultar em elegibilidade confirmada.
        required_unknown = (
            area is None
            or bedrooms is None
            or bathrooms is None
            or price is None
            or (external_required and not external)
        )
        if required_unknown and eligible:
            fail(errors, f"{prefix}: critérios mínimos confirmados apesar de requisito obrigatório ausente")

        photos = reliable_photos(item)
        match = item.get("match") or {}
        components = [match.get("casa"), match.get("localizacao"), match.get("custoBeneficio"), match.get("visual")]
        final_match = match.get("final")

        if match.get("visual") is not None and not photos:
            fail(errors, f"{prefix}: nota visual informada sem foto real HTTPS")
        if match.get("visual") == 50 and not photos:
            fail(errors, f"{prefix}: Visual 50 artificial sem evidência")

        complete_components = all(is_number(value) for value in components)
        if final_match is not None and not complete_components:
            fail(errors, f"{prefix}: Match final calculado com componente relevante ausente")
        if final_match is not None and not eligible:
            fail(errors, f"{prefix}: Match final publicado para imóvel não elegível")
        if final_match is None and match and match.get("confianca") not in {"incompleta", "baixa", None}:
            fail(errors, f"{prefix}: Match incompleto com confiança enganosa")
        if final_match is not None and not is_number(final_match):
            fail(errors, f"{prefix}: Match final deve ser numérico ou null")

        hospital = item.get("hospital") or {}
        for distance_field in ("distanciaKm", "distanciaLinhaRetaKm"):
            distance = hospital.get(distance_field)
            if distance is not None and (not is_number(distance) or distance < 0):
                fail(errors, f"{prefix}: {distance_field} inválida")
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
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            fail(errors, f"data/status-coleta.json: {field} deve ser inteiro >= 0")
    sources = status.get("fontes")
    if not isinstance(sources, dict):
        fail(errors, "data/status-coleta.json: fontes deve ser objeto")
    if status.get("estado") == "ok" and status.get("erros", 0) != 0:
        fail(errors, "data/status-coleta.json: estado ok não pode ter erros")
    return errors


def main() -> None:
    inventory = load("imoveis.json")
    config = load("config.json")
    status = load("status-coleta.json")
    errors = validate_inventory(inventory, config) + validate_collection_status(status)
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
