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
    def listar_fotos() -> str:
        """Lista as fotos de veículos disponíveis na pasta fotos/ para usar no modelo "veiculo"."""
        artes.PASTA_FOTOS.mkdir(exist_ok=True)
        fotos = sorted(
            f.name for f in artes.PASTA_FOTOS.iterdir()
            if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
        )
        return _json(fotos) if fotos else "Nenhuma foto na pasta fotos/. Peça ao usuário para colocar as fotos dos carros lá."

    @beta_tool
    def ver_foto(arquivo: str) -> list[dict]:
        """Mostra uma foto da pasta fotos/ para você identificar o carro e avaliar se a foto está boa.

        Args:
            arquivo: Nome do arquivo (obtido em listar_fotos).
        """
        caminho = (artes.PASTA_FOTOS / Path(arquivo).name).resolve()
        if caminho.parent != artes.PASTA_FOTOS.resolve() or not caminho.exists():
            return [{"type": "text", "text": f"Foto {arquivo} não encontrada."}]
        from io import BytesIO
        from PIL import Image, ImageOps
        im = ImageOps.exif_transpose(Image.open(caminho)).convert("RGB")
        im.thumbnail((1280, 1280))
        buf = BytesIO()
        im.save(buf, "JPEG", quality=85)
        return [{"type": "text", "text": f"Foto {arquivo}:"}, _imagem_b64(buf.getvalue())]

    @beta_tool
    def criar_arte(
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
    ) -> list[dict]:
        """Cria uma arte (JPEG) com a identidade da marca (preto, verde neon, logo) e devolve a imagem para você revisar.

        Coloque *palavras* entre asteriscos no título para pintá-las de verde (use em 1 a 3 palavras-chave).

        Args:
            modelo: "veiculo" (foto do carro + ficha + preço), "destaque" (título + subtítulo), "oferta" (selo grande com número/benefício), "lista" (itens numerados) ou "citacao" (depoimento de cliente).
            titulo: Texto principal, curto. No "veiculo" é marca/modelo/versão (ex. "Honda *Civic* EXL"). No "citacao" é o depoimento.
            subtitulo: Texto de apoio. No "veiculo" é a ficha (ex. "2019 · 45.000 km · Automático"). No "citacao" é o nome do cliente.
            cta: Texto do botão, ex. "Chame no direct", "Agende sua avaliação". Vazio para não exibir.
            itens: No "lista": até 6 itens curtos. No "veiculo": até 4 diferenciais curtos (ex. "Único dono").
            destaque: No "veiculo": preço (ex. "R$ 112.900") ou frase curta (ex. "Vendido em 38 min"). No "oferta": texto do selo (ex. "+600", "40 min").
            formato: "retrato" (1080x1350, recomendado para feed), "quadrado" (1080x1080) ou "story" (1080x1920).
            foto: Obrigatória no "veiculo": nome do arquivo na pasta fotos/ (veja listar_fotos) ou URL de uma imagem.
            vendido: No "veiculo": True aplica o carimbo VENDIDO sobre a foto.
            estrelas: No "citacao": quantidade de estrelas de avaliação (0 a 5).
        """
        caminho = artes.criar_arte(
            cfg, modelo, titulo, subtitulo, cta, itens, destaque, formato, foto, vendido, estrelas
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
        listar_fotos,
        ver_foto,
        criar_arte,
        publicar_post,
    ]
