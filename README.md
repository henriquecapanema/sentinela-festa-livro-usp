# sentinela-festa-livro-usp

Monitor da Festa do Livro da USP (28ª edição): checa 5x por dia se apareceu editora nova ou catálogo novo e avisa pelo bot do Telegram **@festausp2026bot**.

Usa a API JSON que o próprio site usa (`/api/v1/event-publishers` e `/api/v1/event-books`). Só biblioteca padrão do Python, nada pra instalar.

## O que fica no repositório

- `editoras.md` — lista atual de editoras, link do PDF de cada catálogo e quantos livros de cada uma já estão cadastrados no site da festa.
- `livros/<editora>.csv` — os livros de cada editora cadastrados no site da festa, aqueles que dá pra pesquisar por título/autor lá (título, autor, ISBN, assunto, preço e preço na feira). Só é baixado de novo quando o total de livros muda. O cadastro no site é separado do PDF: nem toda editora com catálogo em PDF já tem os livros cadastrados; os arquivos vão surgindo conforme a Edusp cadastra as planilhas.
- `livros-pdf/<editora>.csv` — extração única (feita à mão, fora do workflow) do catálogo em PDF de editoras que interessam mas ainda não tinham os livros cadastrados no site. Hoje: Autonomia Literária (155 livros, PDF de 09/11/2026). Não é atualizado sozinho; os ISBNs repetidos e os códigos `2675003102`–`2675003107` vêm assim no próprio PDF da editora.
- `estado.json` — o que o monitor viu na última rodada, pra comparar com a próxima.

## Como roda

GitHub Actions (`.github/workflows/monitor.yml`), às 7:37, 10:37, 13:37, 16:37 e 19:37 (Brasília). O GitHub às vezes atrasa alguns minutos. Pra mudar, edite o `cron` (em UTC). Pra rodar na hora: aba **Actions** → "Monitor Festa do Livro USP" → **Run workflow**.

O monitor roda até **29/11/2026** (`ULTIMO_DIA` no workflow). Na primeira rodada depois disso ele manda um aviso no Telegram e se desliga sozinho. Pra religar: aba **Actions** → **Enable workflow** (e ajuste `ULTIMO_DIA`).

Os avisos vão pro Telegram pelo bot **@festausp2026bot**, configurado com os secrets `TELEGRAM_TOKEN` e `TELEGRAM_CHAT_ID`. Só chega mensagem quando aparece editora nova, catálogo novo ou atualizado, ou quando livros de uma editora são cadastrados no site.

## Rodar local

```bash
python monitor.py
```

Sem as variáveis do Telegram, só imprime no terminal.

Pra próxima edição: troque `FESTA_FLAG` no workflow pra `29-festa-do-livro-da-usp`.
