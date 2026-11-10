# sentinela-festa-livro-usp

Monitor da Festa do Livro da USP (28ª edição): checa 5x por dia se apareceu editora nova ou catálogo novo e avisa pelo bot do Telegram **@festausp2026bot**.

**Página pública:** https://henriquecapanema.github.io/sentinela-festa-livro-usp/ — busca nos livros da festa por editora, título, autor, assunto ou ISBN, com o preço da feira, e uma lista pessoal (♡) com o total e a economia. A lista fica só no navegador de quem usa (localStorage): sem login, sem servidor. Dá pra cruzar com uma lista que a pessoa já tem (colar ISBNs ou o CSV do Goodreads/Skoob) e mandar a lista por link (`#lista=<isbn>,<isbn>`).

Usa a API JSON que o próprio site usa (`/api/v1/event-publishers` e `/api/v1/event-books`). Só biblioteca padrão do Python, nada pra instalar.

## O que fica no repositório

- `editoras.md` — lista atual de editoras, link do PDF de cada catálogo e quantos livros de cada uma já estão cadastrados no site da festa.
- `livros/<editora>.csv` — os livros de cada editora cadastrados no site da festa, aqueles que dá pra pesquisar por título/autor lá (título, autor, ISBN, assunto, preço e preço na feira). Só é baixado de novo quando o total de livros muda. O cadastro no site é separado do PDF: nem toda editora com catálogo em PDF já tem os livros cadastrados; os arquivos vão surgindo conforme a Edusp cadastra as planilhas.
- `livros-pdf/<editora>.csv` — extração única (feita à mão, fora do workflow) do catálogo em PDF de editoras que interessam mas ainda não tinham os livros cadastrados no site. Hoje: Autonomia Literária (155 livros, PDF de 09/11/2026). Não é atualizado sozinho. **No PDF da editora a coluna de ISBN vem deslocada** (o ISBN de cada linha é, em geral, o do livro vizinho; ex.: `9786587233949` aparece na linha de *E os fracos sofrem o que devem?*, mas é *Economia para a transformação social*). Por isso os ISBNs foram reatribuídos conferindo cada um na BrasilAPI pelo título (112 corrigidos, 15 já certos). Os 28 que não deu para confirmar, incluindo os códigos `2675003102`–`2675003107`, que não são ISBN, ficaram com o ISBN vazio: melhor sem ISBN do que com o de outro livro. Título, autor, preço e link de cada linha batem com o PDF.
- `indice.json` — índice pronto com tudo o que a página usa: editoras (nome, PDF, de onde vêm os livros) e todos os livros de `livros/` e `livros-pdf/` num arquivo só (quando a editora tem os dois, vale `livros/`), com o ISBN-13 já validado. Gerado por `indice.py` no fim de cada rodada do monitor (à mão: `python indice.py`, por exemplo depois de mexer em `livros-pdf/`). Formato descrito no topo do `indice.py`. Quem quiser os dados pode ler direto de `https://raw.githubusercontent.com/henriquecapanema/sentinela-festa-livro-usp/main/indice.json`: um pedido só, sem o limite de 60/h da API do GitHub.
- `site/` — a página pública (HTML, CSS e JS puros, sem build). Lê o `indice.json` do raw a cada visita, então os livros novos aparecem sem republicar; se o raw falhar, usa a cópia publicada junto, e sem rede, a última que carregou (bom pra usar no meio da festa).
- `estado.json` — o que o monitor viu na última rodada, pra comparar com a próxima.

## Como roda

GitHub Actions (`.github/workflows/monitor.yml`), às 7:37, 10:37, 13:37, 16:37 e 19:37 (Brasília). O `schedule` do próprio GitHub não disparava, então o horário vem do **Cron Trigger do Worker do biblionema** (`frontend/wrangler.jsonc` → `triggers.crons`, em UTC), que chama o `workflow_dispatch` pela API com o segredo `GH_DISPATCH_TOKEN` do Worker (token fine-grained, Actions: read and write, só neste repo). Pra mudar o horário, edite o cron lá. Pra rodar na hora: aba **Actions** → "Monitor Festa do Livro USP" → **Run workflow**.

O monitor roda até **29/11/2026** (`ULTIMO_DIA` no workflow). Na primeira rodada depois disso ele manda um aviso no Telegram e se desliga sozinho. Pra religar: aba **Actions** → **Enable workflow** (e ajuste `ULTIMO_DIA`).

Os avisos vão pro Telegram pelo bot **@festausp2026bot**, configurado com os secrets `TELEGRAM_TOKEN` e `TELEGRAM_CHAT_ID`. Só chega mensagem quando aparece editora nova, catálogo novo ou atualizado, ou quando livros de uma editora são cadastrados no site.

## Página (GitHub Pages)

`.github/workflows/pages.yml` publica `site/` + `indice.json` no GitHub Pages quando algo em `site/` muda na `main` (ou à mão: Actions → "Publicar página" → Run workflow). Os commits do monitor não republicam e nem precisam: a página busca o índice novo no raw. Pré-requisito, uma vez só: **Settings → Pages → Source: GitHub Actions**.

Testar local: `python indice.py && cp indice.json site/ && python -m http.server -d site` (o `site/indice.json` copiado é só pra teste, não commite).

## Rodar local

```bash
python monitor.py
```

Sem as variáveis do Telegram, só imprime no terminal.

Pra próxima edição: troque `FESTA_FLAG` no workflow pra `29-festa-do-livro-da-usp`.
