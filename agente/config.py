"""Configuração lida do arquivo .env / variáveis de ambiente."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

RAIZ = Path(__file__).resolve().parent.parent
PASTA_SAIDA = RAIZ / "saida"
PASTA_SAIDA.mkdir(exist_ok=True)


@dataclass(frozen=True)
class Config:
    instagram_token: str
    instagram_user_id: str
    instagram_api_base: str
    imgbb_api_key: str
    public_base_url: str
    marca_nome: str
    cor_primaria: str
    cor_secundaria: str
    cor_texto: str
    modelo: str


def carregar() -> Config:
    return Config(
        instagram_token=os.getenv("INSTAGRAM_ACCESS_TOKEN", "").strip(),
        instagram_user_id=os.getenv("INSTAGRAM_USER_ID", "").strip(),
        instagram_api_base=os.getenv(
            "INSTAGRAM_API_BASE", "https://graph.instagram.com/v21.0"
        ).rstrip("/"),
        imgbb_api_key=os.getenv("IMGBB_API_KEY", "").strip(),
        public_base_url=os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/"),
        marca_nome=os.getenv("MARCA_NOME", "Pronto Vendi"),
        cor_primaria=os.getenv("MARCA_COR_PRIMARIA", "#FF5A1F"),
        cor_secundaria=os.getenv("MARCA_COR_SECUNDARIA", "#1E1E2E"),
        cor_texto=os.getenv("MARCA_COR_TEXTO", "#FFFFFF"),
        modelo=os.getenv("CLAUDE_MODEL", "claude-opus-5-5"),
    )
