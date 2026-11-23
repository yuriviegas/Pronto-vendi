"""Identidade visual compartilhada por Reels e stories (Pillow puro, roda no GitHub Actions).

Convenção de texto: *palavra* entre asteriscos sai em verde.
"""

from __future__ import annotations

import random
import re

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from .config import RAIZ

W, H = 1080, 1920
FPS = 30
M = 96
FUNDO = (7, 9, 12)
VERDE = (143, 232, 58)
BRANCO = (255, 255, 255)
CINZA = (139, 148, 158)
SUAVE = (201, 208, 216)
APOIO = (170, 178, 188)
VERMELHO = (255, 92, 92)

PASTA_FONTES = RAIZ / "fontes"
_ARQ = {"titulo": "Titulo.ttf", "bold": "Bold.ttf", "medio": "Medio.ttf", "regular": "Regular.ttf"}
_cache: dict = {}


def fonte(estilo: str, tamanho: int) -> ImageFont.FreeTypeFont:
    chave = (estilo, tamanho)
    if chave not in _cache:
        _cache[chave] = ImageFont.truetype(str(PASTA_FONTES / _ARQ[estilo]), tamanho)
    return _cache[chave]


def limpo(texto: str) -> str:
    return texto.replace("*", "")


def ajustar(textos: list[str], estilo: str, largura: int, inicio: int) -> ImageFont.FreeTypeFont:
    """Maior fonte (até `inicio`) em que a linha mais longa cabe em `largura`."""
    t = inicio
    while t > 20 and max(fonte(estilo, t).getlength(limpo(x)) for x in textos) > largura:
        t -= 2
    return fonte(estilo, t)


def quebrar(texto: str, f: ImageFont.FreeTypeFont, largura: int) -> list[str]:
    linhas, atual = [], ""
    for palavra in texto.split():
        teste = (atual + " " + palavra).strip()
        if f.getlength(limpo(teste)) <= largura or not atual:
            atual = teste
        else:
            linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    # fecha/reabre o destaque quando ele atravessa a quebra de linha
    saida, aberto = [], False
    for ln in linhas:
        if aberto:
            ln = "*" + ln
        if ln.count("*") % 2 == 1:
            ln += "*"
            aberto = True
        else:
            aberto = False
        saida.append(ln)
    return saida


def texto_rico(d: ImageDraw.ImageDraw, xy, texto: str, f, cor=BRANCO, destaque=VERDE, espaco: float = 0):
    """Desenha texto em que trechos *assim* saem na cor de destaque."""
    x, y = xy
    for i, parte in enumerate(re.split(r"\*", texto)):
        if not parte:
            continue
        c = destaque if i % 2 == 1 else cor
        if espaco:
            for ch in parte:
                d.text((x, y), ch, font=f, fill=c)
                x += f.getlength(ch) + espaco
        else:
            d.text((x, y), parte, font=f, fill=c)
            x += f.getlength(parte)
    return x


def espacado(d, xy, texto, f, cor, espaco):
    texto_rico(d, xy, texto, f, cor, cor, espaco)


def largura_espacada(texto, f, espaco):
    return sum(f.getlength(c) + espaco for c in texto) - espaco


def ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def camada() -> Image.Image:
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def por(base: Image.Image, lay: Image.Image, alfa: float = 1.0, dx: float = 0, dy: float = 0, escala: float = 1.0):
    if alfa <= 0.004:
        return
    if escala != 1.0:
        nw, nh = int(W * escala), int(H * escala)
        grande = lay.resize((nw, nh), Image.BILINEAR)
        lay = camada()
        lay.paste(grande, ((W - nw) // 2, (H - nh) // 2))
    if alfa < 1:
        lay = lay.copy()
        lay.putalpha(lay.getchannel("A").point(lambda v: int(v * alfa)))
    base.paste(lay, (int(dx), int(dy)), lay)


def brilho(lay: Image.Image, raio: int = 40) -> Image.Image:
    return lay.filter(ImageFilter.GaussianBlur(raio))


def clarao(img: Image.Image, t0: float, t: float, cor, forca: float = 0.8, dur: float = 0.4):
    if t0 <= t < t0 + dur:
        a = forca * (1 - (t - t0) / dur) ** 2
        ov = Image.new("RGBA", (W, H), tuple(cor) + (int(255 * a),))
        img.paste(ov, (0, 0), ov)


_rnd = random.Random(11)
_ESTRELAS = [(_rnd.randint(0, W), _rnd.randint(0, H), _rnd.choice([2, 2, 3]), _rnd.randint(50, 120), _rnd.uniform(6, 22))
             for _ in range(40)]


def fundo(t: float = 0.0, altura: int = H) -> Image.Image:
    img = Image.new("RGB", (W, altura), FUNDO)
    d = ImageDraw.Draw(img, "RGBA")
    for x, y, r, a, v in _ESTRELAS:
        yy = (y * altura / H - t * v) % altura
        d.ellipse((x - r, yy - r, x + r, yy + r), fill=(255, 255, 255, a))
    return img


_logo_cache: dict = {}


def logo(largura: int) -> Image.Image:
    """Logo oficial com o fundo preto removido, cortada nas bordas."""
    if largura not in _logo_cache:
        png = RAIZ / "marca" / "logo.png"
        src = Image.open(png).convert("RGBA")
        if src.getchannel("A").getextrema()[0] == 255:  # sem transparência: remove o preto
            rgb = src.convert("RGB")
            mx = ImageChops.lighter(ImageChops.lighter(rgb.getchannel("R"), rgb.getchannel("G")), rgb.getchannel("B"))
            src.putalpha(mx.point(lambda v: max(0, min(255, int((v - 28) * 255 / 50)))))
        caixa = src.getchannel("A").point(lambda v: 255 if v > 20 else 0).getbbox()
        if caixa:
            src = src.crop(caixa)
        alt = int(src.height * largura / src.width)
        _logo_cache[largura] = src.resize((largura, alt), Image.LANCZOS)
    return _logo_cache[largura]
