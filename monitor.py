"""Checa a página de editoras da Festa do Livro da USP e avisa quando aparece
editora nova ou lista de preços (catálogo) nova/atualizada.

Notificações (configure por variável de ambiente, todas opcionais):
  NTFY_TOPIC                       -> push via ntfy.sh (app grátis, qualquer um pode assinar o tópico)
  TELEGRAM_TOKEN + TELEGRAM_CHAT_ID -> mensagem num chat/grupo/canal do Telegram
Sem nenhuma configurada, só imprime no terminal.
"""
import csv
import json
import os
import pathlib
import re
import sys
import unicodedata
import urllib.request
from datetime import datetime, timezone, timedelta

import festa

AQUI = pathlib.Path(__file__).parent
ESTADO = AQUI / "estado.json"
LISTA_MD = AQUI / "editoras.md"
LIVROS_DIR = AQUI / "livros"   # um CSV por editora: livros/<slug>.csv
COLUNAS_CSV = [("titulo", "name"), ("autor", "authors"),
               ("isbn", "isbn"), ("assunto", "subject"), ("preco", "price"),
               ("preco_feira", "price_discount"), ("link", "link")]
SITE = f"https://festadolivro.edusp.com.br/{festa.FLAG}/editoras"
# no Actions o GitHub preenche GITHUB_REPOSITORY; o padrão vale pra rodar local
REPO = os.environ.get("GITHUB_REPOSITORY") or "henriquecapanema/sentinela-festa-livro-usp"
LISTA_URL = f"https://github.com/{REPO}/blob/main/editoras.md"
RODAPE = f"📋 Lista atualizada (editoras, PDFs e livros): {LISTA_URL}\n🌐 Site da festa: {SITE}"
BRT = timezone(timedelta(hours=-3))


def carregar_estado():
    if ESTADO.exists():
        return json.loads(ESTADO.read_text(encoding="utf-8"))
    return None


def comparar(antes, editoras):
    novas, catalogo_novo, catalogo_atualizado = [], [], []
    anteriores = (antes or {}).get("editoras", {})
    for e in editoras:
        slug, pl = e["url"], e.get("price_list") or ""
        if slug not in anteriores:
            novas.append(e)
        elif pl and not anteriores[slug].get("price_list"):
            catalogo_novo.append(e)
        elif pl and pl != anteriores[slug].get("price_list"):
            catalogo_atualizado.append(e)
    return novas, catalogo_novo, catalogo_atualizado


def comparar_busca(antes, depois, editoras):
    """Editoras cujos livros entraram na busca ou mudaram de quantidade.
    antes/depois: {slug: nº de livros}. Devolve [(nome, n_antes ou None, n_depois)]."""
    nome_de = {e["url"]: e["name"] for e in editoras}
    out = []
    for slug, n in sorted(depois.items(), key=lambda kv: nome_de.get(kv[0], kv[0]).lower()):
        if antes.get(slug) != n:
            out.append((nome_de.get(slug, slug), antes.get(slug), n))
    return out


def montar_mensagem(novas, cat_novo, cat_atual, busca, total, total_antes):
    linhas = []

    def bloco(titulo, lista):
        if lista:
            linhas.append(titulo)
            for e in lista:
                pdf = e.get("price_list")
                linhas.append(f"• {e['name']}" + (f" — {pdf}" if pdf else " (sem catálogo ainda)"))
            linhas.append("")

    bloco(f"🆕 {len(novas)} editora(s) nova(s):", novas)
    bloco(f"📄 {len(cat_novo)} catálogo(s) publicado(s):", cat_novo)
    bloco(f"🔄 {len(cat_atual)} catálogo(s) atualizado(s):", cat_atual)
    if busca:
        linhas.append("📖 Livros cadastrados no site (pesquisáveis por título/autor):")
        for nome, n_antes, n in busca:
            linhas.append(f"• {nome}: {n} livros (primeira vez no site)" if not n_antes
                          else f"• {nome}: {n_antes} → {n} livros")
        linhas.append("")
    if total_antes is not None and total != total_antes:
        linhas.append(f"📚 Total de livros cadastrados no site: {total_antes} → {total}")
    if linhas and linhas[-1]:
        linhas.append("")
    linhas.append(RODAPE)
    return "\n".join(linhas).strip()


def notificar(titulo, msg):
    print(f"== {titulo} ==\n{msg}\n")
    topic = os.environ.get("NTFY_TOPIC")
    if topic:
        corpo = json.dumps({"topic": topic, "title": titulo, "message": msg[:3900],
                            "click": SITE, "tags": ["books"]}).encode()
        req = urllib.request.Request("https://ntfy.sh/", data=corpo,
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=20).read()
    token, chat = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if token and chat:
        corpo = json.dumps({"chat_id": chat, "text": f"{titulo}\n\n{msg}"[:4000],
                            "disable_web_page_preview": True}).encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage",
                                     data=corpo, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=20).read()


