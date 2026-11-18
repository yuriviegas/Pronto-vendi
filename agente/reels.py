"""Gerador de Reels (1080x1920, 30 fps) a partir de um roteiro em JSON.

Roteiro:
{
  "cenas": [
    {"tipo": "frases", "linhas": ["E SE AS LOJAS", "*DISPUTASSEM*", "O SEU CARRO?"]},
    {"tipo": "frases", "linhas": ["CURIOSO", "QUE SOME."], "riscar": true},
    {"tipo": "gancho_numero", "numero": "3", "linhas": ["ERROS QUE", "*PERDEM DINHEIRO*"]},
    {"tipo": "item", "numero": "01", "titulo": ["ANUNCIAR", "NO CHUTE."], "texto": "..."},
    {"tipo": "mito", "frase": "“Meu carro vale a Fipe.”", "verdade": false, "texto": "..."},
    {"tipo": "disputa", "lances": [["Lojista 1", 52000], ["Investidor 1", 53500]]}
  ]
}
Todo Reel termina com o slogan e a logo + "Novidades em breve".
"""

from __future__ import annotations

import math
import random
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

from . import trilha
from .estilo import (APOIO, BRANCO, CINZA, FPS, FUNDO, H, M, SUAVE, VERDE, VERMELHO, W, ajustar, brilho, camada,
                     clarao, ease, espacado, fonte, fundo, largura_espacada, limpo, logo, por, quebrar, texto_rico)

TOPO_Y = 330
SLOGAN_DUR, MARCA_DUR = 2.4, 4.0


def _etiqueta() -> Image.Image:
    lay = camada()
    d = ImageDraw.Draw(lay)
    f = fonte("bold", 30)
    espacado(d, (M, TOPO_Y), "EM BREVE", f, VERDE, 12)
    espacado(d, (W - M - largura_espacada("POA · RS", f, 12), TOPO_Y), "POA · RS", f, APOIO, 12)
    return lay


ETIQUETA = None


class Cena:
    dur = 3.0
    eventos: list = []  # (tempo_local, tipo) para a trilha

    def desenhar(self, img, t, out):
        raise NotImplementedError


