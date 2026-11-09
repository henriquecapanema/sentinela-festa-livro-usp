"""Checa a página de editoras da Festa do Livro da USP e avisa quando aparece
editora nova ou lista de preços (catálogo) nova/atualizada.

Notificações (configure por variável de ambiente, todas opcionais):
  NTFY_TOPIC                       -> push via ntfy.sh (app grátis, qualquer um pode assinar o tópico)
  TELEGRAM_TOKEN + TELEGRAM_CHAT_ID -> mensagem num chat/grupo/canal do Telegram
Sem nenhuma configurada, só imprime no terminal.
"""
import json
import os
import pathlib
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

import festa

AQUI = pathlib.Path(__file__).parent
ESTADO = AQUI / "estado.json"
LISTA_MD = AQUI / "editoras.md"
SITE = f"https://festadolivro.edusp.com.br/{festa.FLAG}/editoras"
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


def montar_mensagem(novas, cat_novo, cat_atual, total, total_antes):
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
    if total_antes is not None and total != total_antes:
        linhas.append(f"📚 Livros na busca: {total_antes} → {total}")
    linhas.append(SITE)
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
              f"{len(editoras)} editoras, {com} com catálogo, {total} livros na busca.", "",
              "| Editora | Catálogo |", "|---|---|"]
    for e in sorted(editoras, key=lambda e: e["name"].lower()):
        pdf = e.get("price_list")
        linhas.append(f"| {e['name']} | {'[PDF](' + pdf + ')' if pdf else '—'} |")
    LISTA_MD.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def main():
    agora = datetime.now(BRT)
    antes = carregar_estado()
    eds = festa.editoras()
    total = festa.total_livros()

    novas, cat_novo, cat_atual = comparar(antes, eds)
    primeira_vez = antes is None

    if primeira_vez:
        com = sum(1 for e in eds if e.get("price_list"))
        notificar("Festa do Livro USP: monitor ligado",
                  f"Já tem {len(eds)} editoras ({com} com catálogo) e {total} livros na busca.\n{SITE}")
    elif novas or cat_novo or cat_atual:
        n = len(novas) + len(cat_novo)
        titulo = f"Festa do Livro USP: {n} novidade(s)" if n else "Festa do Livro USP: catálogo atualizado"
        notificar(titulo, montar_mensagem(novas, cat_novo, cat_atual, total,
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
