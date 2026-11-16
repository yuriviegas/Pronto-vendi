# Agente de IA para Instagram — Pronto Vendi

Agente feito com Claude que **analisa o seu Instagram**, **cria artes** e **publica no feed**.

O agente já conhece a Pronto Vendi: intermediação de veículos em Porto Alegre, "vendemos o seu carro em até 40 minutos", "menos enrolação, mais negociação" e +600 carros intermediados. Para mudar essas informações, edite o texto `SISTEMA` em `agente/__main__.py`.

O que ele faz:
- **Analisa**: lê o perfil, os posts recentes e as métricas (alcance, salvamentos, compartilhamentos, curtidas e comentários). Também olha as imagens dos posts para entender o seu estilo visual.
- **Cria artes** com a identidade da Pronto Vendi (preto, verde neon, logo e fonte Montserrat), em 1080x1350 (feed), 1080x1080 ou 1080x1920 (story). Ele confere cada arte e refaz se ficar ruim. Modelos:
  - `veiculo`: foto do carro, nome, ficha (ano, km), diferenciais, preço e carimbo opcional de **VENDIDO**
  - `destaque`: título forte + subtítulo (ex. "Vendemos o seu carro em até 40 minutos")
  - `oferta`: selo grande com um número (ex. "+600 carros intermediados")
  - `lista`: dicas ou passos numerados
  - `citacao`: depoimento de cliente com estrelas
- **Escreve a legenda**: gancho, chamada para ação e hashtags.
- **Publica**: posta no Instagram. Por padrão **pede a sua confirmação** antes de publicar.

## 1. Instalação

Requer Python 3.10 ou mais novo.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # depois preencha o .env
```

## 2. Configuração (`.env`)

| Variável | Para que serve |
|---|---|
| `ANTHROPIC_API_KEY` | Chave do Claude: [platform.claude.com](https://platform.claude.com/) → API Keys |
| `INSTAGRAM_ACCESS_TOKEN` | Token da API do Instagram (passo a passo abaixo) |
| `IMGBB_API_KEY` | Chave gratuita do [imgbb.com](https://api.imgbb.com/). O Instagram só publica imagens que estão numa URL pública, e o imgbb hospeda a arte para isso |
| `MARCA_*` | Nome e cores da marca usados nas artes |

A logo fica em `marca/logo.png` (versão com fundo transparente, gerada a partir de `marca/logo-original.jpg`). As fontes ficam em `fontes/` (Montserrat, licença livre OFL). Para trocar, substitua os arquivos mantendo os nomes.

### Fotos dos carros
Coloque as fotos dos veículos na pasta `fotos/` (ex. `civic-2019.jpg`) e peça ao agente:
```
Você: crie um post do carro da foto civic-2019.jpg: Civic EXL 2019, 45 mil km, automático, R$ 112.900
Você: faça a arte de vendido do civic-2019.jpg, vendemos em 35 minutos
```
O agente olha a foto para identificar o carro, mas **nunca inventa** ano, km ou preço: se faltar algum dado, ele pergunta.

### Como obter o token do Instagram

1. A conta do Instagram precisa ser **Profissional** (Empresa ou Criador de conteúdo). Isso se muda no app, em Configurações → Tipo de conta.
2. Em [developers.facebook.com](https://developers.facebook.com/), crie um app do tipo **Empresa** e adicione o produto **Instagram** → *API com login do Instagram*.
3. Adicione a sua conta como testadora e gere um token com as permissões:
   `instagram_business_basic`, `instagram_business_content_publish` e `instagram_business_manage_insights`.
4. Cole o token em `INSTAGRAM_ACCESS_TOKEN`. O token de longa duração vale 60 dias e precisa ser renovado.

> Se a sua conta está ligada a uma Página do Facebook e você usa a Graph API do Facebook, defina
> `INSTAGRAM_API_BASE=https://graph.facebook.com/v21.0` e `INSTAGRAM_USER_ID` com o ID da conta do Instagram.

## 3. Como usar

Modo conversa:
```bash
python -m agente
```
```
Você: analise meu perfil e monte um plano de conteúdo para as próximas 2 semanas
Você: crie um post explicando como funciona vender o carro com a gente
Você: publique com uma legenda chamando para agendar a avaliação
```

Um pedido direto:
```bash
python -m agente "crie um post de prova social com os +600 carros intermediados e publique"
```

Opções:
- `--simular`: faz tudo, mas **nunca publica** (bom para testar).
- `--auto`: publica **sem pedir confirmação**. Use só se confiar no agente ou para agendar.

As artes ficam salvas na pasta `saida/`.

### Publicar automaticamente todo dia (opcional)

Exemplo com `cron` (Linux/macOS), todo dia às 10h:
```
0 10 * * * cd /caminho/Pronto-vendi && .venv/bin/python -m agente --auto "Analise o perfil e publique um post novo sobre um tema que ainda não foi usado esta semana" >> agente.log 2>&1
```

## Estrutura

```
agente/
  __main__.py     # loop do agente (Claude + ferramentas) e linha de comando
  ferramentas.py  # ferramentas que o Claude usa: perfil, posts, métricas, imagens, criar_arte, publicar_post
  instagram.py    # cliente da API do Instagram
  artes.py        # gerador de artes (Pillow)
marca/            # logo
fontes/           # Montserrat
fotos/            # coloque aqui as fotos dos carros (não vão para o Git)
  hospedagem.py   # envia a arte para uma URL pública (imgbb)
  config.py       # leitura do .env
```

## Limites da API do Instagram
- Até 100 publicações por conta a cada 24 horas.
- Apenas JPEG na publicação de imagem (o agente já gera JPEG).
- Métricas por post só existem para contas profissionais. Algumas métricas não aparecem para posts antigos ou para certos tipos de mídia, e o agente segue com o que estiver disponível.
