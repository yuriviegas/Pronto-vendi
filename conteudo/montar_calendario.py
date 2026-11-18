"""Monta conteudo/calendario.json. Edite os textos aqui e rode:  python conteudo/montar_calendario.py

Regras da marca (não prometer o que a operação ainda não garante):
- não usar "vendemos em 40 minutos" como diferencial;
- não prometer pagamento antes de o carro chegar;
- "+600 carros" sempre "pela nossa equipe";
- valores de disputa são "exemplo ilustrativo".
"""

import json
from datetime import date, timedelta
from pathlib import Path

H = "#portoalegre #poa #vendaseucarro #carrosusados #prontovendi"
FIM = "Menos enrolação. Mais negociação. Em breve em Porto Alegre 🔔"


def leg(*partes):
    return "\n\n".join(partes + (FIM, H))


def riscar(*linhas):
    return {"tipo": "frases", "linhas": list(linhas), "riscar": True}


def frases(*linhas, sub=None, dur=None):
    c = {"tipo": "frases", "linhas": list(linhas)}
    if sub:
        c["sub"] = sub
    if dur:
        c["dur"] = dur
    return c


def item(n, titulo, texto):
    return {"tipo": "item", "numero": n, "titulo": titulo, "texto": texto}


def mito(i, frase, verdade, texto):
    return {"tipo": "mito", "indice": f"{i} / 3", "frase": frase, "verdade": verdade, "texto": texto}


def disputa(lances):
    return {"tipo": "disputa", "lances": lances}


