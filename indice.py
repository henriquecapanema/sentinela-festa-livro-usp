"""Gera `indice.json`: tudo o que a página pública precisa num arquivo só.

Junta `estado.json` (editoras e PDFs), `livros/*.csv` (cadastro do site da festa) e
`livros-pdf/*.csv` (extração manual do PDF). Quando a mesma editora tem os dois,
vale `livros/` (o site é a fonte viva). Assim quem lê não precisa listar arquivos
pela API do GitHub (limite de 60 pedidos/h por IP) nem baixar um CSV por editora.

Formato (o `versao` muda se o formato mudar):
  {
    "versao": 1, "flag": ..., "checado_em": ..., "total": <nº de livros>,
    "editoras": [{"slug", "nome", "pdf", "fonte": "site"|"pdf"|null, "livros": n}],
    "colunas": ["editora", "titulo", "autor", "isbn13", "isbn", "assunto", "preco", "preco_feira", "link"],
    "livros": [[<índice em editoras>, "titulo", ...], ...]
  }
`isbn13` só vem preenchido quando o código é um ISBN válido (10 convertido ou 13 com
dígito verificador certo); `isbn` é o código como está na planilha.

Roda sozinho no fim do `monitor.py`; à mão: `python indice.py`.
"""
import csv
import json
import pathlib
import re

AQUI = pathlib.Path(__file__).parent
SAIDA = AQUI / "indice.json"
FONTES = (("site", AQUI / "livros"), ("pdf", AQUI / "livros-pdf"))
COLUNAS = ["editora", "titulo", "autor", "isbn13", "isbn", "assunto", "preco", "preco_feira", "link"]


def _check13(doze):
    return (10 - sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(doze)) % 10) % 10


def isbn13(raw):
    """ISBN-10/13 com ou sem hífen → ISBN-13, ou '' se não for um ISBN válido."""
    s = re.sub(r"[^0-9Xx]", "", raw or "").upper()
    if len(s) == 13 and s.isdigit() and s[:3] in ("978", "979") and _check13(s[:12]) == int(s[12]):
        return s
    if len(s) == 10 and s[:9].isdigit() and (s[9].isdigit() or s[9] == "X"):
        soma = sum((10 if c == "X" else int(c)) * (10 - i) for i, c in enumerate(s))
        if soma % 11 == 0:
            corpo = "978" + s[:9]
            return corpo + str(_check13(corpo))
    return ""


def _ler(p):
    with p.open(encoding="utf-8", newline="") as f:
        return [{k: (v or "").strip() for k, v in r.items()} for r in csv.DictReader(f)]


def gerar():
    estado = json.loads((AQUI / "estado.json").read_text(encoding="utf-8"))
    meta = estado.get("editoras") or {}

    por_slug = {}  # slug -> (fonte, linhas); "site" ganha de "pdf"
    for fonte, pasta in FONTES:
        for p in sorted(pasta.glob("*.csv")):
            linhas = _ler(p)
            if linhas and (p.stem not in por_slug or por_slug[p.stem][0] == "pdf" and fonte == "site"):
                por_slug[p.stem] = (fonte, linhas)

    def nome(slug):
        return (meta.get(slug) or {}).get("name") or slug.replace("-", " ")

    slugs = sorted(set(meta) | set(por_slug),
                   key=lambda s: (s not in por_slug, nome(s).casefold()))
    editoras, livros = [], []
    for i, slug in enumerate(slugs):
        fonte, linhas = por_slug.get(slug, (None, []))
        editoras.append({"slug": slug, "nome": nome(slug),
                         "pdf": (meta.get(slug) or {}).get("price_list") or "",
                         "fonte": fonte, "livros": len(linhas)})
        for r in linhas:
            livros.append([i, r.get("titulo", ""), r.get("autor", ""), isbn13(r.get("isbn")),
                           r.get("isbn", ""), r.get("assunto", ""), r.get("preco", ""),
                           r.get("preco_feira", ""), r.get("link", "")])

    indice = {"versao": 1, "flag": estado.get("flag"), "checado_em": estado.get("checado_em"),
              "total": len(livros), "editoras": editoras, "colunas": COLUNAS, "livros": livros}
    # uma linha por livro: diff legível no git sem inflar o arquivo
    corpo = ",\n".join(json.dumps(l, ensure_ascii=False, separators=(",", ":")) for l in livros)
    cabeca = json.dumps({k: v for k, v in indice.items() if k != "livros"},
                        ensure_ascii=False, separators=(",", ":"))[:-1]
    SAIDA.write_text(f'{cabeca},"livros":[\n{corpo}\n]}}\n', encoding="utf-8")
    json.loads(SAIDA.read_text(encoding="utf-8"))  # confere que saiu JSON válido
    print(f"indice.json: {len(livros)} livros, {len(editoras)} editoras.")
    return indice


if __name__ == "__main__":
    gerar()
