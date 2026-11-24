"""Avisa no Telegram quando uma lista feita à mão (`livros-pdf/*.csv`) entra ou muda.

O `monitor.py` só avisa do que muda na API da Edusp; o que é posto à mão em
`livros-pdf/` passava em silêncio. Roda pelo workflow `avisar-manual.yml` a cada
push que mexe em `livros-pdf/` na main (ou à mão, com um commit base).

Uso: python avisar_manual.py <commit-base> [<commit-novo>]   (novo padrão: HEAD)
Mesmas variáveis do monitor: TELEGRAM_TOKEN + TELEGRAM_CHAT_ID; sem elas, só imprime.
"""
import csv
import io
import json
import pathlib
import subprocess
import sys

import indice
from monitor import notificar

AQUI = pathlib.Path(__file__).parent
PASTA = "livros-pdf"
PAGINA = "https://henriquecapanema.github.io/sentinela-festa-livro-usp/"


def _git(*args):
    r = subprocess.run(["git", *args], cwd=AQUI, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def contar(commit, caminho):
    """Nº de livros do CSV naquele commit, ou None se o arquivo não existia."""
    txt = _git("show", f"{commit}:{caminho}")
    if txt is None:
        return None
    return sum(1 for _ in csv.DictReader(io.StringIO(txt)))


def nome(slug):
    estado = json.loads((AQUI / "estado.json").read_text(encoding="utf-8"))
    meta = (estado.get("editoras") or {}).get(slug) or {}
    return meta.get("name") or indice.NOMES_EXTRA.get(slug) or slug.replace("-", " ")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    base, novo = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "HEAD")
    mudados = _git("diff", "--name-only", base, novo, "--", PASTA)
    if mudados is None:
        sys.exit(f"não deu pra comparar {base}..{novo} (commit base existe neste clone?)")

    linhas = []
    for caminho in sorted(p for p in mudados.split() if p.endswith(".csv")):
        slug = pathlib.Path(caminho).stem
        antes, depois = contar(base, caminho), contar(novo, caminho)
        if depois is None:
            linhas.append(f"• {nome(slug)}: lista removida")
        elif antes is None:
            linhas.append(f"• {nome(slug)}: {depois} livros (lista nova)")
        elif antes != depois:
            linhas.append(f"• {nome(slug)}: {antes} → {depois} livros")
        else:
            linhas.append(f"• {nome(slug)}: lista corrigida ({depois} livros)")

    if not linhas:
        print("Nada mudou em livros-pdf/.")
        return
    msg = "\n".join(["📖 Listas fora do site da festa (adicionadas à mão):", *linhas, "",
                     f"🔎 Buscar nos livros: {PAGINA}"])
    notificar(f"Festa do Livro USP: {len(linhas)} lista(s) nova(s) ou atualizada(s)", msg)


if __name__ == "__main__":
    main()
