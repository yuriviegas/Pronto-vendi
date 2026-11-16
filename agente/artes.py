"""Gerador de artes para o Instagram (Pillow, sem serviços externos).

Modelos disponíveis:
- destaque: título grande, subtítulo e botão de chamada (CTA)
- oferta:   selo com preço/desconto em destaque
- lista:    dicas/passos numerados
- citacao:  frase com aspas grandes
"""

from __future__ import annotations

import re
import time
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .config import PASTA_SAIDA, Config

FORMATOS = {"retrato": (1080, 1350), "quadrado": (1080, 1080), "story": (1080, 1920)}
MODELOS = ("destaque", "oferta", "lista", "citacao")

_FONTES_BOLD = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]
_FONTES_REG = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/Library/Fonts/Arial.ttf",
    "C:/Windows/Fonts/arial.ttf",
]
PASTA_FONTES = Path(__file__).resolve().parent.parent / "fontes"


def _fonte(tamanho: int, negrito: bool = True) -> ImageFont.FreeTypeFont:
    # Fontes próprias da marca: coloque Bold.ttf / Regular.ttf em ./fontes
    proprias = PASTA_FONTES / ("Bold.ttf" if negrito else "Regular.ttf")
    for caminho in [proprias, *(_FONTES_BOLD if negrito else _FONTES_REG)]:
        try:
            return ImageFont.truetype(str(caminho), tamanho)
        except OSError:
            continue
    return ImageFont.load_default(size=tamanho)


