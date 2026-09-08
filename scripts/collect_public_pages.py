from __future__ import annotations

import html
import json
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = DATA / "coleta-atual.json"
UA = "Mozilla/5.0 (compatible; NossaProximaCasa/1.0; +https://github.com/renatovalerio88/nossa-proxima-casa)"


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: List[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.parts.append(text)


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "pt-BR,pt;q=0.9"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        body = resp.read().decode(charset, errors="replace")
    parser = TextExtractor()
    parser.feed(body)
    return html.unescape("\n".join(parser.parts))


def money_to_float(raw: str) -> float:
    return float(raw.replace(".", "").replace(",", "."))


def first(pattern: str, text: str, flags: int = re.I | re.S) -> Optional[str]:
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None


def has_any(text: str, terms: List[str]) -> Optional[bool]:
    low = text.lower()
    if any(term in low for term in terms):
        return True
    return None


def parse_casa_nova(text: str, seed: Dict) -> Dict:
    price = first(r"Valor do aluguel:\s*R\$\s*([\d\.]+,\d{2})", text)
    rooms = first(r"(\d+)\s*Quarto\(s\)", text)
    baths = first(r"(\d+)\s*Banhos?\(s\)", text)
    parking = first(r"(\d+)\s*Vagas?\(s\)", text)
    area = first(r"([\d\.,]+)\s*m²", text)
    location = first(r"([A-Za-zÀ-ÿ\s]+)\s*·\s*Divinopolis", text)
    desc = first(r"Descrição\s*(.*?)\s*(?:iframe|Fale com nossos consultores|Os preços)", text)
    title = first(r"#?\s*(Casa\s+Aluguel)", text) or "Casa Aluguel"
    return {
        "fonte": seed["fonte"], "codigoFonte": seed["codigoFonte"], "url": seed["url"],
        "titulo": title, "tipo": "casa", "cidade": "Divinópolis", "bairro": location,
        "endereco": None, "latitude": None, "longitude": None,
        "aluguel": money_to_float(price) if price else None,
        "areaM2": money_to_float(area) if area else None,
        "quartos": int(rooms) if rooms else None, "banheiros": int(baths) if baths else None,
        "vagas": int(parking) if parking else None,
        "quintal": has_any((desc or ""), ["quintal", "área externa", "area externa"]),
        "armarios": has_any((desc or ""), ["armário", "armarios", "armários", "planejada"]),
        "churrasqueira": has_any((desc or ""), ["churrasqueira", "área gourmet", "area gourmet"]),
        "piscina": has_any((desc or ""), ["piscina"]),
        "hidromassagem": has_any((desc or ""), ["hidromassagem", "hidro"]),
        "descricao": desc,
        "fotos": [], "publicadoEm": None, "hospital": {}, "comercio": {}, "avaliacaoVisual": {},
        "disponivel": True,
    }


def parse_nova_somar(text: str, seed: Dict) -> Dict:
    price = first(r"R\$\s*([\d\.]+,\d{2})", text)
    area = first(r"([\d\.,]+)\s*m²", text)
    rooms = first(r"(\d+)\s*quarto\(s\)", text)
    baths = first(r"(\d+)\s*banheiro\(s\)", text)
    parking = first(r"(\d+)\s*Vaga\(s\)", text)
    location = first(r"([A-Za-zÀ-ÿ\s]+),\s*Divinopolis\s*-\s*MG", text)
    desc = first(r"Descricao do imóvel\s*(.*?)\s*(?:Características internas|Cód\. imóvel|Valor)", text)
    title = first(r"(Casa para aluguel[^\n]*)", text) or "Casa para aluguel"
    low_desc = (desc or "").lower()
    return {
        "fonte": seed["fonte"], "codigoFonte": seed["codigoFonte"], "url": seed["url"],
        "titulo": title, "tipo": "casa", "cidade": "Divinópolis", "bairro": location,
        "endereco": None, "latitude": None, "longitude": None,
        "aluguel": money_to_float(price) if price else None,
        "areaM2": money_to_float(area) if area else None,
        "quartos": int(rooms) if rooms else None, "banheiros": int(baths) if baths else None,
        "vagas": int(parking) if parking else None,
        "quintal": has_any(low_desc, ["quintal", "área externa", "area externa"]),
        "armarios": has_any(low_desc, ["armário", "armarios", "armários", "planejada"]),
        "churrasqueira": has_any(low_desc, ["churrasqueira", "área gourmet", "area gourmet"]),
        "piscina": has_any(low_desc, ["piscina"]),
        "hidromassagem": has_any(low_desc, ["hidromassagem", "hidro"]),
        "descricao": desc,
        "fotos": [], "publicadoEm": None, "hospital": {}, "comercio": {}, "avaliacaoVisual": {},
        "disponivel": True,
    }


def main() -> None:
    seeds = json.loads((DATA / "coleta-seeds.json").read_text(encoding="utf-8"))["urls"]
    rows = []
    errors = []
    for seed in seeds:
        try:
            text = fetch_text(seed["url"])
            if seed["fonte"] == "Casa Nova":
                rows.append(parse_casa_nova(text, seed))
            elif seed["fonte"] == "Nova Somar":
                rows.append(parse_nova_somar(text, seed))
            else:
                errors.append({"url": seed["url"], "erro": "parser não implementado"})
        except Exception as exc:
            errors.append({"url": seed["url"], "erro": str(exc)})
    OUT.write_text(json.dumps({"schemaVersion": 1, "imoveis": rows, "erros": errors}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Coletados: {len(rows)} | erros: {len(errors)}")
    if not rows:
        raise SystemExit("Nenhum imóvel pôde ser coletado")


if __name__ == "__main__":
    main()
