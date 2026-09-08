from __future__ import annotations

import argparse
from pathlib import Path

from core import DATA_DIR, calculate_match, eligibility, load_json, merge_inventory, save_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Normaliza e atualiza o inventário de imóveis")
    parser.add_argument("--input", required=True, help="JSON com lista em 'imoveis'")
    parser.add_argument("--today", default=None, help="Data ISO opcional para reprodutibilidade")
    args = parser.parse_args()

    cfg = load_json(DATA_DIR / "config.json")
    inventory_path = DATA_DIR / "imoveis.json"
    existing = load_json(inventory_path)
    incoming_doc = load_json(Path(args.input))
    incoming = incoming_doc.get("imoveis", incoming_doc if isinstance(incoming_doc, list) else [])

    # Uma pane/bloqueio de todas as fontes não significa que todos os imóveis
    # anteriores ficaram indisponíveis. Só inferimos indisponibilidade quando
    # houve uma coleta válida com ao menos um item observado.
    if not incoming:
        print("Coleta sem imóveis válidos: inventário anterior preservado sem alterar disponibilidade.")
        return

    processed = []
    for item in incoming:
        row = dict(item)
        row["elegibilidade"] = eligibility(row, cfg)
        row["match"] = calculate_match(row, cfg)
        processed.append(row)

    merged = merge_inventory(existing, processed, today=args.today)
    save_json(inventory_path, merged)
    print(f"Inventário atualizado: {len(merged['imoveis'])} imóveis")


if __name__ == "__main__":
    main()