def escrever_lista(editoras, total, agora):
    com = sum(1 for e in editoras if e.get("price_list"))
    linhas = [f"# Editoras — {festa.FLAG}", "",
              f"Atualizado em {agora:%d/%m/%Y %H:%M} (horário de Brasília). "
              f"{len(editoras)} editoras, {com} com catálogo, {total} livros cadastrados no site.", "",
              "| Editora | Catálogo | Livros cadastrados no site |", "|---|---|---|"]
    qtd = livros_por_arquivo()
    for e in sorted(editoras, key=lambda e: e["name"].lower()):
        pdf = e.get("price_list")
        n = qtd.get(e["url"])
        livros = f"[{n}](livros/{e['url']}.csv)" if n else "—"
        linhas.append(f"| {e['name']} | {'[PDF](' + pdf + ')' if pdf else '—'} | {livros} |")
    LISTA_MD.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def slugify(nome):
    s = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-") or "sem-editora"


def livros_por_arquivo():
    """{slug: nº de livros} lendo os CSVs que já estão em livros/."""
    out = {}
    for p in sorted(LIVROS_DIR.glob("*.csv")):
        with p.open(encoding="utf-8", newline="") as f:
            out[p.stem] = sum(1 for _ in csv.reader(f)) - 1  # menos o cabeçalho
    return out


def salvar_livros(editoras, total):
    """Baixa a busca inteira da API e grava um CSV por editora em livros/.
    Só baixa quando o total de livros mudou, pra não martelar a API 5x por dia."""
    if sum(livros_por_arquivo().values()) == total:
        return
    slug_de = {e["name"].strip().lower(): e["url"] for e in editoras}
    grupos = {}
    for b in festa.buscar_livros(max_paginas=10_000):
        nome = (b.get("publisher") or "").strip()
        slug = slug_de.get(nome.lower()) or slugify(nome)
        grupos.setdefault(slug, []).append(b)

    LIVROS_DIR.mkdir(exist_ok=True)
    for p in LIVROS_DIR.glob("*.csv"):
        if p.stem not in grupos:
            p.unlink()  # editora que sumiu da busca
    for slug, livros in grupos.items():
        livros.sort(key=lambda b: ((b.get("name") or "").lower(), b.get("isbn") or ""))
        with (LIVROS_DIR / f"{slug}.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow([col for col, _ in COLUNAS_CSV])
            for b in livros:
                w.writerow([b.get(campo) or "" for _, campo in COLUNAS_CSV])
    print(f"livros/: {sum(map(len, grupos.values()))} livros em {len(grupos)} arquivos.")


def main():
    agora = datetime.now(BRT)
    antes = carregar_estado()
    eds = festa.editoras()
    total = festa.total_livros()

    novas, cat_novo, cat_atual = comparar(antes, eds)
    primeira_vez = antes is None

    qtd_antes = livros_por_arquivo()
    salvar_livros(eds, total)
    busca = comparar_busca(qtd_antes, livros_por_arquivo(), eds)

    if primeira_vez:
        com = sum(1 for e in eds if e.get("price_list"))
        notificar("Festa do Livro USP: monitor ligado",
                  f"Já tem {len(eds)} editoras ({com} com catálogo) e {total} livros cadastrados no site.\n\n{RODAPE}")
    elif novas or cat_novo or cat_atual or busca:
        n = len(novas) + len(cat_novo) + sum(1 for _, n_antes, _ in busca if not n_antes)
        if n:
            titulo = f"Festa do Livro USP: {n} novidade(s)"
        elif cat_atual:
            titulo = "Festa do Livro USP: catálogo atualizado"
        else:
            titulo = "Festa do Livro USP: livros novos no site"
        notificar(titulo, montar_mensagem(novas, cat_novo, cat_atual, busca, total,
                                          (antes or {}).get("total_livros")))
    else:
        print(f"{agora:%d/%m %H:%M} — nada novo ({len(eds)} editoras, {total} livros).")

    estado = {
        "flag": festa.FLAG,
        "checado_em": agora.isoformat(timespec="minutes"),
        "total_livros": total,
        "editoras": {e["url"]: {"name": e["name"], "price_list": e.get("price_list") or ""}
                     for e in eds},
    }
    ESTADO.write_text(json.dumps(estado, ensure_ascii=False, indent=1, sort_keys=True),
                      encoding="utf-8")
    escrever_lista(eds, total, agora)


if __name__ == "__main__":
    sys.exit(main())
