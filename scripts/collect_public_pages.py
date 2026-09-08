from __future__ import annotations

import datetime as dt
import html
import json
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = DATA / "coleta-atual.json"
STATUS = DATA / "status-coleta.json"
UA = "Mozilla/5.0 (compatible; NossaProximaCasa/1.0; +https://github.com/renatovalerio88/nossa-proxima-casa)"


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: List[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.parts.append(text)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def extract_text(body: str) -> str:
    parser = TextExtractor()
    parser.feed(body)
    return html.unescape("\n".join(parser.parts))


def fetch_with_urllib(url: str) -> str:
    headers = {
        "User-Agent": UA,
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.5",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Cache-Control": "no-cache",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=18) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def fetch_with_curl(url: str) -> str:
    curl = shutil.which("curl")
    if not curl:
        raise RuntimeError("curl não disponível para fallback")

    cmd = [
        curl,
        "--fail",
        "--location",
        "--silent",
        "--show-error",
        "--compressed",
        "--http1.1",
        "--ipv4",
        "--connect-timeout",
        "10",
        "--max-time",
        "35",
        "--retry",
        "2",
        "--retry-delay",
        "2",
        "--retry-connrefused",
        "--user-agent",
        UA,
        "--header",
        "Accept-Language: pt-BR,pt;q=0.9,en;q=0.5",
        "--header",
        "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=50, check=False)
    if result.returncode != 0:
        detail = (result.stderr or "curl falhou").strip().replace("\n", " ")
        raise RuntimeError(f"curl exit {result.returncode}: {detail[:350]}")
    if not result.stdout.strip():
        raise RuntimeError("curl retornou resposta vazia")
    return result.stdout


def fetch_text(url: str) -> str:
    errors: List[str] = []

    try:
        return extract_text(fetch_with_urllib(url))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        errors.append(f"urllib={type(exc).__name__}: {exc}")

    try:
        return extract_text(fetch_with_curl(url))
    except (RuntimeError, subprocess.TimeoutExpired, OSError) as exc:
        errors.append(f"curl={type(exc).__name__}: {exc}")

    raise RuntimeError(" | ".join(errors))


def money_to_float(raw: str) -> float:
    return float(raw.replace(".", "").replace(",", "."))


def first(pattern: str, text: str, flags: int = re.I | re.S) -> Optional[str]:
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None


def clean_location(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    parts = [p.strip(" ,-·") for p in re.split(r"[\r\n]+", raw) if p.strip(" ,-·")]
    parts = [p for p in parts if p.upper() not in {"MG", "MINAS GERAIS"}]
    return parts[-1] if parts else None


def has_any(text: str, terms: List[str]) -> Optional[bool]:
    low = text.lower()
    return True if any(term in low for term in terms) else None


def base(seed: Dict) -> Dict:
    return {
        "fonte": seed["fonte"],
        "codigoFonte": seed["codigoFonte"],
        "url": seed["url"],
        "cidade": "Divinópolis",
        "endereco": None,
        "latitude": None,
        "longitude": None,
        "fotos": [],
        "publicadoEm": None,
        "hospital": {},
        "comercio": {},
        "avaliacaoVisual": {},
        "disponivel": True,
    }


def parse_casa_nova(text: str, seed: Dict) -> Dict:
    row = base(seed)
    price = first(r"Valor do aluguel:\s*R\$\s*([\d\.]+,\d{2})", text)
    rooms = first(r"(\d+)\s*Quarto\(s\)", text)
    baths = first(r"(\d+)\s*Banhos?\(s\)", text)
    parking = first(r"(\d+)\s*Vagas?\(s\)", text)
    area = first(r"([\d\.,]+)\s*m²", text)
    location = clean_location(first(r"([A-Za-zÀ-ÿ\s]+)\s*·\s*Divinopolis", text))
    desc = first(r"Descrição\s*(.*?)\s*(?:iframe|Fale com nossos consultores|Fale com nossos corretores|Os preços)", text)
    title = first(r"#?\s*(Casa\s+Aluguel)", text) or "Casa Aluguel"
    row.update({
        "titulo": title,
        "tipo": "casa",
        "bairro": location,
        "aluguel": money_to_float(price) if price else None,
        "areaM2": money_to_float(area) if area else None,
        "quartos": int(rooms) if rooms else None,
        "banheiros": int(baths) if baths else None,
        "vagas": int(parking) if parking else None,
        "quintal": has_any(desc or "", ["quintal", "área externa", "area externa"]),
        "armarios": has_any(desc or "", ["armário", "armarios", "armários", "planejada"]),
        "churrasqueira": has_any(desc or "", ["churrasqueira", "área gourmet", "area gourmet"]),
        "piscina": has_any(desc or "", ["piscina"]),
        "hidromassagem": has_any(desc or "", ["hidromassagem", "hidro"]),
        "descricao": desc,
    })
    return row


def parse_nova_somar(text: str, seed: Dict) -> Dict:
    row = base(seed)
    price = first(r"R\$\s*([\d\.]+,\d{2})", text)
    area = first(r"([\d\.,]+)\s*m²", text)
    rooms = first(r"(\d+)\s*quarto\(s\)", text)
    baths = first(r"(\d+)\s*banheiro\(s\)", text)
    parking = first(r"(\d+)\s*Vaga\(s\)", text)
    location = clean_location(first(r"([A-Za-zÀ-ÿ\s]+),\s*Divinopolis\s*-\s*MG", text))
    desc = first(r"Descricao do imóvel\s*(.*?)\s*(?:Características internas|Cód\. imóvel|Valor)", text)
    title = first(r"(Casa para aluguel[^\n]*)", text) or "Casa para aluguel"
    row.update({
        "titulo": title,
        "tipo": "casa",
        "bairro": location,
        "aluguel": money_to_float(price) if price else None,
        "areaM2": money_to_float(area) if area else None,
        "quartos": int(rooms) if rooms else None,
        "banheiros": int(baths) if baths else None,
        "vagas": int(parking) if parking else None,
        "quintal": has_any(desc or "", ["quintal", "área externa", "area externa"]),
        "armarios": has_any(desc or "", ["armário", "armarios", "armários", "planejada"]),
        "churrasqueira": has_any(desc or "", ["churrasqueira", "área gourmet", "area gourmet"]),
        "piscina": has_any(desc or "", ["piscina"]),
        "hidromassagem": has_any(desc or "", ["hidromassagem", "hidro"]),
        "descricao": desc,
    })
    return row


def parser_for(source: str):
    return {"Casa Nova": parse_casa_nova, "Nova Somar": parse_nova_somar}.get(source)


def main() -> None:
    started = now_iso()
    seeds = json.loads((DATA / "coleta-seeds.json").read_text(encoding="utf-8"))["urls"]
    rows: List[Dict] = []
    errors: List[Dict] = []
    source_status: Dict[str, Dict] = {}

    for seed in seeds:
        source = seed["fonte"]
        source_status.setdefault(source, {"tentativas": 0, "sucessos": 0, "erros": 0})
        source_status[source]["tentativas"] += 1
        parser = parser_for(source)
        if parser is None:
            errors.append({"fonte": source, "url": seed["url"], "erro": "parser não implementado"})
            source_status[source]["erros"] += 1
            continue
        try:
            text = fetch_text(seed["url"])
            row = parser(text, seed)
            if row.get("aluguel") is None and row.get("quartos") is None and row.get("areaM2") is None:
                raise ValueError("página acessível, mas sem campos mínimos reconhecidos")
            rows.append(row)
            source_status[source]["sucessos"] += 1
        except Exception as exc:
            errors.append({"fonte": source, "url": seed["url"], "erro": f"{type(exc).__name__}: {exc}"})
            source_status[source]["erros"] += 1
        time.sleep(0.5)

    finished = now_iso()
    OUT.write_text(
        json.dumps({"schemaVersion": 1, "coletadoEm": finished, "imoveis": rows, "erros": errors}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    status = {
        "schemaVersion": 1,
        "inicio": started,
        "fim": finished,
        "estado": "ok" if rows and not errors else ("parcial" if rows else "indisponivel"),
        "coletados": len(rows),
        "erros": len(errors),
        "fontes": source_status,
    }
    STATUS.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Coletados: {len(rows)} | erros: {len(errors)} | estado: {status['estado']}")
    if not rows:
        print("Aviso: fontes externas indisponíveis nesta execução; inventário anterior será preservado.")


if __name__ == "__main__":
    main()
