# sentinela-festa-livro-usp

Monitor da Festa do Livro da USP (28ª edição): checa 5x por dia se apareceu editora nova ou catálogo novo e avisa pelo bot do Telegram **@festausp2026bot**.

Usa a API JSON que o próprio site usa (`/api/v1/event-publishers` e `/api/v1/event-books`). Só biblioteca padrão do Python, nada pra instalar.

## O que fica no repositório

- `editoras.md` — lista atual de editoras, link do PDF de cada catálogo e quantos livros de cada uma já estão na busca do site.
- `livros/<editora>.csv` — os livros de cada editora que estão na busca do site (título, autor, ISBN, assunto, preço e preço na feira). Só é baixado de novo quando o total de livros muda. Nem toda editora com catálogo em PDF já aparece na busca; os arquivos vão surgindo conforme a Edusp inclui as editoras.
- `estado.json` — o que o monitor viu na última rodada, pra comparar com a próxima.

## Como roda

GitHub Actions (`.github/workflows/monitor.yml`), às 7:37, 10:37, 13:37, 16:37 e 19:37 (Brasília). O GitHub às vezes atrasa alguns minutos. Pra mudar, edite o `cron` (em UTC). Pra rodar na hora: aba **Actions** → "Monitor Festa do Livro USP" → **Run workflow**.

Os avisos vão pro Telegram pelo bot **@festausp2026bot**, configurado com os secrets `TELEGRAM_TOKEN` e `TELEGRAM_CHAT_ID`. Só chega mensagem quando aparece editora nova ou catálogo novo ou atualizado.

## Rodar local

```bash
python monitor.py
```

Sem as variáveis do Telegram, só imprime no terminal.

Pra próxima edição: troque `FESTA_FLAG` no workflow pra `29-festa-do-livro-da-usp`.
