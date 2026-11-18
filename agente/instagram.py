"""Cliente mínimo da API do Instagram (Graph API).

Funciona com a "API do Instagram com login do Instagram" (graph.instagram.com)
e, trocando INSTAGRAM_API_BASE, com contas ligadas a uma Página do Facebook
(graph.facebook.com).
"""

from __future__ import annotations

import time

import requests


class InstagramErro(RuntimeError):
    pass


class Instagram:
    def __init__(self, token: str, api_base: str, user_id: str = ""):
        if not token:
            raise InstagramErro(
                "INSTAGRAM_ACCESS_TOKEN não configurado no .env"
            )
        self.token = token
        self.base = api_base
        self._user_id = user_id

    # ---------------------------------------------------------------- básico
    def _req(self, metodo: str, caminho: str, **params) -> dict:
        params["access_token"] = self.token
        url = f"{self.base}/{caminho.lstrip('/')}"
        if metodo == "GET":
            r = requests.get(url, params=params, timeout=30)
        else:
            r = requests.post(url, data=params, timeout=60)
        try:
            dados = r.json()
        except ValueError:
            raise InstagramErro(f"Resposta inválida ({r.status_code}): {r.text[:300]}")
        if r.status_code >= 400 or "error" in dados:
            erro = dados.get("error", {})
            raise InstagramErro(
                f"Erro da API do Instagram ({r.status_code}): "
                f"{erro.get('message', dados)}"
            )
        return dados

    @property
    def user_id(self) -> str:
        if not self._user_id:
            dados = self._req("GET", "me", fields="user_id,id,username")
            self._user_id = str(dados.get("user_id") or dados["id"])
        return self._user_id

    # --------------------------------------------------------------- leitura
    def perfil(self) -> dict:
        return self._req(
            "GET",
            self.user_id,
            fields="username,name,biography,followers_count,follows_count,media_count",
        )

    def posts_recentes(self, limite: int = 20) -> list[dict]:
        dados = self._req(
            "GET",
            f"{self.user_id}/media",
            fields=(
                "id,caption,media_type,media_url,thumbnail_url,permalink,"
                "timestamp,like_count,comments_count"
            ),
            limit=min(max(limite, 1), 50),
        )
        return dados.get("data", [])

    def insights_post(self, media_id: str) -> dict:
        """Métricas de um post. Nem toda métrica existe para todo tipo de mídia,
        então tentamos um conjunto amplo e caímos para um menor se falhar."""
        for metricas in ("reach,saved,shares,total_interactions,views", "reach,saved"):
            try:
                dados = self._req("GET", f"{media_id}/insights", metric=metricas)
                return {m["name"]: m["values"][0]["value"] for m in dados.get("data", [])}
            except InstagramErro:
                continue
        return {}

    def insights_conta(self, dias: int = 28) -> dict:
        fim = int(time.time())
        inicio = fim - min(dias, 30) * 86400
        resultado: dict = {}
        for metrica in ("reach", "accounts_engaged", "total_interactions", "profile_views"):
            try:
                dados = self._req(
                    "GET",
                    f"{self.user_id}/insights",
                    metric=metrica,
                    period="day",
                    metric_type="total_value",
                    since=inicio,
                    until=fim,
                )
                for m in dados.get("data", []):
                    resultado[m["name"]] = m.get("total_value", {}).get("value")
            except InstagramErro as e:
                resultado[metrica] = f"indisponível ({e})"
        return resultado

    # ------------------------------------------------------------ publicação
    def _aguardar(self, cid: str, tentativas: int = 30, intervalo: float = 2) -> None:
        """Espera o Instagram terminar de processar o container."""
        for _ in range(tentativas):
            dados = self._req("GET", cid, fields="status_code")
            status = dados.get("status_code")
            if status == "FINISHED":
                return
            if status in ("ERROR", "EXPIRED"):
                raise InstagramErro(f"Falha ao processar a mídia (status {status})")
            time.sleep(intervalo)
        raise InstagramErro("O Instagram demorou demais para processar a mídia")

    def _publicar_container(self, cid: str) -> dict:
        publicado = self._req("POST", f"{self.user_id}/media_publish", creation_id=cid)
        media_id = publicado["id"]
        try:
            link = self._req("GET", media_id, fields="permalink").get("permalink")
        except InstagramErro:
            link = None
        return {"media_id": media_id, "permalink": link}

    def publicar_story_imagem(self, url_imagem: str) -> dict:
        """Story de imagem. A imagem precisa estar numa URL pública (JPEG)."""
        container = self._req(
            "POST", f"{self.user_id}/media", image_url=url_imagem, media_type="STORIES"
        )
        self._aguardar(container["id"])
        return self._publicar_container(container["id"])

    def publicar_video(self, caminho: str, legenda: str = "", tipo: str = "REELS") -> dict:
        """Reel (tipo REELS) ou story de vídeo (tipo STORIES).

        Usa o upload "resumable": o arquivo vai direto do computador/servidor
        para o Instagram, sem precisar de hospedagem pública.
        """
        import os

        params = {"media_type": tipo, "upload_type": "resumable"}
        if tipo == "REELS" and legenda:
            params["caption"] = legenda
        container = self._req("POST", f"{self.user_id}/media", **params)
        cid = container["id"]
        uri = container.get("uri") or (
            f"https://rupload.facebook.com/ig-api-upload/{self.base.rsplit('/', 1)[-1]}/{cid}"
        )
        tamanho = os.path.getsize(caminho)
        with open(caminho, "rb") as f:
            r = requests.post(
                uri,
                headers={
                    "Authorization": f"OAuth {self.token}",
                    "offset": "0",
                    "file_size": str(tamanho),
                },
                data=f,
                timeout=300,
            )
        if r.status_code >= 400:
            raise InstagramErro(f"Falha no envio do vídeo ({r.status_code}): {r.text[:300]}")
        self._aguardar(cid, tentativas=30, intervalo=10)
        return self._publicar_container(cid)

    def publicar_imagem(self, url_imagem: str, legenda: str) -> dict:
        container = self._req(
            "POST", f"{self.user_id}/media", image_url=url_imagem, caption=legenda
        )
        cid = container["id"]
        self._aguardar(cid)
        publicado = self._req("POST", f"{self.user_id}/media_publish", creation_id=cid)
        media_id = publicado["id"]
        try:
            link = self._req("GET", media_id, fields="permalink").get("permalink")
        except InstagramErro:
            link = None
        return {"media_id": media_id, "permalink": link}
