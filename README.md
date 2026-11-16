# Agente de IA para Instagram — Pronto Vendi

Agente feito com Claude que **analisa o seu Instagram**, **cria artes** e **publica no feed**.

O que ele faz:
- **Analisa**: lê o perfil, os posts recentes e as métricas (alcance, salvamentos, compartilhamentos, curtidas e comentários). Também olha as imagens dos posts para entender o seu estilo visual.
- **Cria artes**: gera imagens 1080x1350 (feed), 1080x1080 ou 1080x1920 (story) nas cores da marca, em 4 modelos: `destaque`, `oferta`, `lista` e `citacao`. Ele confere cada arte e refaz se ficar ruim.
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

Para usar as fontes da sua marca, coloque `Bold.ttf` e `Regular.ttf` numa pasta `fontes/`.

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
Você: analise meu perfil e me diga o que está funcionando
Você: crie 3 artes para a Black Friday seguindo o estilo dos meus melhores posts
Você: publique a segunda com uma legenda chamando para o direct
```

Um pedido direto:
```bash
python -m agente "analise meus últimos 20 posts, crie uma arte no formato que mais engaja e publique"
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
  hospedagem.py   # envia a arte para uma URL pública (imgbb)
  config.py       # leitura do .env
```

## Limites da API do Instagram
- Até 100 publicações por conta a cada 24 horas.
- Apenas JPEG na publicação de imagem (o agente já gera JPEG).
- Métricas por post só existem para contas profissionais. Algumas métricas não aparecem para posts antigos ou para certos tipos de mídia, e o agente segue com o que estiver disponível.
