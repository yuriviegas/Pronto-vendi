"""Agente de IA para Instagram: analisa o perfil, cria artes e publica.

Uso:
    python -m agente                      # conversa interativa
    python -m agente "crie um post sobre a promoção de sexta"
    python -m agente --auto "..."         # publica sem pedir confirmação
    python -m agente --simular "..."      # nunca publica (teste)
"""

from __future__ import annotations

import argparse
import json
import sys

import anthropic

from . import config
from .ferramentas import criar_ferramentas
from .instagram import Instagram

SISTEMA = """Você é o social media da marca "{marca}". Você gerencia o Instagram dela \
e responde sempre em português do Brasil.

Seu trabalho:
1. Analisar o perfil: leia o perfil, os posts recentes e suas métricas. Descubra quais \
temas, formatos, horários e estilos de legenda geram mais alcance, salvamentos e \
comentários. Quando ajudar, veja as imagens dos melhores e piores posts para entender \
o estilo visual.
2. Criar artes com a ferramenta criar_arte. Textos curtos e legíveis no celular, \
coerentes com a identidade visual que você observou. Sempre olhe a imagem devolvida; \
se o texto ficou apertado, cortado ou fraco, refaça.
3. Escrever a legenda: gancho forte na primeira linha, valor para o seguidor, chamada \
para ação clara e de 5 a 15 hashtags relevantes (misture amplas e de nicho).
4. Publicar com publicar_post somente quando o pedido do usuário incluir publicar. \
Se o usuário não aprovar, ajuste conforme o pedido dele e tente de novo.

Seja direto nos relatórios: números concretos, o que funciona, o que não funciona e \
recomendações práticas. Se alguma métrica não estiver disponível, siga com o que tiver.
Cores da marca: primária {cor1}, secundária {cor2}."""


def _texto(conteudo) -> str:
    return "\n".join(b.text for b in conteudo if b.type == "text" and b.text)


class Agente:
    def __init__(self, cfg: config.Config, modo_publicacao: str):
        self.cfg = cfg
        self.client = anthropic.Anthropic()
        ig = None
        if cfg.instagram_token:
            ig = Instagram(cfg.instagram_token, cfg.instagram_api_base, cfg.instagram_user_id)
        else:
            print("Aviso: INSTAGRAM_ACCESS_TOKEN vazio — só a criação de artes vai funcionar.\n")
        self.ferramentas = {f.name: f for f in criar_ferramentas(cfg, ig, modo_publicacao)}
        self.sistema = SISTEMA.format(
            marca=cfg.marca_nome, cor1=cfg.cor_primaria, cor2=cfg.cor_secundaria
        )
        self.historico: list = []

    def _executar(self, bloco) -> dict:
        print(f"  → {bloco.name}({json.dumps(bloco.input, ensure_ascii=False)[:150]})")
        ferramenta = self.ferramentas.get(bloco.name)
        try:
            if ferramenta is None:
                raise ValueError(f"Ferramenta desconhecida: {bloco.name}")
            resultado = ferramenta.call(bloco.input)
            return {"type": "tool_result", "tool_use_id": bloco.id, "content": resultado}
        except Exception as e:  # devolve o erro ao Claude para ele reagir
            print(f"    ✗ {e}")
            return {
                "type": "tool_result",
                "tool_use_id": bloco.id,
                "content": f"Erro: {e}",
                "is_error": True,
            }

    def enviar(self, mensagem: str) -> str:
        self.historico.append({"role": "user", "content": mensagem})
        for _ in range(40):  # limite de segurança de passos
            try:
                resposta = self.client.beta.messages.create(
                    model=self.cfg.modelo,
                    max_tokens=16000,
                    system=self.sistema,
                    tools=[f.to_dict() for f in self.ferramentas.values()],
                    messages=self.historico,
                    output_config={"effort": "high"},
                    cache_control={"type": "ephemeral"},
                    # Se o modelo principal recusar, o próprio servidor tenta outro modelo
                    betas=["server-side-fallback-2026-07-01"],
                    fallbacks="default",
                )
            except anthropic.AuthenticationError:
                sys.exit("Chave da Anthropic inválida. Confira ANTHROPIC_API_KEY no .env.")
            except anthropic.RateLimitError:
                sys.exit("Limite de uso da API atingido. Tente de novo em alguns minutos.")
            except anthropic.APIConnectionError:
                sys.exit("Sem conexão com a API da Anthropic.")

            # Guarda o conteúdo completo (inclui blocos de raciocínio) no histórico
            self.historico.append({"role": "assistant", "content": resposta.content})

            if resposta.stop_reason == "refusal":
                return "O modelo recusou este pedido. Reformule e tente novamente."
            if resposta.stop_reason == "pause_turn":
                continue
            if resposta.stop_reason == "max_tokens":
                return _texto(resposta.content) + "\n[resposta cortada por limite de tamanho]"

            chamadas = [b for b in resposta.content if b.type == "tool_use"]
            if not chamadas:
                return _texto(resposta.content)

            parcial = _texto(resposta.content)
            if parcial:
                print(parcial)
            # Todos os resultados vão juntos em uma única mensagem
            self.historico.append(
                {"role": "user", "content": [self._executar(b) for b in chamadas]}
            )
        return "Parei: muitos passos seguidos. Peça para continuar se quiser."


def main() -> None:
    p = argparse.ArgumentParser(description="Agente de IA para Instagram")
    p.add_argument("tarefa", nargs="*", help="Pedido para o agente (vazio = modo conversa)")
    grupo = p.add_mutually_exclusive_group()
    grupo.add_argument("--auto", action="store_true", help="Publica sem pedir confirmação")
    grupo.add_argument("--simular", action="store_true", help="Nunca publica de verdade")
    args = p.parse_args()

    modo = "auto" if args.auto else "simular" if args.simular else "confirmar"
    agente = Agente(config.carregar(), modo)

    if args.tarefa:
        print(agente.enviar(" ".join(args.tarefa)))
        return

    print(f"Agente de Instagram — {agente.cfg.marca_nome} (modo: {modo}). 'sair' para encerrar.")
    print("Exemplos: 'analise meu perfil' | 'crie e publique um post sobre frete grátis'\n")
    while True:
        try:
            msg = input("Você: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if msg.lower() in ("sair", "exit", "quit"):
            break
        if msg:
            print(f"\nAgente: {agente.enviar(msg)}\n")


if __name__ == "__main__":
    main()