def _hex(cor: str) -> tuple[int, int, int]:
    cor = cor.lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}", cor):
        return (0, 0, 0)
    return tuple(int(cor[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _mistura(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _gradiente(tam, c1, c2) -> Image.Image:
    w, h = tam
    img = Image.new("RGB", tam)
    d = ImageDraw.Draw(img)
    for y in range(h):
        d.line([(0, y), (w, y)], fill=_mistura(c1, c2, y / h))
    return img


def _quebrar(d: ImageDraw.ImageDraw, texto: str, fonte, largura: int) -> list[str]:
    linhas: list[str] = []
    for paragrafo in texto.split("\n"):
        atual = ""
        for palavra in paragrafo.split():
            teste = f"{atual} {palavra}".strip()
            if d.textlength(teste, font=fonte) <= largura:
                atual = teste
            else:
                if atual:
                    linhas.append(atual)
                atual = palavra
        linhas.append(atual)
    return linhas


def _texto_ajustado(d, texto, caixa, tam_max, tam_min=28, negrito=True, entrelinha=1.15):
    """Escolhe o maior tamanho de fonte que cabe na caixa (largura, altura)."""
    largura, altura = caixa
    for tam in range(tam_max, tam_min - 1, -4):
        f = _fonte(tam, negrito)
        linhas = _quebrar(d, texto, f, largura)
        alt = int(len(linhas) * tam * entrelinha)
        if alt <= altura and all(d.textlength(l, font=f) <= largura for l in linhas):
            return f, linhas, tam
    f = _fonte(tam_min, negrito)
    return f, _quebrar(d, texto, f, largura), tam_min


def _escrever(d, linhas, fonte, tam, x, y, cor, alinhar="esquerda", largura=0, entrelinha=1.15):
    for linha in linhas:
        lx = x
        if alinhar == "centro":
            lx = x + (largura - d.textlength(linha, font=fonte)) / 2
        d.text((lx, y), linha, font=fonte, fill=cor)
        y += int(tam * entrelinha)
    return y


def _rodape(d, w, h, marca, cor, margem):
    f = _fonte(30, True)
    d.text((margem, h - margem - 30), marca.upper(), font=f, fill=cor)
    d.line([(margem, h - margem - 50), (margem + 80, h - margem - 50)], fill=cor, width=5)


def criar_arte(
    cfg: Config,
    modelo: str,
    titulo: str,
    subtitulo: str = "",
    cta: str = "",
    itens: list[str] | None = None,
    destaque: str = "",
    formato: str = "retrato",
    cor_fundo: str = "",
    cor_destaque: str = "",
) -> Path:
    if modelo not in MODELOS:
        raise ValueError(f"Modelo inválido: {modelo}. Use um de {MODELOS}")
    w, h = FORMATOS.get(formato, FORMATOS["retrato"])
    prim = _hex(cor_destaque or cfg.cor_primaria)
    sec = _hex(cor_fundo or cfg.cor_secundaria)
    txt = _hex(cfg.cor_texto)
    margem = 90
    larg_util = w - 2 * margem

    img = _gradiente((w, h), sec, _mistura(sec, prim, 0.35))
    d = ImageDraw.Draw(img)
    # Elementos decorativos
    d.ellipse([w - 260, -300, w + 240, 200], fill=_mistura(sec, prim, 0.45))
    d.rectangle([0, 0, 18, h], fill=prim)

    y = margem + 60
    if modelo == "destaque":
        f, linhas, tam = _texto_ajustado(d, titulo, (larg_util, int(h * 0.38)), 120)
        y = _escrever(d, linhas, f, tam, margem, y, txt)
        if subtitulo:
            y += 30
            f, linhas, tam = _texto_ajustado(d, subtitulo, (larg_util, int(h * 0.22)), 54, negrito=False)
            y = _escrever(d, linhas, f, tam, margem, y, _mistura(txt, sec, 0.15))

    elif modelo == "oferta":
        f, linhas, tam = _texto_ajustado(d, titulo, (larg_util, int(h * 0.22)), 96)
        y = _escrever(d, linhas, f, tam, margem, y, txt)
        selo = destaque or "OFERTA"
        y += 50
        f, linhas, tam = _texto_ajustado(d, selo, (larg_util - 80, int(h * 0.22)), 170, 60)
        alt_selo = int(len(linhas) * tam * 1.1) + 80
        d.rounded_rectangle([margem, y, w - margem, y + alt_selo], radius=40, fill=prim)
        _escrever(d, linhas, f, tam, margem + 40, y + 40, txt, "centro", larg_util - 80, 1.1)
        y += alt_selo + 40
        if subtitulo:
            f, linhas, tam = _texto_ajustado(d, subtitulo, (larg_util, int(h * 0.15)), 48, negrito=False)
            y = _escrever(d, linhas, f, tam, margem, y, txt)

    elif modelo == "lista":
        f, linhas, tam = _texto_ajustado(d, titulo, (larg_util, int(h * 0.2)), 90)
        y = _escrever(d, linhas, f, tam, margem, y, txt) + 40
        itens = (itens or [])[:6]
        espaco = (h - y - margem - 220) // max(len(itens), 1)
        for i, item in enumerate(itens, 1):
            raio = 34
            d.ellipse([margem, y, margem + 2 * raio, y + 2 * raio], fill=prim)
            fn = _fonte(38, True)
            n = str(i)
            d.text((margem + raio - d.textlength(n, font=fn) / 2, y + 12), n, font=fn, fill=txt)
            fi, li, ti = _texto_ajustado(d, item, (larg_util - 110, espaco - 20), 46, 26, negrito=False)
            _escrever(d, li, fi, ti, margem + 110, y + 8, txt)
            y += espaco

    elif modelo == "citacao":
        d.text((margem - 10, y - 60), "“", font=_fonte(320, True), fill=prim)
        y += 200
        f, linhas, tam = _texto_ajustado(d, titulo, (larg_util, int(h * 0.42)), 92)
        y = _escrever(d, linhas, f, tam, margem, y, txt)
        if subtitulo:
            y += 30
            d.text((margem, y), f"— {subtitulo}", font=_fonte(42, False), fill=prim)

    if cta:
        fc = _fonte(44, True)
        lc = d.textlength(cta, font=fc)
        bx, by = margem, h - margem - 200
        d.rounded_rectangle([bx, by, bx + lc + 100, by + 100], radius=50, fill=prim)
        d.text((bx + 50, by + 26), cta, font=fc, fill=txt)

    _rodape(d, w, h, cfg.marca_nome, txt, margem)

    sem_acento = unicodedata.normalize("NFKD", titulo).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", sem_acento.lower())[:40].strip("-") or "arte"
    caminho = PASTA_SAIDA / f"{time.strftime('%Y%m%d-%H%M%S')}-{slug}.jpg"
    img.save(caminho, "JPEG", quality=92)  # Instagram aceita apenas JPEG
    return caminho
