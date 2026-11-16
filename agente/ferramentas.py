"""Ferramentas que o Claude pode usar: analisar o Instagram, criar artes e publicar."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import requests
from anthropic import beta_tool

from . import artes
from .config import PASTA_SAIDA, Config
from .hospedagem import url_publica
from .instagram import Instagram


def _json(dados) -> str:
    return json.dumps(dados, ensure_ascii=False, indent=2, default=str)


def _imagem_b64(caminho_ou_bytes, tipo="image/jpeg") -> dict:
    dados = caminho_ou_bytes if isinstance(caminho_ou_bytes, bytes) else Path(caminho_ou_bytes).read_bytes()
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": tipo, "data": base64.standard_b64encode(dados).decode()},
    }


def criar_ferramentas(cfg: Config, ig: Instagram | None, modo_publicacao: str):
    """modo_publicacao: 'confirmar' (pergunta no terminal), 'auto' ou 'simular'."""

    def _ig() -> Instagram:
        if ig is None:
            raise RuntimeError("Instagram não configurado (INSTAGRAM_ACCESS_TOKEN vazio no .env).")
        return ig

    @beta_tool
    def ver_perfil() -> str:
        """Retorna os dados do perfil do Instagram: usuário, bio, seguidores, quantidade de posts."""
        return _json(_ig().perfil())

    @beta_tool
    def listar_posts(limite: int = 20, com_metricas: bool = True) -> str:
        """Lista os posts mais recentes com legenda, tipo, data, curtidas e comentários.

        Args:
            limite: Quantos posts buscar (1 a 50).
            com_metricas: Se True, inclui alcance, salvamentos e compartilhamentos de cada post (mais lento).
        """
        posts = _ig().posts_recentes(limite)
        for p in posts:
            p.pop("media_url", None)
            p.pop("thumbnail_url", None)
            if com_metricas:
                p["metricas"] = _ig().insights_post(p["id"])
        return _json(posts)

    @beta_tool
    def metricas_da_conta(dias: int = 28) -> str:
        """Métricas gerais da conta no período: alcance, contas engajadas, interações, visitas ao perfil.

        Args:
            dias: Período em dias (máximo 30).
        """
        return _json(_ig().insights_conta(dias))

    @beta_tool
    def ver_imagens_dos_posts(ids: list[str]) -> list[dict]:
        """Mostra as imagens de posts específicos para analisar o estilo visual (cores, layout, tipografia).

        Args:
            ids: IDs dos posts (obtidos em listar_posts). Máximo 6.
        """
        posts = {p["id"]: p for p in _ig().posts_recentes(50)}
        blocos: list[dict] = []
        for pid in ids[:6]:
            p = posts.get(pid)
            url = p and (p.get("thumbnail_url") or p.get("media_url"))
            if not url:
                blocos.append({"type": "text", "text": f"Post {pid}: imagem indisponível."})
                continue
            r = requests.get(url, timeout=30)
            tipo = r.headers.get("content-type", "image/jpeg").split(";")[0]
            if r.ok and tipo in ("image/jpeg", "image/png", "image/webp", "image/gif"):
                blocos.append({"type": "text", "text": f"Post {pid} ({p.get('media_type')}):"})
                blocos.append(_imagem_b64(r.content, tipo))
            else:
                blocos.append({"type": "text", "text": f"Post {pid}: falha ao baixar a imagem."})
        return blocos

    @beta_tool
    def criar_arte(
        modelo: str,
        titulo: str,
        subtitulo: str = "",
        cta: str = "",
        itens: list[str] | None = None,
        destaque: str = "",
        formato: str = "retrato",
        cor_fundo: str = "",
        cor_destaque: str = "",
    ) -> list[dict]:
        """Cria uma arte (JPEG) para o feed e devolve a imagem para você revisar antes de publicar.

        Args:
            modelo: "destaque" (título + subtítulo), "oferta" (selo com preço/desconto), "lista" (itens numerados) ou "citacao" (frase com aspas).
            titulo: Texto principal, curto e forte (idealmente até 8 palavras).
            subtitulo: Texto de apoio. No modelo "citacao" é o autor.
            cta: Texto do botão de chamada, ex. "Chame no direct". Vazio para não exibir.
            itens: Lista de até 6 itens curtos (apenas no modelo "lista").
            destaque: Texto do selo no modelo "oferta", ex. "-30%" ou "R$ 49,90".
            formato: "retrato" (1080x1350, recomendado para feed), "quadrado" (1080x1080) ou "story" (1080x1920).
            cor_fundo: Cor de fundo em hex (#RRGGBB). Vazio usa a cor da marca.
            cor_destaque: Cor de destaque em hex. Vazio usa a cor da marca.
        """
        caminho = artes.criar_arte(
            cfg, modelo, titulo, subtitulo, cta, itens, destaque, formato, cor_fundo, cor_destaque
        )
        return [
            {"type": "text", "text": f"Arte criada: {caminho.name}. Revise a imagem abaixo; se algo estiver ruim, crie outra."},
            _imagem_b64(caminho),
        ]

    @beta_tool
    def publicar_post(arquivo_arte: str, legenda: str) -> str:
        """Publica uma arte criada no feed do Instagram com a legenda informada.

        Args:
            arquivo_arte: Nome do arquivo retornado por criar_arte (ex. "20261116-101500-titulo.jpg").
            legenda: Legenda completa do post, incluindo chamada para ação e hashtags (máx. 2200 caracteres, até 30 hashtags).
        """
        caminho = (PASTA_SAIDA / Path(arquivo_arte).name).resolve()
        if caminho.parent != PASTA_SAIDA.resolve() or not caminho.exists():
            return f"Erro: arquivo {arquivo_arte} não encontrado na pasta saida/."
        if len(legenda) > 2200:
            return "Erro: a legenda passa de 2200 caracteres. Encurte e tente de novo."

        if modo_publicacao == "simular":
            return f"[SIMULAÇÃO] Post NÃO publicado. Arte: {caminho} | Legenda:\n{legenda}"

        if modo_publicacao == "confirmar":
            print("\n" + "=" * 60)
            print(f"PUBLICAR NO INSTAGRAM?\nArte: {caminho}\n\nLegenda:\n{legenda}")
            print("=" * 60)
            resposta = input("Publicar agora? [s/N] ").strip().lower()
            if resposta not in ("s", "sim", "y", "yes"):
                motivo = input("O que mudar? (Enter para só cancelar) ").strip()
                return "O usuário NÃO aprovou a publicação." + (f" Pedido de ajuste: {motivo}" if motivo else "")

        url = url_publica(caminho, cfg)
        resultado = _ig().publicar_imagem(url, legenda)
        return "Publicado com sucesso! " + _json(resultado)

    return [
        ver_perfil,
        listar_posts,
        metricas_da_conta,
        ver_imagens_dos_posts,
        criar_arte,
        publicar_post,
    ]