REELS = [
    {"cenas": [frases("LOJISTAS."), frases("INVESTIDORES."), frases("TODOS DE", "OLHO NO", "*SEU CARRO.*")],
     "legenda": leg("Em breve, o seu carro no centro da disputa. 👀")},
    {"cenas": [frases("MITO", "OU", "*VERDADE?*", sub="Parte 4"),
               mito(1, "“Pneu gasto não muda o preço.”", False, "O comprador já calcula a troca e pede desconto."),
               mito(2, "“Carro de único dono passa mais confiança.”", True, "Histórico simples costuma deixar o comprador mais tranquilo."),
               mito(3, "“Quanto mais tempo anunciado, melhor a oferta.”", False, "Anúncio parado há meses levanta desconfiança, e a proposta cai.")],
     "legenda": leg("Quantas você acertou? 👇")},
    {"cenas": [{"tipo": "gancho_numero", "numero": "3", "linhas": ["COISAS QUE", "*DESVALORIZAM*", "O SEU", "CARRO"]},
               item("01", ["MANUTENÇÃO", "ATRASADA."], "Revisão vencida vira desconfiança e desconto."),
               item("02", ["RISCOS E", "AMASSADOS."], "Cada detalhe na lataria vira argumento na negociação."),
               item("03", ["DOCUMENTO", "PENDENTE."], "Débitos travam a transferência e assustam o comprador.")],
     "legenda": leg("Salva pra cuidar disso antes de vender 📌")},
    {"cenas": [frases("VOCÊ NÃO", "CORRE ATRÁS", "DE COMPRADOR."), frases("OS COMPRADORES", "*DISPUTAM*", "O SEU CARRO.")],
     "legenda": leg("Inverte o jogo. 👀")},
    {"cenas": [{"tipo": "gancho_numero", "numero": "4", "linhas": ["COISAS PRA", "FAZER *ANTES*", "DE VENDER", "SEU CARRO"]},
               item("01", ["LIMPEZA", "CAPRICHADA."], "Por dentro e por fora. É a primeira coisa que o comprador repara."),
               item("02", ["REVISÃO", "EM DIA."], "Óleo, freios e pneus em ordem mostram um carro bem cuidado."),
               item("03", ["DOCUMENTOS", "EM ORDEM."], "IPVA, licenciamento e multas quitados evitam travar a transferência."),
               item("04", ["SABER O", "VALOR REAL."], "Pesquise o preço de mercado do seu modelo, não só a tabela.")],
     "legenda": leg("Salva esse checklist 📌", "Qual desses você costuma esquecer?")},
    {"cenas": [frases("COMO A GENTE", "*TRABALHA:*"),
               item("01", ["SEGURANÇA."], "Do primeiro contato até o dinheiro na conta."),
               item("02", ["TRANSPARÊNCIA."], "Você vê cada oferta pelo seu carro."),
               item("03", ["AGILIDADE."], "Sem curioso, sem visita que não aparece.")],
     "legenda": leg("✅ Segurança do início ao fim\n✅ Transparência em cada oferta\n✅ Agilidade, sem enrolação")},
    {"cenas": [{"tipo": "gancho_numero", "numero": "3", "linhas": ["SINAIS DE QUE", "É HORA DE", "*VENDER*", "SEU CARRO"]},
               item("01", ["MANUTENÇÃO", "SÓ SOBE."], "Quando a oficina vira rotina, cada mês parado custa mais."),
               item("02", ["MAIS PARADO", "DO QUE RODANDO."], "Carro parado na garagem continua perdendo valor."),
               item("03", ["NÃO SERVE", "MAIS PRA VOCÊ."], "A família cresceu, a rotina mudou. O carro precisa acompanhar.")],
     "legenda": leg("Algum desses é o seu caso? 👀", "Comenta aqui 👇")},
    {"cenas": [frases("FIPE", "NÃO É", "*PREÇO DE VENDA.*"),
               item("01", ["A FIPE", "É MÉDIA."], "Ela mostra preços médios do mercado, não o valor do SEU carro."),
               item("02", ["O ESTADO", "MANDA."], "Quilometragem, conservação e revisões mudam o valor."),
               item("03", ["A PROCURA", "PESA."], "Modelos muito procurados vendem melhor. Os menos procurados, nem tanto.")],
     "legenda": leg("Você usava a Fipe como preço final? 👀", "Salva pra lembrar na hora de anunciar.")},
    {"cenas": [riscar("“FAZ 35", "À VISTA?”"), riscar("“AMANHÃ", "PASSO AÍ.”"), riscar("“TEM FOTO", "DO MOTOR?”"),
               frases("CHEGA", "*DISSO.*")],
     "legenda": leg("Quem nunca ouviu uma dessas? 😅", "Conta a pior que já te mandaram 👇")},
    {"cenas": [frases("MITO", "OU", "*VERDADE?*", sub="Parte 2"),
               mito(1, "“Carro com mais de 100 mil km não vende.”", False, "Vende sim. A quilometragem pesa no preço, mas estado e manutenção contam muito."),
               mito(2, "“Manual e chave reserva valorizam o carro.”", True, "Mostram cuidado e evitam desconto na negociação."),
               mito(3, "“Dá pra transferir com multa pendente.”", False, "IPVA, licenciamento e multas precisam estar quitados para transferir.")],
     "legenda": leg("Quantas você acertou? 👇")},
    {"cenas": [frases("SEU CARRO", "PARADO", "*PERDE VALOR.*", sub="Todo mês um pouco."),
               frases("E SE ELE", "VIRASSE", "*DINHEIRO?*")],
     "legenda": leg("Aquele carro que quase ninguém usa... já pensou em vender? 👀")},
    {"cenas": [{"tipo": "gancho_numero", "numero": "3", "linhas": ["DICAS DE", "FOTO QUE", "*VENDEM*", "SEU CARRO"]},
               item("01", ["LUZ", "DO DIA."], "Nada de foto à noite ou na garagem escura."),
               item("02", ["CARRO", "LIMPO."], "Lavado por fora, aspirado por dentro. Sem objetos no banco."),
               item("03", ["TODOS OS", "ÂNGULOS."], "Frente, traseira, laterais, painel, bancos e porta-malas.")],
     "legenda": leg("Salva e usa na próxima venda 📸")},
    {"cenas": [frases("IMAGINA:"), frases("VÁRIAS", "OFERTAS PELO", "SEU CARRO."),
               frases("E VOCÊ", "SÓ *ESCOLHE.*")],
     "legenda": leg("Em vez de correr atrás de comprador, deixar os compradores disputarem o seu carro. 👀")},
    {"cenas": [frases("E SE LOJISTAS", "E INVESTIDORES", "*DISPUTASSEM*", "O SEU SUV?"),
               disputa([["Investidor 1", 89000], ["Lojista 1", 91000], ["Lojista 2", 92500], ["Investidor 2", 94000],
                        ["Lojista 1", 95800], ["Investidor 3", 97500]]),
               frases("QUEM DÁ MAIS,", "*LEVA.*")],
     "legenda": leg("Seu carro, várias ofertas, uma escolha: a melhor. 👀", "(Valores do vídeo são um exemplo ilustrativo.)")},
    {"cenas": [{"tipo": "gancho_numero", "numero": "3", "linhas": ["PERGUNTAS", "PRA FAZER", "*ANTES*", "DE VENDER"]},
               item("01", ["QUANTO ELE", "VALE HOJE?"], "No mercado de verdade, não só na tabela."),
               item("02", ["DOCUMENTOS", "EM DIA?"], "Débito pendente trava a transferência."),
               item("03", ["QUEM CUIDA DA", "TRANSFERÊNCIA?"], "Sem ela feita, a responsabilidade continua com você.")],
     "legenda": leg("Você sabia responder as 3? 👇")},
    {"cenas": [riscar("ANÚNCIO", "PARADO."), riscar("TELEFONE", "TOCANDO TODA", "HORA."), riscar("NEGOCIAÇÃO", "QUE NÃO ANDA."),
               frases("TEM JEITO", "*MELHOR.*")],
     "legenda": leg("Vender carro não precisa ser um segundo emprego. 😅")},
    {"cenas": [frases("+600", "CARROS", "*INTERMEDIADOS*", sub="pela nossa equipe."),
               frases("O NOME", "É NOVO."), frases("A EXPERIÊNCIA,", "*NÃO.*")],
     "legenda": leg("Mais de 600 carros já passaram pelas mãos da nossa equipe. 💪")},
    {"cenas": [frases("MITO", "OU", "*VERDADE?*", sub="Parte 3"),
               mito(1, "“Carro sujo vende pelo mesmo preço.”", False, "Sujeira vira argumento de desconto na hora da negociação."),
               mito(2, "“Histórico de revisões valoriza.”", True, "Notas e carimbos mostram que o carro foi bem cuidado."),
               mito(3, "“Recall pendente não faz diferença.”", False, "Recall em aberto assusta o comprador. Resolva antes de vender.")],
     "legenda": leg("Acertou todas? Conta aqui 👇")},
    {"cenas": [frases("*SEGURANÇA*", "DO INÍCIO", "AO FIM."), frases("*TRANSPARÊNCIA*", "EM CADA", "OFERTA."),
               frases("*AGILIDADE*", "SEM", "ENROLAÇÃO.")],
     "legenda": leg("Três palavras que vão guiar cada negociação. 💚")},
    {"cenas": [frases("ALGO NOVO", "ESTÁ", "*CHEGANDO.*"), frases("PORTO ALEGRE,", "*PREPARE-SE.*", sub="Ativa as notificações do perfil.")],
     "legenda": leg("Falta pouco. 👀")},
    {"cenas": [frases("O QUE O", "COMPRADOR", "*VÊ PRIMEIRO?*"),
               item("01", ["AS FOTOS."], "É ali que ele decide se chama você ou passa pro próximo."),
               item("02", ["O ESTADO."], "Pneus, bancos e painel contam a história do carro."),
               item("03", ["A PAPELADA."], "Documentação em dia passa confiança e acelera o negócio.")],
     "legenda": leg("Capricha nesses 3 e a negociação muda de nível. 💪")},
    {"cenas": [frases("E SE LOJISTAS", "E INVESTIDORES", "*DISPUTASSEM*", "O SEU HATCH?"),
               disputa([["Lojista 1", 41000], ["Investidor 1", 42200], ["Lojista 2", 43500], ["Investidor 2", 44800],
                        ["Lojista 3", 45600], ["Investidor 1", 46300]]),
               frases("QUEM DÁ MAIS,", "*LEVA.*")],
     "legenda": leg("Não importa o tamanho do carro: a disputa é pela melhor oferta. 👀", "(Valores do vídeo são um exemplo ilustrativo.)")},
    {"cenas": [frases("VENDER", "SOZINHO", "*CANSA.*"), riscar("FOTO,", "ANÚNCIO,"), riscar("MENSAGEM,", "VISITA,"),
               riscar("PECHINCHA,", "PAPELADA."), frases("A GENTE", "*RESOLVE.*", sub="Em breve em Porto Alegre.")],
     "legenda": leg("Quanto tempo você já perdeu tentando vender um carro? ⏳")},
    {"cenas": [frases("*MENOS*", "ENROLAÇÃO."), frases("*MAIS*", "NEGOCIAÇÃO."), frases("ESSE É O", "NOSSO *JEITO.*")],
     "legenda": leg("Simples assim. 💚")},
    {"cenas": [frases("QUAL CARRO", "VOCÊ QUER", "*VENDER?*"), frases("CONTA AQUI", "NOS *COMENTÁRIOS.*", sub="A gente quer conhecer você.")],
     "legenda": leg("Modelo e ano aqui embaixo 👇 Queremos saber quem vai estrear com a gente!")},
    {"cenas": [frases("DÚVIDA SOBRE", "*VENDER*", "SEU CARRO?"), frases("MANDA NO", "*DIRECT.*", sub="A gente responde tudo.")],
     "legenda": leg("Pergunta o que quiser no direct 📩")},
    {"cenas": [frases("SEU CARRO", "VALE MAIS", "DO QUE TE", "*OFERECERAM?*"),
               frases("TALVEZ", "*SIM.*", sub="Com mais compradores disputando, a oferta pode melhorar.")],
     "legenda": leg("Já sentiu que a proposta pelo seu carro foi baixa demais? 👇")},
    {"cenas": [frases("FALTA", "*POUCO.*"), frases("E SE AS", "OFERTAS", "VIESSEM ATÉ", "*VOCÊ?*")],
     "legenda": leg("Ativa as notificações pra não perder a novidade 🔔")},
]

