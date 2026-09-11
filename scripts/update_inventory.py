from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

from core import DATA_DIR, calculate_match, eligibility, load_json, merge_inventory, reapply_rules, save_json


def limpar_distancia_nao_validada(item: Dict[str, Any]) -> Dict[str, Any]:
    """Impede distância antiga/não validada de alimentar Match ou oportunidade.

    O enriquecimento geográfico roda depois desta etapa e pode preencher novamente
    as distâncias, mas somente após validar a localização em Divinópolis. Até lá,
    localização desconhecida permanece realmente desconhecida.
    """
    row = deepcopy(item)
    hospital = row.get("hospital")
    if not isinstance(hospital, dict):
        return row
    if hospital.get("localizacaoValidada") is True:
        return row

    hospital = deepcopy(hospital)
    for campo in (
        "distanciaKm",
        "distanciaLinhaRetaKm",
        "precisaoLocalizacao",
        "fonteDistancia",
    ):
        hospital[campo] = None
    hospital["localizacaoValidada"] = False
    row["hospital"] = hospital
    return row


def limpar_documento_localizacao(documento: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(documento)
    out["imoveis"] = [limpar_distancia_nao_validada(i) for i in out.get("imoveis", [])]
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Normaliza e atualiza o inventário de imóveis")
    parser.add_argument("--input", required=True, help="JSON com lista em 'imoveis'")
    parser.add_argument("--today", default=None, help="Data ISO opcional para reprodutibilidade")
    args = parser.parse_args()

    cfg = load_json(DATA_DIR / "config.json")
    inventory_path = DATA_DIR / "imoveis.json"
    existing = limpar_documento_localizacao(load_json(inventory_path))
    incoming_doc = load_json(Path(args.input))
    incoming_raw = incoming_doc.get("imoveis", incoming_doc if isinstance(incoming_doc, list) else [])
    incoming = [limpar_distancia_nao_validada(item) for item in incoming_raw]

    # Mesmo quando a coleta do dia não traz imóveis válidos, reaplicamos as
    # regras atuais ao inventário já conhecido. Isso corrige classificações
    # legadas sem inventar disponibilidade, preço ou qualquer dado de origem.
    if not incoming:
        refreshed = reapply_rules(existing, cfg)
        save_json(inventory_path, refreshed)
        print("Coleta sem imóveis válidos: disponibilidade preservada e regras atuais reaplicadas.")
        return

    processed = []
    for item in incoming:
        row = dict(item)
        row["elegibilidade"] = eligibility(row, cfg)
        row["match"] = calculate_match(row, cfg)
        processed.append(row)

    merged = merge_inventory(existing, processed, today=args.today)
    # A fusão pode preservar campos antigos quando a coleta nova vem com null.
    # Reaplicamos a barreira para impedir que uma distância histórica sem
    # validação geográfica volte a ser usada na classificação.
    merged = limpar_documento_localizacao(merged)
    merged = reapply_rules(merged, cfg)
    save_json(inventory_path, merged)
    print(f"Inventário atualizado e reclassificado: {len(merged['imoveis'])} imóveis")


if __name__ == "__main__":
    main()
