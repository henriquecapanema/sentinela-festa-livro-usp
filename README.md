# festa-usp

Monitor da Festa do Livro da USP (28ª edição): checa 5x por dia se apareceu editora nova ou catálogo novo e manda notificação no celular.

Usa a API JSON que o próprio site usa (`/api/v1/event-publishers` e `/api/v1/event-books`). Só biblioteca padrão do Python, nada pra instalar.

## Rodar local

```bash
python monitor.py
```

A primeira execução salva o estado (`estado.json`) e avisa quantas editoras já existem; as seguintes só avisam quando muda algo. `editoras.md` fica sempre com a lista atual + links dos PDFs.

## Rodar sozinho (GitHub Actions, grátis)

1. Crie um repositório no GitHub e suba esta pasta (incluindo `.github/`).
2. Escolha como receber os avisos e adicione em **Settings → Secrets and variables → Actions**:
   - **ntfy** (mais fácil): invente um nome difícil de adivinhar, ex. `festa-usp-28-k9x2`, salve como `NTFY_TOPIC`, instale o app **ntfy** e assine esse tópico. Pra avisar os amigos ansiosos, é só passar o nome do tópico.
   - **Telegram**: crie um bot com o @BotFather → `TELEGRAM_TOKEN`; o id do chat/grupo → `TELEGRAM_CHAT_ID`.
3. Aba **Actions** → "Monitor Festa do Livro USP" → **Run workflow** pra testar.

Horários: 7:37, 10:37, 13:37, 16:37 e 19:37 (Brasília). O GitHub às vezes atrasa alguns minutos. Pra mudar, edite o `cron` em `.github/workflows/monitor.yml` (em UTC).

Pra próxima edição: troque `FESTA_FLAG` no workflow pra `29-festa-do-livro-da-usp`.
