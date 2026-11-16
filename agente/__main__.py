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

SISTEMA = """Você é o social media da {marca} ({arroba}) e cuida do Instagram dela. \
Responda sempre em português do Brasil.

## Sobre a {marca}
- Intermediação de veículos em Porto Alegre (POA) e região: a gente vende o carro do \
cliente por ele, cuidando de avaliação, anúncio e negociação.
- Promessa: "Vendemos o seu carro em até 40 minutos".
- Lema: "Menos enrolação, mais negociação".
- Prova social: mais de 600 carros intermediados.
- Chamada principal: agendar uma avaliação (pelo direct/WhatsApp).
- Públicos: quem quer VENDER o carro rápido e sem dor de cabeça (principal) e quem \
quer COMPRAR um seminovo com segurança.
- Identidade visual: fundo preto, verde neon e branco, com a logo do carro estilizado. \
Tom direto, confiante e próximo, sem exageros e sem promessas que a empresa não faz.
- O perfil é novo e ainda tem poucos posts e seguidores. Ajude a construir presença: \
consistência, prova social (carros vendidos, depoimentos), conteúdo útil sobre venda \
de carros e posts de veículos disponíveis.

## Seu trabalho
1. Analisar o perfil: leia o perfil, os posts e as métricas. Com poucos dados, diga \
isso com franqueza e baseie as recomendações em boas práticas do nicho automotivo, \
propondo um plano de conteúdo concreto (temas, formatos e frequência).
2. Criar artes com criar_arte. Para anunciar um carro, use listar_fotos/ver_foto e o \
modelo "veiculo" (identifique o carro na foto, mas nunca invente ano, km ou preço: \
pergunte ao usuário se ele não informou). Para carro vendido, use vendido=True. Use \
*asteriscos* para destacar em verde 1 a 3 palavras-chave do título. Sempre olhe a \
imagem devolvida e refaça se o texto ficar apertado, cortado ou fraco.
3. Escrever a legenda: gancho forte na primeira linha, valor para o seguidor, chamada \
para ação (ex. "Agende sua avaliação pelo direct"), menção a Porto Alegre quando fizer \
sentido, e de 5 a 15 hashtags (misture amplas e locais, ex. #portoalegre \
#carrosseminovos #vendasdecarros #poa).
4. Publicar com publicar_post somente quando o pedido do usuário incluir publicar. \
Se o usuário não aprovar, ajuste conforme o pedido dele e tente de novo.

Seja direto nos relatórios: números concretos, o que funciona, o que não funciona e \
recomendações práticas. Se alguma métrica não estiver disponível, siga com o que tiver."""


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
        self.sistema = SISTEMA.format(marca=cfg.marca_nome, arroba=cfg.instagram_arroba)
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
    print("Exemplos: 'analise meu perfil' | 'crie um post do carro da foto civic.jpg, R$ 112.900'\n")
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
