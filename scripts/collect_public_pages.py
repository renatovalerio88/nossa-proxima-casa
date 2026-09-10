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
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = DATA / "coleta-atual.json"
STATUS = DATA / "status-coleta.json"
UA = "Mozilla/5.0 (compatible; NossaProximaCasa/1.0; +https://github.com/renatovalerio88/nossa-proxima-casa)"
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".avif")
GENERIC_IMAGE_TOKENS = (
    "logo", "favicon", "sprite", "avatar", "placeholder", "default-image",
    "default_image", "sem-foto", "sem_foto", "no-image", "no_image", "banner",
)


class ListingUnavailable(RuntimeError):
    """Anúncio confirmado como removido (HTTP 404/410)."""


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: List[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.parts.append(text)


class PhotoMetadataExtractor(HTMLParser):
    """Extrai somente imagens declaradas como mídia principal/social do próprio anúncio."""

    def __init__(self) -> None:
        super().__init__()
        self.urls: List[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() != "meta":
            return
        data = {str(k).lower(): str(v or "") for k, v in attrs}
        key = (data.get("property") or data.get("name") or "").lower()
        if key in {"og:image", "og:image:url", "twitter:image", "twitter:image:src"}:
            candidate = data.get("content")
            if candidate:
                self.urls.append(candidate)


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
        curl, "--fail", "--location", "--silent", "--show-error", "--compressed",
        "--http1.1", "--ipv4", "--connect-timeout", "10", "--max-time", "35",
        "--retry", "2", "--retry-delay", "2", "--retry-connrefused", "--user-agent", UA,
        "--header", "Accept-Language: pt-BR,pt;q=0.9,en;q=0.5",
        "--header", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=50, check=False)
    if result.returncode != 0:
        detail = (result.stderr or "curl falhou").strip().replace("\n", " ")
        raise RuntimeError(f"curl exit {result.returncode}: {detail[:350]}")
    if not result.stdout.strip():
        raise RuntimeError("curl retornou resposta vazia")
    return result.stdout


def fetch_html(url: str) -> str:
    errors: List[str] = []
    try:
        return fetch_with_urllib(url)
    except urllib.error.HTTPError as exc:
        if exc.code in {404, 410}:
            raise ListingUnavailable(f"HTTP {exc.code}") from exc
        errors.append(f"urllib=HTTPError: {exc}")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        errors.append(f"urllib={type(exc).__name__}: {exc}")
    try:
        return fetch_with_curl(url)
    except (RuntimeError, subprocess.TimeoutExpired, OSError) as exc:
        errors.append(f"curl={type(exc).__name__}: {exc}")
    raise RuntimeError(" | ".join(errors))


def fetch_text(url: str) -> str:
    """Compatibilidade: devolve texto visível, preservando fetch_html para extração de mídia."""
    return extract_text(fetch_html(url))


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


def _valid_real_photo_url(raw: object, page_url: str) -> Optional[str]:
    if not isinstance(raw, str) or not raw.strip():
        return None
    url = html.unescape(urljoin(page_url, raw.strip())).replace("\\/", "/")
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        return None
    low = url.lower()
    if any(token in low for token in GENERIC_IMAGE_TOKENS):
        return None
    path = parsed.path.lower()
    if not path.endswith(IMAGE_EXTENSIONS) and not any(ext in low for ext in IMAGE_EXTENSIONS):
        return None
    return url


def _json_ld_images(document: object) -> List[str]:
    found: List[str] = []
    if isinstance(document, dict):
        for key, value in document.items():
            if key.lower() in {"image", "images", "photo", "photos"}:
                if isinstance(value, str):
                    found.append(value)
                elif isinstance(value, list):
                    found.extend(x for x in value if isinstance(x, str))
                elif isinstance(value, dict):
                    for candidate_key in ("url", "contentUrl"):
                        candidate = value.get(candidate_key)
                        if isinstance(candidate, str):
                            found.append(candidate)
            if isinstance(value, (dict, list)):
                found.extend(_json_ld_images(value))
    elif isinstance(document, list):
        for item in document:
            found.extend(_json_ld_images(item))
    return found


def extract_real_photos(body: str, page_url: str, limit: int = 20) -> List[str]:
    """Extrai fotos explicitamente publicadas pelo anúncio; nunca cria/substitui imagens ausentes."""
    candidates: List[str] = []
    meta = PhotoMetadataExtractor()
    try:
        meta.feed(body)
        candidates.extend(meta.urls)
    except Exception:
        pass

    for match in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', body, re.I | re.S):
        try:
            payload = json.loads(html.unescape(match.group(1)).strip())
            candidates.extend(_json_ld_images(payload))
        except (json.JSONDecodeError, TypeError):
            continue

    result: List[str] = []
    seen = set()
    for candidate in candidates:
        url = _valid_real_photo_url(candidate, page_url)
        if not url or url in seen:
            continue
        seen.add(url)
        result.append(url)
        if len(result) >= limit:
            break
    return result


def base(seed: Dict) -> Dict:
    return {
        "fonte": seed["fonte"], "codigoFonte": seed["codigoFonte"], "url": seed["url"],
        "cidade": "Divinópolis", "endereco": None, "latitude": None, "longitude": None,
        "fotos": [], "publicadoEm": None, "hospital": {}, "comercio": {}, "avaliacaoVisual": {},
        "disponivel": True,
    }


def tombstone(seed: Dict) -> Dict:
    row = base(seed)
    row["disponivel"] = False
    return row


def parse_casa_nova(text: str, seed: Dict) -> Dict:
    row = base(seed)
    price = first(r"Valor do aluguel:\s*R\$\s*([\d\.]+,\d{2})", text)
    rooms = first(r"(\d+)\s*Quarto\(s\)", text)
    baths = first(r"(\d+)\s*Banhos?\(s\)", text)
    parking = first(r"(\d+)\s*Vagas?\(s\)", text)
    area = first(r"([\d\.,]+)\s*m²", text)
    location = clean_location(first(r"([A-Za-zÀ-ÿ\s]+)\s*·\s*Divinopolis", text))
    desc = first(r"Descrição\s*(.*?)\s*(?:iframe|Fale com nossos consultores|Fale com nossos corretores|Os preços)", text)
    title = first(r"#?\s*(Casa\s+Aluguel)", text) or first(r"(Casa\s+para\s+aluguel[^\n]*)", text)
    row.update({
        "titulo": title, "tipo": "casa" if title else None, "bairro": location,
        "aluguel": money_to_float(price) if price else None, "areaM2": money_to_float(area) if area else None,
        "quartos": int(rooms) if rooms else None, "banheiros": int(baths) if baths else None,
        "vagas": int(parking) if parking else None,
        "quintal": has_any(desc or "", ["quintal", "área externa", "area externa"]),
        "armarios": has_any(desc or "", ["armário", "armarios", "armários", "planejada"]),
        "churrasqueira": has_any(desc or "", ["churrasqueira", "área gourmet", "area gourmet"]),
        "piscina": has_any(desc or "", ["piscina"]),
        "hidromassagem": has_any(desc or "", ["hidromassagem", "hidro"]), "descricao": desc,
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
    title = first(r"(Casa para aluguel[^\n]*)", text)
    row.update({
        "titulo": title, "tipo": "casa" if title else None, "bairro": location,
        "aluguel": money_to_float(price) if price else None, "areaM2": money_to_float(area) if area else None,
        "quartos": int(rooms) if rooms else None, "banheiros": int(baths) if baths else None,
        "vagas": int(parking) if parking else None,
        "quintal": has_any(desc or "", ["quintal", "área externa", "area externa"]),
        "armarios": has_any(desc or "", ["armário", "armarios", "armários", "planejada"]),
        "churrasqueira": has_any(desc or "", ["churrasqueira", "área gourmet", "area gourmet"]),
        "piscina": has_any(desc or "", ["piscina"]),
        "hidromassagem": has_any(desc or "", ["hidromassagem", "hidro"]), "descricao": desc,
    })
    return row


def validate_row(row: Dict) -> None:
    if row.get("tipo") != "casa":
        raise ValueError("página não confirmou que o anúncio é uma casa para aluguel")
    if not row.get("descricao"):
        raise ValueError("página acessível, mas descrição do imóvel não foi reconhecida")
    recognized = sum(row.get(field) is not None for field in ("aluguel", "quartos", "areaM2"))
    if recognized < 2:
        raise ValueError("página acessível, mas campos essenciais vieram incompletos")


def parser_for(source: str):
    return {"Casa Nova": parse_casa_nova, "Nova Somar": parse_nova_somar}.get(source)


def collect_seed(seed: Dict) -> Tuple[Dict, int]:
    page_url = seed["url"]
    body = fetch_html(page_url)
    text = extract_text(body)
    parser = parser_for(seed["fonte"])
    if parser is None:
        raise ValueError("parser não implementado")
    row = parser(text, seed)
    validate_row(row)
    photos = extract_real_photos(body, page_url)
    row["fotos"] = photos
    if photos:
        row["fotoUrl"] = photos[0]
    return row, len(photos)


def main() -> None:
    started = now_iso()
    seeds = json.loads((DATA / "coleta-seeds.json").read_text(encoding="utf-8"))["urls"]
    rows: List[Dict] = []
    errors: List[Dict] = []
    unavailable_events: List[Dict] = []
    source_status: Dict[str, Dict] = {}
    unavailable = 0
    photos_collected = 0
    listings_with_photos = 0

    for seed in seeds:
        source = seed["fonte"]
        source_status.setdefault(source, {"tentativas": 0, "sucessos": 0, "indisponiveis": 0, "erros": 0, "comFotos": 0})
        source_status[source]["tentativas"] += 1
        if parser_for(source) is None:
            errors.append({"fonte": source, "url": seed["url"], "erro": "parser não implementado"})
            source_status[source]["erros"] += 1
            continue
        try:
            row, photo_count = collect_seed(seed)
            rows.append(row)
            source_status[source]["sucessos"] += 1
            if photo_count:
                source_status[source]["comFotos"] += 1
                listings_with_photos += 1
                photos_collected += photo_count
        except ListingUnavailable as exc:
            rows.append(tombstone(seed))
            unavailable += 1
            source_status[source]["indisponiveis"] += 1
            unavailable_events.append({"fonte": source, "url": seed["url"], "motivo": f"anúncio indisponível confirmado: {exc}"})
        except Exception as exc:
            errors.append({"fonte": source, "url": seed["url"], "erro": f"{type(exc).__name__}: {exc}"})
            source_status[source]["erros"] += 1
        time.sleep(0.5)

    finished = now_iso()
    valid_count = sum(1 for row in rows if row.get("disponivel") is not False)
    OUT.write_text(json.dumps({
        "schemaVersion": 2,
        "coletadoEm": finished,
        "imoveis": rows,
        "erros": errors,
        "indisponiveisConfirmados": unavailable_events,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    status = {
        "schemaVersion": 2,
        "inicio": started,
        "fim": finished,
        "estado": "ok" if valid_count and not errors else ("parcial" if valid_count or unavailable else "indisponivel"),
        "coletados": valid_count,
        "indisponiveisConfirmados": unavailable,
        "erros": len(errors),
        "avisos": len(unavailable_events),
        "imoveisComFotos": listings_with_photos,
        "fotosReaisCapturadas": photos_collected,
        "fontes": source_status,
    }
    STATUS.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Coletados válidos: {valid_count} | com fotos reais: {listings_with_photos} | fotos: {photos_collected} | "
        f"indisponíveis confirmados: {unavailable} | erros técnicos: {len(errors)} | estado: {status['estado']}"
    )
    if not valid_count:
        print("Aviso: nenhuma observação válida nova; inventário anterior será preservado, salvo tombstones confirmados.")


if __name__ == "__main__":
    main()
