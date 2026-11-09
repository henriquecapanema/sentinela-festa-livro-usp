"""Cliente mínimo da API da Festa do Livro da USP (só biblioteca padrão).

Endpoints descobertos inspecionando o site (festadolivro.edusp.com.br):
  /api/v1/event-publishers?page=N&flag=<edicao>&filter=
  /api/v1/event-books?flag=<edicao>&page=N&column=name&order=asc&per_page=100
        filtros opcionais: name, author_name, isbn, subject, publisher_name
"""
import json
import os
import time
import urllib.parse
import urllib.request

BASE = "https://festadolivro.edusp.com.br/api/v1"
FLAG = os.environ.get("FESTA_FLAG", "28-festa-do-livro-da-usp")
UA = "festa-usp-monitor/1.0 (projeto pessoal; poucas requisicoes por dia)"


def get_json(path, **params):
    url = f"{BASE}/{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    for tentativa in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception:
            if tentativa == 2:
                raise
            time.sleep(5 * (tentativa + 1))


def _paginar(path, pausa=0.5, **params):
    page = 1
    while True:
        j = get_json(path, page=page, **params)
        yield from j.get("data", [])
        meta = j.get("meta") or {}
        if page >= int(meta.get("last_page") or 1):
            break
        page += 1
        time.sleep(pausa)  # educação com o servidor da Edusp


def editoras(flag=FLAG):
    return list(_paginar("event-publishers", flag=flag, filter=""))


def total_livros(flag=FLAG):
    j = get_json("event-books", flag=flag, page=1, column="name", order="asc", per_page=1)
    return int((j.get("meta") or {}).get("total") or 0)


def buscar_livros(flag=FLAG, max_paginas=5, **filtro):
    """filtro: name=, author_name=, isbn=, subject=, publisher_name="""
    out = []
    for i, livro in enumerate(_paginar("event-books", flag=flag, column="name",
                                       order="asc", per_page=100, **filtro)):
        out.append({k: (v.strip() if isinstance(v, str) else v) for k, v in livro.items()})
        if len(out) >= max_paginas * 100:
            break
    return out