BOM_DIA = [
    "Metade da semana já foi. E a gente está cada vez mais perto.",
    "Quem tem carro pra vender, guarda esse nome: Pronto Vendi.",
    "Sexta é dia de fechar a semana com tudo. Por aqui, tem novidade chegando.",
    "Bom sábado! Aproveita o carro, o sol e a família.",
    "Domingo é dia de descanso. Semana que vem tem mais novidade por aqui.",
    "Semana nova, planos novos. O nosso está quase pronto.",
    "Terça é dia de colocar os planos em movimento. O nosso já está andando.",
    "Quarta-feira, café na mão e foco. A novidade está chegando.",
    "Quinta é quase sexta. E a gente está quase pronto.",
    "Sextou! Bom fim de semana. Na próxima, tem mais por aqui.",
    "Bom sábado! Já pensou no que faria com o dinheiro da venda do seu carro?",
    "Bom domingo! Descansa, que a gente segue trabalhando na novidade.",
    "Último dia de novembro. Dezembro chega com novidade em Porto Alegre.",
    "Dezembro chegou. E com ele, um novo jeito de vender carro em Porto Alegre.",
]

PERGUNTAS = [
    ("CONTA PRA GENTE", "Qual foi a *pior proposta* que já te fizeram pelo seu carro?"),
    ("SINCERIDADE", "O que mais te *irrita* na hora de vender carro?"),
    ("CONTA PRA GENTE", "Qual seu *maior medo* ao vender o carro?"),
    ("RESPONDE AÍ", "Você confia na *tabela Fipe* na hora de vender?"),
    ("QUEREMOS SABER", "Qual *carro* você tem hoje?"),
    ("SINCERIDADE", "Prefere vender *sozinho* ou com ajuda?"),
    ("CONTA PRA GENTE", "Já levou *bolo* de comprador?"),
    ("RESPONDE AÍ", "Venderia seu carro para quem desse o *maior lance*?"),
    ("QUEREMOS SABER", "O que você faria com o *dinheiro* da venda?"),
    ("CONFESSA AÍ", "Seu carro está com a *revisão* em dia?"),
    ("CONTA PRA GENTE", "Qual sua maior *dúvida* sobre vender carro?"),
    ("RESPONDE AÍ", "Você já vendeu carro para uma *loja*?"),
    ("QUEREMOS SABER", "O que você *espera* da Pronto Vendi?"),
    ("CONTA PRA GENTE", "Qual carro você *quer vender* primeiro com a gente?"),
]


def montar(inicio: date) -> dict:
    dias = {}
    for i in range(len(BOM_DIA)):
        d = inicio + timedelta(days=i)
        topo, titulo = PERGUNTAS[i]
        dias[d.isoformat()] = {
            "bom_dia": {"modelo": "saudacao", "titulo": "Bom dia, *Porto Alegre.*", "texto": BOM_DIA[i]},
            "reel_meio_dia": REELS[2 * i],
            "story_tarde": {"modelo": "pergunta", "topo": topo, "titulo": titulo, "cta": "Responde no direct"},
            "reel_tarde": REELS[2 * i + 1],
        }
    return {"_leia": "Gerado por conteudo/montar_calendario.py. Edite lá e rode o script de novo.", "dias": dias}


if __name__ == "__main__":
    assert len(REELS) >= 2 * len(BOM_DIA), (len(REELS), len(BOM_DIA))
    destino = Path(__file__).with_name("calendario.json")
    destino.write_text(json.dumps(montar(date(2026, 11, 18)), ensure_ascii=False, indent=1), encoding="utf-8")
    print("ok:", destino)