class Frases(Cena):
    def __init__(self, linhas, dur=None, riscar=False, sub=None, tamanho=210):
        self.dur = dur or (2.6 if not riscar else 1.6)
        self.riscar = riscar
        self.eventos = [(0.0, "batida")] if riscar else []
        f = ajustar(linhas, "titulo", W - 2 * M, tamanho)
        alt = int(f.size * 1.05)
        total = alt * len(linhas) + (90 if sub else 0)
        y0 = 980 - total // 2
        self.linhas = []
        for i, ln in enumerate(linhas):
            normal, cinza = camada(), camada()
            y = y0 + i * alt
            texto_rico(ImageDraw.Draw(normal), (M, y), ln, f)
            texto_rico(ImageDraw.Draw(cinza), (M, y), limpo(ln), f, CINZA, CINZA)
            bb = f.getbbox(limpo(ln))
            self.linhas.append((normal, cinza, y + (bb[1] + bb[3]) // 2, f.getlength(limpo(ln)), "*" in ln))
        self.brilhos = [brilho(n) if destaque else None for n, _, _, _, destaque in self.linhas]
        self.sub = None
        if sub:
            self.sub = camada()
            fs = fonte("medio", 44)
            yy = y0 + alt * len(linhas) + 40
            for ln in quebrar(sub, fs, W - 2 * M):
                texto_rico(ImageDraw.Draw(self.sub), (M, yy), ln, fs, SUAVE)
                yy += 60

    def desenhar(self, img, t, out):
        rnd = random.Random(int(t * 1000))
        for i, (normal, cinza, my, w, _) in enumerate(self.linhas):
            atraso = 0.0 if self.riscar else i * 0.3
            a = ease((t - atraso) / 0.28)
            if a <= 0:
                continue
            if self.riscar:
                treme = max(0.0, 1 - t / 0.22)
                dx, dy = rnd.uniform(-16, 16) * treme, rnd.uniform(-10, 10) * treme
                cinz = ease((t - 0.75) / 0.25)
                por(img, normal, (1 - cinz) * out, dx, dy, 1.0 + 0.08 * (1 - ease(t / 0.22)))
                if cinz > 0:
                    por(img, cinza, cinz * out)
                    p = ease((t - 0.75 - i * 0.08) / 0.25)
                    lay = camada()
                    ImageDraw.Draw(lay).rectangle((M - 10, my - 7, M - 10 + (w + 20) * p, my + 7), fill=VERDE)
                    por(img, lay, out)
            else:
                if self.brilhos[i] is not None:
                    por(img, self.brilhos[i], (0.5 + 0.2 * math.cos(t * 4 * math.pi)) * a * out)
                por(img, normal, a * out, escala=1.0 + 0.12 * (1 - a))
        if self.sub is not None:
            b = ease((t - 0.3 * len(self.linhas)) / 0.35)
            por(img, self.sub, b * out, dy=(1 - b) * 30)
        if self.riscar:
            clarao(img, 0, t, BRANCO, 0.22, 0.2)


class GanchoNumero(Cena):
    def __init__(self, numero, linhas, dur=2.6):
        self.dur = dur
        self.num = camada()
        ImageDraw.Draw(self.num).text((M - 10, 380), numero, font=fonte("titulo", 460), fill=VERDE)
        self.num_b = brilho(self.num, 50)
        self.txt = camada()
        f = ajustar(linhas, "titulo", W - 2 * M, 130)
        for i, ln in enumerate(linhas):
            texto_rico(ImageDraw.Draw(self.txt), (M, 940 + i * int(f.size * 1.1)), ln, f)

    def desenhar(self, img, t, out):
        por(img, self.num_b, (0.55 + 0.2 * math.cos(t * 4 * math.pi)) * out)
        por(img, self.num, out, escala=1.0 + 0.15 * (1 - ease(t / 0.3)))
        a = ease((t - 0.35) / 0.35)
        por(img, self.txt, a * out, dy=(1 - a) * 60)
        clarao(img, 0, t, BRANCO, 0.6, 0.35)


class Item(Cena):
    def __init__(self, numero, titulo, texto, dur=3.6, tam_titulo=None):
        self.dur = dur
        self.n = camada()
        ImageDraw.Draw(self.n).text((M - 6, 400), numero, font=fonte("titulo", 260), fill=VERDE)
        self.nb = brilho(self.n, 40)
        f = tam_titulo or ajustar(titulo, "titulo", W - 2 * M, 140)
        self.t = camada()
        d = ImageDraw.Draw(self.t)
        y = 740
        for ln in titulo:
            texto_rico(d, (M, y), ln, f)
            y += int(f.size * 1.06)
        by = y + 50
        d.rectangle((M, by, M + 120, by + 7), fill=VERDE)
        self.b = camada()
        fb = fonte("medio", 48)
        yy = by + 60
        for ln in quebrar(texto, fb, W - 2 * M):
            texto_rico(ImageDraw.Draw(self.b), (M, yy), ln, fb, SUAVE)
            yy += 66
        self.eventos = []

    def desenhar(self, img, t, out):
        por(img, self.nb, 0.5 * ease(t / 0.3) * out)
        por(img, self.n, out, dx=(1 - ease(t / 0.3)) * -120)
        a = ease((t - 0.2) / 0.3)
        por(img, self.t, a * out, dy=(1 - a) * 60)
        b = ease((t - 0.6) / 0.4)
        por(img, self.b, b * out, dy=(1 - b) * 30)
        clarao(img, 0, t, VERDE, 0.3, 0.3)


class Mito(Cena):
    def __init__(self, frase, verdade, texto, indice="", dur=3.9):
        self.dur = dur
        self.verdade = bool(verdade)
        self.eventos = [(1.4, "ok" if self.verdade else "erro")]
        f = fonte("titulo", 88)
        self.cl = camada()
        d = ImageDraw.Draw(self.cl)
        if indice:
            espacado(d, (M, 470), indice, fonte("bold", 30), VERDE, 8)
        y = 560
        for ln in quebrar(frase, f, W - 2 * M):
            texto_rico(d, (M, y), ln, f)
            y += 106
        rot = "VERDADE" if self.verdade else "MITO"
        cor = VERDE if self.verdade else VERMELHO
        fs = fonte("titulo", 120)
        w = fs.getlength(rot)
        cx, cy = W / 2, y + 150
        st = camada()
        sd = ImageDraw.Draw(st)
        sd.rounded_rectangle((cx - w / 2 - 50, cy - 90, cx + w / 2 + 50, cy + 90), 26, outline=cor, width=12)
        sd.text((cx - w / 2, cy - 72), rot, font=fs, fill=cor)
        self.st = st.rotate(-7, center=(cx, cy), resample=Image.BICUBIC)
        self.sb = brilho(self.st, 36)
        self.cor = cor
        self.ex = camada()
        d = ImageDraw.Draw(self.ex)
        yy = cy + 170
        d.rectangle((M, yy, M + 120, yy + 7), fill=VERDE)
        yy += 50
        fe = fonte("medio", 46)
        for ln in quebrar(texto, fe, W - 2 * M):
            texto_rico(d, (M, yy), ln, fe, SUAVE)
            yy += 64

    def desenhar(self, img, t, out):
        a = ease(t / 0.3)
        por(img, self.cl, a * out, dy=(1 - a) * 50)
        if t >= 1.4:
            s = ease((t - 1.4) / 0.2)
            por(img, self.sb, 0.5 * s * out)
            por(img, self.st, s * out, escala=1.0 + 0.6 * (1 - s))
            clarao(img, 1.4, t, self.cor, 0.3, 0.3)
        b = ease((t - 1.9) / 0.35)
        por(img, self.ex, b * out, dy=(1 - b) * 30)


def _brl(v):
    return "R$ " + f"{int(round(v)):,}".replace(",", ".")


class Disputa(Cena):
    PX0, PY0, PX1, PY1 = M - 20, 430, W - M + 20, 1600

    def __init__(self, lances, dur=None, selo="VENDIDO!"):
        self.lances = [(0.5 + i * 0.8, nome, valor) for i, (nome, valor) in enumerate(lances)]
        self.t_selo = self.lances[-1][0] + 1.1
        self.dur = dur or self.t_selo + 1.6
        self.selo = selo
        self.eventos = [(tl, "lance") for tl, _, _ in self.lances] + [(self.t_selo, "batida")]
        maior = _brl(max(v for _, _, v in self.lances))
        self.f_preco = ajustar([maior], "titulo", W - 2 * M - 60, 170)

    def desenhar(self, img, t, out):
        a = ease(t / 0.35)
        lay = camada()
        d = ImageDraw.Draw(lay)
        x0, y0, x1, y1 = self.PX0, self.PY0, self.PX1, self.PY1
        d.rounded_rectangle((x0, y0, x1, y1), 36, fill=(17, 22, 28, 255), outline=(38, 46, 56, 255), width=3)
        espacado(d, (M + 20, y0 + 50), "SEU CARRO · OFERTAS AO VIVO", fonte("bold", 30), APOIO, 6)
        pisca = 0.5 + 0.5 * math.cos(t * 2 * math.pi * 1.5)
        d.ellipse((x1 - 70, y0 + 56, x1 - 46, y0 + 80), fill=VERDE + (int(120 + 135 * pisca),))
        feitos = [l for l in self.lances if l[0] <= t]
        if feitos:
            tb, _, v = feitos[-1]
            ant = feitos[-2][2] if len(feitos) > 1 else None
            atual = v if ant is None else ant + (v - ant) * ease((t - tb) / 0.35)
        else:
            atual = None
        espacado(d, (M + 20, y0 + 150), "MAIOR OFERTA", fonte("bold", 30), VERDE, 6)
        d.text((M + 14, y0 + 200), _brl(atual) if atual else "R$ —", font=self.f_preco, fill=BRANCO)
        d.line((x0 + 40, y0 + 430, x1 - 40, y0 + 430), fill=(38, 46, 56), width=3)
        linhas = list(reversed(feitos))[:4]
        fr, fv = fonte("bold", 44), fonte("titulo", 46)
        for i, (tb, nome, v) in enumerate(linhas):
            entra = ease((t - tb) / 0.3) if i == 0 else 1.0
            desce = 0 if i == 0 else -(1 - ease((t - linhas[0][0]) / 0.3)) * 120
            y = y0 + 470 + i * 120 - (1 - entra) * 40 + desce
            alfa = int(255 * entra)
            topo = i == 0
            d.text((M + 20, y), nome, font=fr, fill=(255, 255, 255, int(alfa * (1 if topo else 0.55))))
            vt = _brl(v)
            d.text((x1 - 40 - fv.getlength(vt), y - 2), vt, font=fv,
                   fill=VERDE + (alfa,) if topo else (255, 255, 255, int(alfa * 0.55)))
        d.text((M + 20, y1 - 60), "Exemplo ilustrativo", font=fonte("regular", 24), fill=(107, 116, 128, 255))
        por(img, lay, a * out, dy=(1 - a) * 60)
        for tb, _, _ in self.lances:
            clarao(img, tb, t, VERDE, 0.12, 0.25)
        if t >= self.t_selo:
            s = ease((t - self.t_selo) / 0.25)
            st = camada()
            sd = ImageDraw.Draw(st)
            f = fonte("titulo", 110)
            w = f.getlength(self.selo)
            cx, cy = W / 2, y0 + 800
            sd.rounded_rectangle((cx - w / 2 - 50, cy - 90, cx + w / 2 + 50, cy + 90), 24, fill=VERDE + (255,))
            sd.text((cx - w / 2, cy - 68), self.selo, font=f, fill=FUNDO)
            st = st.rotate(-6, center=(cx, cy), resample=Image.BICUBIC)
            por(img, brilho(st, 40), 0.6 * s * out)
            por(img, st, s * out, escala=1.0 + 0.5 * (1 - s))
            clarao(img, self.t_selo, t, BRANCO, 0.6, 0.35)


class Slogan(Cena):
    dur = SLOGAN_DUR

    def __init__(self):
        f = ajustar(["NEGOCIAÇÃO."], "titulo", W - 2 * M, 200)
        self.camadas = []
        alt = int(f.size * 1.04)
        for i, (ln, cor) in enumerate([("MENOS", BRANCO), ("ENROLAÇÃO.", BRANCO), ("MAIS", VERDE), ("NEGOCIAÇÃO.", VERDE)]):
            lay = camada()
            ImageDraw.Draw(lay).text((M, 600 + i * alt + (50 if i >= 2 else 0)), ln, font=f, fill=cor)
            self.camadas.append(lay)
        self.b = brilho(self.camadas[3])
        self.barra_y = 600 + 2 * alt + 18

    def desenhar(self, img, t, out):
        for i, lay in enumerate(self.camadas):
            a = ease((t - i * 0.3) / 0.3)
            if i == 3 and a > 0:
                por(img, self.b, (0.5 + 0.2 * math.cos(t * 4 * math.pi)) * a * out)
            por(img, lay, a * out, escala=1.0 + 0.10 * (1 - a))
        a = ease((t - 0.6) / 0.3)
        barra = camada()
        ImageDraw.Draw(barra).rectangle((M, self.barra_y, M + 140 * a, self.barra_y + 8), fill=VERDE)
        por(img, barra, out)
        clarao(img, 0, t, BRANCO, 0.7, 0.4)


class Marca(Cena):
    dur = MARCA_DUR

    def __init__(self, linha1="NOVIDADES", linha2="EM BREVE", rodape="PORTO ALEGRE · FIQUE LIGADO"):
        lg = logo(W - 2 * 40)
        self.logo = camada()
        self.logo.paste(lg, (40, 640), lg)
        self.lb = brilho(self.logo, 50)
        self.ny = 640 + lg.height + 130
        f = fonte("bold", 58)
        self.n1, self.n2, self.rod = camada(), camada(), camada()
        espacado(ImageDraw.Draw(self.n1), (M, self.ny), linha1, f, BRANCO, 16)
        espacado(ImageDraw.Draw(self.n2), (M, self.ny + 92), linha2, f, VERDE, 16)
        espacado(ImageDraw.Draw(self.rod), (M, self.ny + 290), rodape, fonte("bold", 30), APOIO, 10)

    def desenhar(self, img, t, out):
        por(img, self.lb, (0.35 + 0.2 * math.cos(t * 4 * math.pi)) * ease(t / 0.3))
        por(img, self.logo, ease(t / 0.3), escala=1.0 + 0.08 * (1 - ease(t / 0.3)))
        a1 = ease((t - 1.0) / 0.4)
        if a1 > 0:
            ImageDraw.Draw(img).rectangle((M, self.ny - 56, M + 140 * a1, self.ny - 48), fill=VERDE)
            por(img, self.n1, a1, dy=(1 - a1) * 40)
        a2 = ease((t - 1.5) / 0.4)
        por(img, self.n2, a2, dy=(1 - a2) * 40)
        por(img, self.rod, ease((t - 2.5) / 0.5))
        clarao(img, 0, t, VERDE, 0.6, 0.45)


def _cena(spec: dict) -> Cena:
    tipo = spec.get("tipo", "frases")
    if tipo == "frases":
        return Frases(spec["linhas"], spec.get("dur"), spec.get("riscar", False), spec.get("sub"))
    if tipo == "gancho_numero":
        return GanchoNumero(spec["numero"], spec["linhas"], spec.get("dur", 2.6))
    if tipo == "item":
        return Item(spec["numero"], spec["titulo"], spec["texto"], spec.get("dur", 3.6))
    if tipo == "mito":
        return Mito(spec["frase"], spec["verdade"], spec["texto"], spec.get("indice", ""), spec.get("dur", 3.9))
    if tipo == "disputa":
        return Disputa(spec["lances"], spec.get("dur"), spec.get("selo", "VENDIDO!"))
    raise ValueError(f"Tipo de cena desconhecido: {tipo}")


class Reel:
    def __init__(self, roteiro: dict):
        global ETIQUETA
        if ETIQUETA is None:
            ETIQUETA = _etiqueta()
        cenas = [_cena(c) for c in roteiro["cenas"]]
        # títulos dos itens com o mesmo tamanho
        itens = [c for c in roteiro["cenas"] if c.get("tipo") == "item"]
        if itens:
            todas = [ln for c in itens for ln in c["titulo"]]
            f = ajustar(todas, "titulo", W - 2 * M, 140)
            cenas = [Item(c["numero"], c["titulo"], c["texto"], c.get("dur", 3.6), f) if c.get("tipo") == "item" else o
                     for c, o in zip(roteiro["cenas"], cenas)]
        self.conteudo = cenas
        self.slogan = Slogan()
        self.marca = Marca()
        self.cenas = cenas + [self.slogan, self.marca]
        self.inicios = []
        t = 0.0
        for c in self.cenas:
            self.inicios.append(t)
            t += c.dur
        self.duracao = t
        self.t_slogan = self.inicios[-2]
        self.t_marca = self.inicios[-1]

    def quadro(self, t: float) -> Image.Image:
        img = fundo(t)
        if t < self.t_slogan:
            por(img, ETIQUETA, ease(t / 0.3) * (1 - ease((t - self.t_slogan + 0.3) / 0.3)))
        for c, ini in zip(self.cenas, self.inicios):
            if ini <= t < ini + c.dur:
                local = t - ini
                ultima = c is self.marca
                out = 1.0 if ultima else 1 - ease((local - (c.dur - 0.25)) / 0.25)
                c.desenhar(img, local, out)
                break
        return img

    def renderizar(self, destino: Path, pasta_tmp: Path) -> Path:
        pasta_tmp.mkdir(parents=True, exist_ok=True)
        video = pasta_tmp / (destino.stem + "_v.mp4")
        audio = pasta_tmp / (destino.stem + ".wav")
        p = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
             "-pix_fmt", "yuv420p", str(video)],
            stdin=subprocess.PIPE)
        for n in range(int(round(self.duracao * FPS))):
            p.stdin.write(self.quadro(n / FPS).tobytes())
        p.stdin.close()
        if p.wait() != 0:
            raise RuntimeError("ffmpeg falhou ao gerar o vídeo")
        eventos = [(ini + tl, tipo) for c, ini in zip(self.conteudo, self.inicios) for tl, tipo in c.eventos]
        trilha.compor(self.duracao, self.inicios[:len(self.conteudo)], eventos, self.t_slogan, self.t_marca, audio,
                      semente=int(self.duracao * 100) % 97)
        parcial = destino.with_suffix(".part.mp4")
        r = subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(audio), "-map", "0:v", "-map", "1:a",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(parcial)])
        if r.returncode != 0:
            raise RuntimeError("ffmpeg falhou ao juntar a trilha")
        parcial.replace(destino)
        return destino

    def previa(self, pasta: Path, tempos: list[float] | None = None) -> list[Path]:
        """Salva alguns quadros para conferência (no meio de cada cena)."""
        pasta.mkdir(parents=True, exist_ok=True)
        tempos = tempos or [ini + c.dur * 0.75 for c, ini in zip(self.cenas, self.inicios)]
        saida = []
        for i, t in enumerate(tempos):
            caminho = pasta / f"quadro_{i:02d}.png"
            self.quadro(t).save(caminho)
            saida.append(caminho)
        return saida
