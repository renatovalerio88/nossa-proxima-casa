from __future__ import annotations

import json
import math
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional, Tuple

try:
    from core import DATA_DIR, calculate_match, load_json, save_json
except ModuleNotFoundError:
    from scripts.core import DATA_DIR, calculate_match, load_json, save_json

CACHE_PATH = DATA_DIR / "geocode-cache.json"
INVENTORY_PATH = DATA_DIR / "imoveis.json"
UA = "NossaProximaCasa/1.0 (https://github.com/renatovalerio88/nossa-proxima-casa)"
NOMINATIM = "https://nominatim.openstreetmap.org/search"
OSRM = "https://router.project-osrm.org/route/v1/driving"


def http_json(url: str, timeout: int = 20) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def query_for(item: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    city = item.get("cidade") or "Divinópolis"
    if item.get("endereco"):
        return f"{item['endereco']}, {city}, MG, Brasil", "endereco"
    if item.get("bairro"):
        return f"{item['bairro']}, {city}, MG, Brasil", "bairro"
    return None


def hospital_reference(hospital_cfg: Dict[str, Any], cache: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    lat = hospital_cfg.get("latitude")
    lon = hospital_cfg.get("longitude")
    if lat is not None and lon is not None:
        return {
            "latitude": float(lat),
            "longitude": float(lon),
            "displayName": hospital_cfg.get("endereco"),
            "fonte": hospital_cfg.get("fonteCoordenadas"),
        }

    query = hospital_cfg.get("endereco")
    if not query:
        return None
    return geocode(query, cache)


def geocode(query: str, cache: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    key = f"geo:{query.lower()}"
    if key in cache:
        return cache[key]
    params = urllib.parse.urlencode({"q": query, "format": "jsonv2", "limit": 1, "countrycodes": "br"})
    data = http_json(f"{NOMINATIM}?{params}")
    result = None
    if data:
        result = {
            "latitude": float(data[0]["lat"]),
            "longitude": float(data[0]["lon"]),
            "displayName": data[0].get("display_name"),
        }
    cache[key] = result
    time.sleep(1.05)
    return result


def haversine_km(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    radius = 6371.0088
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp = math.radians(b_lat - a_lat)
    dl = math.radians(b_lon - a_lon)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(h), math.sqrt(1 - h))


def route(origin: Dict[str, Any], destination: Dict[str, Any], cache: Dict[str, Any]) -> Optional[Dict[str, float]]:
    key = (
        f"route:{origin['latitude']:.6f},{origin['longitude']:.6f}:"
        f"{destination['latitude']:.6f},{destination['longitude']:.6f}"
    )
    if key in cache:
        return cache[key]
    coords = (
        f"{origin['longitude']},{origin['latitude']};"
        f"{destination['longitude']},{destination['latitude']}"
    )
    params = urllib.parse.urlencode({"overview": "false", "alternatives": "false", "steps": "false"})
    data = http_json(f"{OSRM}/{coords}?{params}")
    result = None
    if data.get("code") == "Ok" and data.get("routes"):
        r = data["routes"][0]
        result = {
            "distanciaKm": round(float(r["distance"]) / 1000, 1),
            "tempoCarroMin": round(float(r["duration"]) / 60),
        }
    cache[key] = result
    return result


def load_cache() -> Dict[str, Any]:
    if not CACHE_PATH.exists():
        return {"schemaVersion": 1, "entries": {}}
    return load_json(CACHE_PATH)


def main() -> None:
    cfg = load_json(DATA_DIR / "config.json")
    inventory = load_json(INVENTORY_PATH)
    cache_doc = load_cache()
    cache = cache_doc.setdefault("entries", {})

    hospital_cfg = cfg.get("referencias", {}).get("hospital", {})
    try:
        hospital_geo = hospital_reference(hospital_cfg, cache)
    except Exception as exc:
        print(f"Referência do hospital indisponível: {type(exc).__name__}: {exc}")
        save_json(CACHE_PATH, cache_doc)
        return

    if not hospital_geo:
        print("Hospital sem coordenadas/endereço resolvível; inventário preservado.")
        save_json(CACHE_PATH, cache_doc)
        return

    changed = 0
    for item in inventory.get("imoveis", []):
        query_data = query_for(item)
        if not query_data:
            continue
        query, precision = query_data
        try:
            geo = geocode(query, cache)
        except Exception as exc:
            print(f"Geocodificação falhou para {item.get('id')}: {type(exc).__name__}: {exc}")
            continue
        if not geo:
            continue

        item["latitude"] = geo["latitude"]
        item["longitude"] = geo["longitude"]
        hospital = dict(item.get("hospital") or {})
        hospital["referencia"] = hospital_cfg.get("nome", "Hospital Santa Mônica")
        hospital["precisaoLocalizacao"] = precision
        hospital["fonteReferencia"] = hospital_cfg.get("fonteCoordenadas")
        hospital["distanciaLinhaRetaKm"] = round(
            haversine_km(geo["latitude"], geo["longitude"], hospital_geo["latitude"], hospital_geo["longitude"]), 1
        )
        try:
            routed = route(geo, hospital_geo, cache)
        except Exception as exc:
            print(f"Rota indisponível para {item.get('id')}: {type(exc).__name__}: {exc}")
            routed = None
        if routed:
            hospital.update(routed)
            hospital["fonteRota"] = "OSRM/OpenStreetMap"
        else:
            hospital["distanciaKm"] = None
            hospital["tempoCarroMin"] = None
        item["hospital"] = hospital
        item["match"] = calculate_match(item, cfg)
        changed += 1

    save_json(CACHE_PATH, cache_doc)
    if changed:
        save_json(INVENTORY_PATH, inventory)
    print(f"Localização enriquecida em {changed} imóvel(is).")


if __name__ == "__main__":
    main()
