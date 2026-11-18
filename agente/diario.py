"""Rotina diária: gera e publica o conteúdo do dia a partir de conteudo/calendario.json.

Horários (Brasília):
  bom_dia        08:30  story de imagem
  reel_meio_dia  12:00  Reel
  story_tarde    14:00  story de imagem
  reel_tarde     17:30  Reel

Uso:
  python -m agente.diario bom_dia                 # gera e publica o de hoje
  python -m agente.diario reel_tarde --simular    # só gera, não publica
  python -m agente.diario todos --data 2026-11-20 --simular
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from . import stories
from .config import PASTA_SAIDA, RAIZ, carregar

CALENDARIO = RAIZ / "conteudo" / "calendario.json"
FUSO = ZoneInfo("America/Sao_Paulo")
SLOTS = ["bom_dia", "reel_meio_dia", "story_tarde", "reel_tarde"]
DIAS_SEMANA = ["SEGUNDA-FEIRA", "TERÇA-FEIRA", "QUARTA-FEIRA", "QUINTA-FEIRA", "SEXTA-FEIRA", "SÁBADO", "DOMINGO"]


def _resumo(texto: str) -> None:
    print(texto)
    arq = os.getenv("GITHUB_STEP_SUMMARY")
    if arq:
        with open(arq, "a", encoding="utf-8") as f:
            f.write(texto + "\n")


def carregar_dia(dia: date) -> dict:
    dados = json.loads(CALENDARIO.read_text(encoding="utf-8"))
    dias = dados["dias"]
    chave = dia.isoformat()
    restantes = sorted(d for d in dias if d >= chave)
    if len(restantes) <= 5:
        _resumo(f"⚠️ Só restam {len(restantes)} dia(s) de conteúdo no calendário. Peça mais ao Claude.")
    if chave not in dias:
        raise SystemExit(f"Não há conteúdo para {chave} em conteudo/calendario.json. Peça mais dias ao Claude.")
    return dias[chave]


def gerar(slot: str, spec: dict, dia: date, pasta: Path) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / slot
    if slot.startswith("reel"):
        from .reels import Reel

        return Reel(spec).renderizar(destino.with_suffix(".mp4"), pasta / "tmp")
    spec = dict(spec)
    spec.setdefault("topo", DIAS_SEMANA[dia.weekday()])
    return stories.gerar(spec, destino)


def publicar(slot: str, arquivo: Path, spec: dict) -> dict:
    from .hospedagem import url_publica
    from .instagram import Instagram

    cfg = carregar()
    ig = Instagram(cfg.instagram_token, cfg.instagram_api_base, cfg.instagram_user_id)
    if slot.startswith("reel"):
        return ig.publicar_video(str(arquivo), spec.get("legenda", ""), "REELS")
    return ig.publicar_story_imagem(url_publica(arquivo, cfg))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Publicação diária do Instagram da Pronto Vendi")
    ap.add_argument("slot", choices=SLOTS + ["todos"])
    ap.add_argument("--data", help="AAAA-MM-DD (padrão: hoje, horário de Brasília)")
    ap.add_argument("--simular", action="store_true", help="gera os arquivos mas não publica")
    args = ap.parse_args(argv)

    dia = date.fromisoformat(args.data) if args.data else datetime.now(FUSO).date()
    conteudo = carregar_dia(dia)
    slots = SLOTS if args.slot == "todos" else [args.slot]
    pasta = PASTA_SAIDA / dia.isoformat()
    falhou = False
    for slot in slots:
        spec = conteudo.get(slot)
        if not spec:
            _resumo(f"- {slot}: sem conteúdo para {dia}, pulando.")
            continue
        arquivo = gerar(slot, spec, dia, pasta)
        _resumo(f"- {slot}: gerado `{arquivo.relative_to(RAIZ)}`")
        if args.simular:
            continue
        try:
            r = publicar(slot, arquivo, spec)
            _resumo(f"  ✅ publicado: {r.get('permalink') or r.get('media_id')}")
        except Exception as e:  # noqa: BLE001
            falhou = True
            _resumo(f"  ❌ falha ao publicar: {e}")
    return 1 if falhou else 0


if __name__ == "__main__":
    sys.exit(main())
