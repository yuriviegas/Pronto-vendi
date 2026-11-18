"""Stories estáticos (1080x1920) na identidade da Pronto Vendi.

Modelos:
- saudacao: {"modelo": "saudacao", "topo": "QUARTA-FEIRA", "titulo": "Bom dia, *Porto Alegre.*", "texto": "..."}
- pergunta: {"modelo": "pergunta", "topo": "CONTA PRA GENTE", "titulo": "Qual foi a *pior proposta*...?",
             "cta": "RESPONDE NO DIRECT"}

As figurinhas interativas (enquete, quiz) não podem ser colocadas pela API,
por isso a chamada para ação vai escrita na própria arte.
"""

from __future__ import annotations

from pathlib import Path

from PIL import ImageDraw

from .estilo import (BRANCO, H, M, SUAVE, VERDE, W, ajustar, espacado, fonte, fundo, logo, quebrar, texto_rico)

TOPO, BASE = 300, 380


def _titulo(d, titulo: str, y: int, tamanho: int, linhas_max: int = 4) -> int:
    t = tamanho
    while True:
        f = fonte("titulo", t)
        linhas = quebrar(titulo, f, W - 2 * M)
        if len(linhas) <= linhas_max or t <= 60:
            break
        t -= 6
    for ln in linhas:
        texto_rico(d, (M, y), ln.upper() if titulo.isupper() else ln, f)
        y += int(f.size * 1.05)
    return y


def gerar(spec: dict, destino: Path) -> Path:
    img = fundo(0.0)
    d = ImageDraw.Draw(img)
    espacado(d, (M, TOPO), spec.get("topo", "EM BREVE").upper(), fonte("bold", 30), VERDE, 12)
    lg = logo(500)
    y_logo = H - BASE - lg.height
    modelo = spec.get("modelo", "saudacao")

    # mede o bloco central para centralizar entre o topo e a logo
    def bloco(desenhar: bool, y0: int) -> int:
        dd = d if desenhar else ImageDraw.Draw(fundo(0.0))
        y = y0
        if desenhar:
            dd.rectangle((M, y, M + 120, y + 6), fill=VERDE)
        y += 54
        tam = 150 if modelo == "saudacao" else 104
        y = _titulo(dd, spec["titulo"].upper(), y, tam)
        if spec.get("texto"):
            y += 36
            ft = fonte("medio", 46)
            for ln in quebrar(spec["texto"], ft, W - 2 * M):
                texto_rico(dd, (M, y), ln, ft, SUAVE)
                y += 60
        if modelo == "pergunta":
            y += 70
            cta = spec.get("cta", "RESPONDE NO DIRECT").upper()
            fc = fonte("bold", 40)
            w = fc.getlength(cta) + 120
            dd.rounded_rectangle((M, y, M + w, y + 110), 55, outline=VERDE, width=5)
            dd.text((M + 48, y + 30), cta, font=fc, fill=VERDE)
            # seta para baixo
            ax = M + w - 50
            dd.polygon([(ax - 14, y + 46), (ax + 14, y + 46), (ax, y + 66)], fill=VERDE)
            y += 110
        return y

    altura = bloco(False, 0)
    inicio = TOPO + 80 + max(0, ((y_logo - 80) - (TOPO + 80) - altura) // 2)
    bloco(True, inicio)
    img.paste(lg, (M - 8, y_logo), lg)
    destino = destino.with_suffix(".jpg")
    img.save(destino, "JPEG", quality=92)
    return destino
