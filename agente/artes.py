"""Gerador de artes para o Instagram da Pronto Vendi (Pillow, sem serviços externos).

Identidade: fundo preto, verde neon, branco, logo da marca e fonte Montserrat.
Dica: escreva *palavra* entre asteriscos no título para pintá-la de verde.

Modelos:
- veiculo:  foto do carro + nome, ficha (ano, km...), preço e selo opcional de VENDIDO
- destaque: título grande, subtítulo e botão de chamada (CTA)
- oferta:   selo grande com número/benefício (ex. "40 min", "0% de taxa")
- lista:    dicas/passos numerados
- citacao:  depoimento ou frase com aspas
"""

from __future__ import annotations

import io
import re
import time
import unicodedata
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from .config import PASTA_SAIDA, RAIZ, Config

FORMATOS = {"retrato": (1080, 1350), "quadrado": (1080, 1080), "story": (1080, 1920)}
MODELOS = ("veiculo", "destaque", "oferta", "lista", "citacao")

PASTA_FONTES = RAIZ / "fontes"
PASTA_FOTOS = RAIZ / "fotos"
LOGO = RAIZ / "marca" / "logo.png"

_FONTES = {
    "titulo": ["Titulo.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf"],
    "bold": ["Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "medio": ["Medio.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
    "regular": ["Regular.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
}


def _fonte(tamanho: int, estilo: str = "bold") -> ImageFont.FreeTypeFont:
    for nome in _FONTES[estilo]:
        caminho = PASTA_FONTES / nome if "/" not in nome else Path(nome)
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


# ------------------------------------------------------------------ fundo
def _fundo(tam, base, verde) -> Image.Image:
    w, h = tam
    img = Image.new("RGB", tam, base)
    brilho = Image.new("L", tam, 0)
    d = ImageDraw.Draw(brilho)
    d.ellipse([w * 0.35, h * 0.72, w * 1.45, h * 1.25], fill=120)
    d.ellipse([-w * 0.5, -h * 0.25, w * 0.45, h * 0.2], fill=55)
    brilho = brilho.filter(ImageFilter.GaussianBlur(160))
    img = Image.composite(Image.new("RGB", tam, _mistura(base, verde, 0.5)), img, brilho)
    # linhas de velocidade
    d = ImageDraw.Draw(img)
    for i, (y, comp) in enumerate([(0.86, 0.55), (0.885, 0.38), (0.905, 0.22)]):
        d.line([(w - w * comp, h * y), (w, h * y - 30)], fill=_mistura(base, verde, 0.55 - i * 0.12), width=4)
    return img


def _colar_logo(img: Image.Image, largura: int, x: int, y: int, centralizar=False) -> int:
    """Cola a logo e devolve a altura usada."""
    if not LOGO.exists():
        return 0
    logo = Image.open(LOGO).convert("RGBA")
    alt = int(logo.height * largura / logo.width)
    logo = logo.resize((largura, alt), Image.LANCZOS)
    if centralizar:
        x = (img.width - largura) // 2
    img.paste(logo, (x, y), logo)
    return alt


# --------------------------------------------- texto com *destaque* verde
def _palavras(texto: str) -> list[tuple[str, bool]]:
    saida, verde = [], False
    for parte in re.split(r"(\*)", texto):
        if parte == "*":
            verde = not verde
            continue
        saida += [(p, verde) for p in parte.split()]
    return saida


def _quebrar(d, texto, fonte, largura) -> list[list[tuple[str, bool]]]:
    linhas: list[list[tuple[str, bool]]] = []
    for paragrafo in texto.split("\n"):
        atual: list[tuple[str, bool]] = []
        for pal in _palavras(paragrafo):
            teste = " ".join(p for p, _ in atual + [pal])
            if d.textlength(teste, font=fonte) <= largura or not atual:
                atual.append(pal)
            else:
                linhas.append(atual)
                atual = [pal]
        linhas.append(atual)
    return linhas


def _largura_linha(d, linha, fonte) -> float:
    return d.textlength(" ".join(p for p, _ in linha), font=fonte)


def _ajustar(d, texto, caixa, tam_max, tam_min=26, estilo="titulo", entrelinha=1.12):
    largura, altura = caixa
    for tam in range(tam_max, tam_min - 1, -3):
        f = _fonte(tam, estilo)
        linhas = _quebrar(d, texto, f, largura)
        if len(linhas) * tam * entrelinha <= altura and all(
            _largura_linha(d, l, f) <= largura for l in linhas
        ):
            return f, linhas, tam
    f = _fonte(tam_min, estilo)
    return f, _quebrar(d, texto, f, largura), tam_min


def _escrever(d, linhas, fonte, tam, x, y, cor, verde, alinhar="esquerda", largura=0, entrelinha=1.12):
    espaco = d.textlength(" ", font=fonte)
    for linha in linhas:
        lx = x
        if alinhar == "centro":
            lx = x + (largura - _largura_linha(d, linha, fonte)) / 2
        for palavra, eh_verde in linha:
            d.text((lx, y), palavra, font=fonte, fill=verde if eh_verde else cor)
            lx += d.textlength(palavra, font=fonte) + espaco
        y += int(tam * entrelinha)
    return y


def _botao(d, texto, x, y, verde, cor_txt, tam=40, centralizar_em=0) -> int:
    f = _fonte(tam, "bold")
    lt = d.textlength(texto, font=f)
    larg, alt = lt + 2 * tam * 1.3, tam * 2.4
    if centralizar_em:
        x = (centralizar_em - larg) / 2
    d.rounded_rectangle([x, y, x + larg, y + alt], radius=alt / 2, fill=verde)
    d.text((x + tam * 1.3, y + alt / 2), texto, font=f, fill=cor_txt, anchor="lm")
    return int(alt)


def _estrelas(d, x, y, n, tam, cor):
    import math
    for i in range(n):
        cx, cy = x + tam / 2 + i * tam * 1.2, y + tam / 2
        pts = []
        for k in range(10):
            r = tam / 2 if k % 2 == 0 else tam / 5
            ang = math.pi / 2 + k * math.pi / 5
            pts.append((cx + r * math.cos(ang), cy - r * math.sin(ang)))
        d.polygon(pts, fill=cor)


def _rodape(d, w, h, arroba, verde, txt):
    f = _fonte(30, "bold")
    texto = arroba
    lt = d.textlength(texto, font=f)
    y = h - 70
    d.text(((w - lt) / 2, y), texto, font=f, fill=txt, anchor="la")
    d.line([((w - lt) / 2 - 90, y + 18), ((w - lt) / 2 - 25, y + 18)], fill=verde, width=4)
    d.line([((w + lt) / 2 + 25, y + 18), ((w + lt) / 2 + 90, y + 18)], fill=verde, width=4)


# ------------------------------------------------------------------- foto
def _abrir_foto(foto: str) -> Image.Image:
    if foto.startswith(("http://", "https://")):
        r = requests.get(foto, timeout=30)
        r.raise_for_status()
        return Image.open(io.BytesIO(r.content)).convert("RGB")
    caminho = (PASTA_FOTOS / Path(foto).name).resolve()
    if caminho.parent != PASTA_FOTOS.resolve() or not caminho.exists():
        raise FileNotFoundError(f"Foto {foto} não encontrada na pasta fotos/")
    return ImageOps.exif_transpose(Image.open(caminho)).convert("RGB")


def _foto_com_degrade(foto: Image.Image, larg, alt) -> tuple[Image.Image, Image.Image]:
    foto = ImageOps.fit(foto, (larg, alt), Image.LANCZOS, centering=(0.5, 0.55))
    mascara = Image.new("L", (larg, alt), 255)
    d = ImageDraw.Draw(mascara)
    inicio = int(alt * 0.62)
    for y in range(inicio, alt):
        d.line([(0, y), (larg, y)], fill=int(255 * (1 - (y - inicio) / (alt - inicio)) ** 1.6))
    return foto, mascara


def _carimbo_vendido(img: Image.Image, verde):
    w, h = img.size
    camada = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(camada)
    f = _fonte(150, "titulo")
    texto = "VENDIDO"
    lt = d.textlength(texto, font=f)
    cx, cy = w / 2, h * 0.3
    d.rounded_rectangle([cx - lt / 2 - 50, cy - 110, cx + lt / 2 + 50, cy + 110], radius=24,
                        fill=verde + (235,))
    d.text((cx, cy), texto, font=f, fill=(10, 10, 10, 255), anchor="mm")
    camada = camada.rotate(-12, resample=Image.BICUBIC, center=(cx, cy))
    img.paste(camada, (0, 0), camada)


# ---------------------------------------------------------------- principal
def criar_arte(
    cfg: Config,
    modelo: str,
    titulo: str,
    subtitulo: str = "",
    cta: str = "",
    itens: list[str] | None = None,
    destaque: str = "",
    formato: str = "retrato",
    foto: str = "",
    vendido: bool = False,
    estrelas: int = 0,
) -> Path:
    if modelo not in MODELOS:
        raise ValueError(f"Modelo inválido: {modelo}. Use um de {MODELOS}")
    if modelo == "veiculo" and not foto:
        raise ValueError("O modelo 'veiculo' precisa de uma foto (arquivo em fotos/ ou URL).")
    w, h = FORMATOS.get(formato, FORMATOS["retrato"])
    verde, base, txt = _hex(cfg.cor_primaria), _hex(cfg.cor_secundaria), _hex(cfg.cor_texto)
    cinza = _mistura(txt, base, 0.3)
    margem = 80
    larg = w - 2 * margem
    limite_inferior = h - 130  # acima do rodapé

    img = _fundo((w, h), base, verde)
    d = ImageDraw.Draw(img)

    if modelo == "veiculo":
        alt_foto = int(h * (0.62 if formato != "story" else 0.58))
        foto_img, mascara = _foto_com_degrade(_abrir_foto(foto), w, alt_foto)
        img.paste(foto_img, (0, 0), mascara)
        d = ImageDraw.Draw(img)
        _colar_logo(img, 300, margem - 20, 40)
        if vendido:
            _carimbo_vendido(img, verde)
            d = ImageDraw.Draw(img)
        y = alt_foto - 70
        f, linhas, tam = _ajustar(d, titulo, (larg, 170), 84)
        y = _escrever(d, linhas, f, tam, margem, y, txt, verde)
        if subtitulo:
            fs, ls, ts = _ajustar(d, subtitulo, (larg, 60), 38, estilo="medio")
            y = _escrever(d, ls, fs, ts, margem, y + 4, cinza, verde)
        if itens:
            y += 18
            fc, x = _fonte(30, "bold"), margem
            for item in itens[:4]:
                lt = d.textlength(item, font=fc)
                if x + lt + 50 > w - margem:
                    break
                d.rounded_rectangle([x, y, x + lt + 44, y + 60], radius=30, outline=verde, width=3)
                d.text((x + 22, y + 30), item, font=fc, fill=txt, anchor="lm")
                x += lt + 64
            y += 60
        if destaque or cta:
            alt_linha = 100
            y = max(y + 30, limite_inferior - alt_linha - 40)
            if destaque:
                fp, _, tp = _ajustar(d, destaque, (larg * 0.55, alt_linha), 76, estilo="titulo")
                d.text((margem, y + alt_linha / 2), destaque, font=fp, fill=verde, anchor="lm")
            if cta:
                fb = _fonte(34, "bold")
                lb = d.textlength(cta, font=fb) + 2 * 44
                _botao(d, cta, w - margem - lb, y + (alt_linha - 82) / 2, verde, base, 34)

    elif modelo == "destaque":
        y = 70 + _colar_logo(img, 340, 0, 70, centralizar=True) + 110
        f, linhas, tam = _ajustar(d, titulo, (larg, int(h * 0.36)), 120)
        y = _escrever(d, linhas, f, tam, margem, y, txt, verde)
        if subtitulo:
            d.line([(margem, y + 25), (margem + 120, y + 25)], fill=verde, width=6)
            f, linhas, tam = _ajustar(d, subtitulo, (larg, int(h * 0.2)), 50, estilo="medio", entrelinha=1.3)
            _escrever(d, linhas, f, tam, margem, y + 60, cinza, verde, entrelinha=1.3)
        if cta:
            _botao(d, cta, margem, limite_inferior - 150, verde, base)

    elif modelo == "oferta":
        y = 70 + _colar_logo(img, 340, 0, 70, centralizar=True) + 90
        f, linhas, tam = _ajustar(d, titulo, (larg, int(h * 0.18)), 80)
        y = _escrever(d, linhas, f, tam, margem, y, txt, verde, "centro", larg) + 30
        selo = destaque or "OFERTA"
        f, linhas, tam = _ajustar(d, selo, (larg - 60, int(h * 0.2)), 230, 60)
        alt_selo = int(len(linhas) * tam * 1.05) + 70
        d.rounded_rectangle([margem, y, w - margem, y + alt_selo], radius=36, fill=verde)
        _escrever(d, linhas, f, tam, margem + 30, y + 30, base, base, "centro", larg - 60, 1.05)
        y += alt_selo + 40
        if subtitulo:
            f, linhas, tam = _ajustar(d, subtitulo, (larg, int(h * 0.14)), 46, estilo="medio", entrelinha=1.3)
            _escrever(d, linhas, f, tam, margem, y, txt, verde, "centro", larg, 1.3)
        if cta:
            _botao(d, cta, 0, limite_inferior - 150, verde, base, centralizar_em=w)

    elif modelo == "lista":
        y = 60 + _colar_logo(img, 280, margem, 60) + 70
        f, linhas, tam = _ajustar(d, titulo, (larg, int(h * 0.2)), 86)
        y = _escrever(d, linhas, f, tam, margem, y, txt, verde) + 30
        itens = (itens or [])[:6]
        fim = limite_inferior - (160 if cta else 20)
        espaco = (fim - y) // max(len(itens), 1)
        for i, item in enumerate(itens, 1):
            r = 34
            d.ellipse([margem, y, margem + 2 * r, y + 2 * r], fill=verde)
            d.text((margem + r, y + r), str(i), font=_fonte(36, "titulo"), fill=base, anchor="mm")
            fi, li, ti = _ajustar(d, item, (larg - 110, espaco - 16), 44, 24, estilo="medio")
            _escrever(d, li, fi, ti, margem + 105, y + 10, txt, verde)
            y += espaco
        if cta:
            _botao(d, cta, margem, limite_inferior - 130, verde, base)

    elif modelo == "citacao":
        _colar_logo(img, 280, margem, 60)
        y = int(h * 0.15)
        d.text((margem - 10, y), "“", font=_fonte(300, "titulo"), fill=verde)
        y += 210
        fim = limite_inferior - (190 if cta else 40) - (70 if subtitulo else 0) - (70 if estrelas else 0)
        f, linhas, tam = _ajustar(d, titulo, (larg, fim - y), 78, estilo="bold", entrelinha=1.25)
        y = _escrever(d, linhas, f, tam, margem, y, txt, verde, entrelinha=1.25)
        if subtitulo:
            d.text((margem, y + 25), f"— {subtitulo}", font=_fonte(40, "medio"), fill=verde)
            y += 70
        if estrelas:
            _estrelas(d, margem, y + 25, min(estrelas, 5), 44, verde)
        if cta:
            _botao(d, cta, margem, limite_inferior - 150, verde, base)

    _rodape(d, w, h, cfg.instagram_arroba, verde, txt)

    sem_acento = unicodedata.normalize("NFKD", titulo.replace("*", "")).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", sem_acento.lower())[:40].strip("-") or "arte"
    caminho = PASTA_SAIDA / f"{time.strftime('%Y%m%d-%H%M%S')}-{modelo}-{slug}.jpg"
    n = 2
    while caminho.exists():
        caminho = caminho.with_name(f"{caminho.stem.rsplit('_', 1)[0]}_{n}.jpg")
        n += 1
    img.save(caminho, "JPEG", quality=93)  # Instagram aceita apenas JPEG
    return caminho
