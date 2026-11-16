"""Coloca a arte numa URL pública (exigência da API do Instagram)."""

from __future__ import annotations

import base64
from pathlib import Path

import requests

from .config import Config


def url_publica(caminho: Path, cfg: Config) -> str:
    if cfg.imgbb_api_key:
        with open(caminho, "rb") as f:
            imagem = base64.b64encode(f.read()).decode()
        r = requests.post(
            "https://api.imgbb.com/1/upload",
            data={"key": cfg.imgbb_api_key, "image": imagem},
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["data"]["url"]
    if cfg.public_base_url:
        return f"{cfg.public_base_url}/{caminho.name}"
    raise RuntimeError(
        "Sem hospedagem configurada: defina IMGBB_API_KEY ou PUBLIC_BASE_URL no .env"
    )
