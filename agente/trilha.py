"""Trilha original sintetizada (numpy), sincronizada com as cenas do Reel.

Sem música de terceiros: não há risco de direitos autorais. 120 bpm.
"""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

SR = 44100


class Trilha:
    def __init__(self, duracao: float, semente: int = 3):
        self.dur = duracao
        self.n = int(SR * duracao)
        self.t = np.arange(self.n) / SR
        self.mix = np.zeros(self.n)
        self.rng = np.random.default_rng(semente)

    # ---------------------------------------------------------------- base
    def add(self, sinal, inicio, ganho=1.0):
        i = int(inicio * SR)
        if i >= self.n or i < 0:
            return
        k = min(len(sinal), self.n - i)
        self.mix[i:i + k] += sinal[:k] * ganho

    @staticmethod
    def _env(n, tau):
        return np.exp(-np.arange(n) / (SR * tau))

    @staticmethod
    def _passa_baixa(x, k):
        return np.convolve(x, np.ones(k) / k, mode="same")

    @staticmethod
    def _serra(f, n, harm=7):
        tt = np.arange(n) / SR
        return sum(np.sin(2 * np.pi * f * h * tt) / h for h in range(1, harm + 1))

    # ---------------------------------------------------------------- sons
    def bumbo(self, d=0.35):
        n = int(SR * d)
        tt = np.arange(n) / SR
        f = 45 + 110 * np.exp(-tt / 0.03)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * self._env(n, 0.12)

    def tique(self, f=2400, d=0.05):
        n = int(SR * d)
        return np.sin(2 * np.pi * f * np.arange(n) / SR) * self._env(n, 0.008)

    def chimbal(self, d=0.06):
        n = int(SR * d)
        x = self.rng.standard_normal(n)
        return (x - self._passa_baixa(x, 8)) * self._env(n, 0.015)

    def impacto(self, d=1.6, grave=42):
        n = int(SR * d)
        tt = np.arange(n) / SR
        f = grave + 60 * np.exp(-tt / 0.05)
        corpo = np.sin(2 * np.pi * np.cumsum(f) / SR) * self._env(n, 0.45)
        ruido = self._passa_baixa(self.rng.standard_normal(n), 24) * self._env(n, 0.18) * 1.5
        return corpo + ruido

    def batida(self, d=0.5):
        n = int(SR * d)
        tt = np.arange(n) / SR
        corpo = np.sin(2 * np.pi * np.cumsum(60 + 80 * np.exp(-tt / 0.02)) / SR) * self._env(n, 0.1)
        return corpo + self._passa_baixa(self.rng.standard_normal(n), 10) * self._env(n, 0.05) * 0.9

    def pluck(self, f, d=0.22):
        n = int(SR * d)
        return self._serra(f, n, 5) * self._env(n, 0.07)

    def pad(self, freqs, d, ataque=0.05, soltura=0.6):
        n = int(SR * d)
        tt = np.arange(n) / SR
        x = np.zeros(n)
        for f in freqs:
            for det in (-0.004, 0.004):
                x += self._serra(f * (1 + det), n, 6)
        e = np.minimum(1, tt / ataque) * np.minimum(1, np.maximum(0, d - tt) / soltura)
        return self._passa_baixa(x, 6) * e * (0.8 + 0.2 * np.sin(2 * np.pi * 4 * tt)) / len(freqs)

    def sino(self, f=1318.5, d=0.6):
        n = int(SR * d)
        tt = np.arange(n) / SR
        return (np.sin(2 * np.pi * f * tt) + 0.5 * np.sin(2 * np.pi * f * 2.01 * tt)
                + 0.25 * np.sin(2 * np.pi * f * 3 * tt)) * self._env(n, 0.15)

    def buzina(self, d=0.45):
        n = int(SR * d)
        tt = np.arange(n) / SR
        x = 0.5 * np.sign(np.sin(2 * np.pi * 140 * tt)) + 0.5 * np.sign(np.sin(2 * np.pi * 147 * tt))
        return self._passa_baixa(x, 6) * np.minimum(1, (d - tt) / 0.05) * 0.6

    def subida(self, inicio, d=0.8, ganho=0.45):
        n = int(SR * d)
        tt = np.arange(n) / SR
        varre = np.sin(2 * np.pi * np.cumsum(180 * 2 ** (tt * 3.5)) / SR)
        nz = self.rng.standard_normal(n)
        nz = nz - self._passa_baixa(nz, 12)
        self.add((varre * 0.5 + nz * 0.6) * tt ** 2, inicio, ganho)

    # ---------------------------------------------------------------- blocos
    def groove(self, ini, fim, raizes, forte=0.65, fraco=0.42):
        b, i = ini, 0
        while b < fim - 1e-6:
            r = raizes[(i // 4) % len(raizes)]
            self.add(self.bumbo(), b, forte if i % 2 == 0 else fraco)
            self.add(self.chimbal(), b + 0.25, 0.17)
            self.add(self.pluck(r), b, 0.16)
            self.add(self.pluck(r * 1.5), b + 0.25, 0.09)
            b += 0.5
            i += 1

    def salvar(self, caminho: Path):
        fade = np.clip((self.dur - self.t) / 1.2, 0, 1)
        mix = np.tanh(self.mix * fade * 1.4)
        mix = mix / (np.max(np.abs(mix)) or 1) * 0.84
        pcm = (mix * 32767).astype(np.int16)
        st = np.repeat(pcm[:, None], 2, axis=1)
        with wave.open(str(caminho), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(st.tobytes())


A2, C3, D3, E3, F3, G3, A3, C4, D4, E4 = 110.0, 130.81, 146.83, 164.81, 174.61, 196.0, 220.0, 261.63, 293.66, 329.63
F2, G2, B2 = 87.31, 98.0, 123.47


def compor(duracao: float, cortes: list[float], eventos: list[tuple[float, str]], t_slogan: float, t_marca: float,
           caminho: Path, semente: int = 3):
    """cortes: inícios de cena (recebem impacto); eventos: (tempo, 'ok'|'erro'|'lance'|'batida')."""
    tr = Trilha(duracao, semente)
    tr.add(tr.impacto(), 0.0, 0.9)
    for k in (0.0, 0.4, 0.8):
        tr.add(tr.batida(), k, 0.45)
    inicio_groove = cortes[1] if len(cortes) > 1 else 2.0
    for i in range(int(inicio_groove / 0.25)):
        tr.add(tr.tique(2400 if i % 2 == 0 else 1700), i * 0.25, 0.22 if i % 2 == 0 else 0.12)
    tr.groove(inicio_groove, t_slogan, [A2, F2 * 2, C3, G2 * 2])
    tr.add(tr.pad([A2, E3, A3, C4], t_slogan - inicio_groove, ataque=0.8, soltura=0.4), inicio_groove, 0.16)
    for c in cortes[1:]:
        if c < t_slogan - 0.1:
            tr.add(tr.impacto(1.0, 50), c, 0.6)
            tr.add(tr.batida(), c, 0.35)
    notas = [987.8, 1046.5, 1174.7, 1318.5, 1396.9, 1568.0, 1760.0]
    k = 0
    for tempo, tipo in eventos:
        if tipo == "ok":
            tr.add(tr.batida(), tempo, 0.55)
            tr.add(tr.sino(1318.5, 0.9), tempo, 0.4)
            tr.add(tr.sino(1975.5, 0.9), tempo + 0.05, 0.3)
        elif tipo == "erro":
            tr.add(tr.batida(), tempo, 0.55)
            tr.add(tr.buzina(), tempo, 0.45)
        elif tipo == "lance":
            tr.add(tr.sino(notas[k % len(notas)]), tempo, 0.35)
            k += 1
        elif tipo == "batida":
            tr.add(tr.batida(), tempo, 0.6)
    tr.subida(t_slogan - 0.8)
    # slogan
    tr.add(tr.impacto(), t_slogan, 1.0)
    tr.add(tr.pad([D3 / 2, A2, D3, F3, A3, D4], t_marca - t_slogan, soltura=0.3), t_slogan, 0.5)
    b = t_slogan
    while b < t_marca - 1e-6:
        tr.add(tr.bumbo(), b, 0.8)
        tr.add(tr.chimbal(), b + 0.25, 0.22)
        tr.add(tr.pluck(D3 / 2), b, 0.2)
        tr.add(tr.pluck(D3 / 2), b + 0.25, 0.14)
        b += 0.5
    # marca
    tr.add(tr.impacto(), t_marca, 1.0)
    tr.add(tr.pad([A2, E3, A3, C4 * 2 ** (1 / 12), E4], duracao - t_marca, soltura=3.0), t_marca, 0.55)
    for i in range(5):
        b = t_marca + i * 0.5
        tr.add(tr.bumbo(), b, 0.8)
        tr.add(tr.chimbal(), b + 0.25, 0.22)
        tr.add(tr.pluck(A2), b, 0.2)
        tr.add(tr.pluck(A2), b + 0.25, 0.14)
    tr.salvar(caminho)
