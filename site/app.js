/* Festa do Livro da USP — busca no catálogo e lista pessoal (guardada no navegador).
 * Lê indice.json (gerado pelo indice.py a cada rodada do monitor) direto do repo:
 * raw.githubusercontent.com não tem o limite da API do GitHub e libera CORS.
 * Se falhar, usa a cópia publicada junto com a página e, sem rede, a última que deu certo. */
'use strict'

const REPO = 'henriquecapanema/sentinela-festa-livro-usp'
const FONTES = [`https://raw.githubusercontent.com/${REPO}/main/indice.json`, 'indice.json']
const K_LISTA = 'festa-usp:lista'
const K_CACHE = 'festa-usp:indice'
const K_ABA = 'festa-usp:aba'
const PAGINA = 80

const $ = (id) => document.getElementById(id)
const store = {
  get(k) { try { return localStorage.getItem(k) } catch { return null } },
  set(k, v) { try { localStorage.setItem(k, v); return true } catch { return false } },
  del(k) { try { localStorage.removeItem(k) } catch { /* sem storage */ } },
}

/* ---------- utilidades ---------- */

const norm = (s) => (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim()
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c])
const collator = new Intl.Collator('pt-BR', { sensitivity: 'base' })

function check13(doze) {
  let soma = 0
  for (let i = 0; i < 12; i++) soma += Number(doze[i]) * (i % 2 === 0 ? 1 : 3)
  return (10 - (soma % 10)) % 10
}
/** ISBN-10/13 com ou sem hífen → ISBN-13, ou '' se não for ISBN válido (igual ao indice.py). */
function isbn13(raw) {
  const s = String(raw || '').replace(/[^0-9Xx]/g, '').toUpperCase()
  if (s.length === 13 && /^97[89]\d{10}$/.test(s) && check13(s) === Number(s[12])) return s
  if (s.length === 10 && /^\d{9}[\dX]$/.test(s)) {
    let soma = 0
    for (let i = 0; i < 10; i++) soma += (s[i] === 'X' ? 10 : Number(s[i])) * (10 - i)
    if (soma % 11 === 0) { const c = '978' + s.slice(0, 9); return c + check13(c) }
  }
  return ''
}

/** "R$ 1.234,56" → 1234.56; vazio ou ilegível → null */
function parseBRL(v) {
  const m = String(v || '').replace(/[^\d,.]/g, '').match(/\d[\d.]*(,\d+)?/)
  if (!m) return null
  const n = Number(m[0].replace(/\./g, '').replace(',', '.'))
  return Number.isFinite(n) ? n : null
}
const brl = (n) => n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })

function quando(iso) {
  const d = new Date(iso || '')
  if (Number.isNaN(d.getTime())) return iso || ''
  return `${d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', timeZone: 'America/Sao_Paulo' })} às ${d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', timeZone: 'America/Sao_Paulo' })}`
}

let toastT
function toast(msg) {
  const t = $('toast')
  t.textContent = msg
  t.classList.add('on')
  clearTimeout(toastT)
  toastT = setTimeout(() => t.classList.remove('on'), 2200)
}

/* ---------- dados ---------- */

let D = null          // { editoras, livros, checado_em, ... } com livros já como objetos
let porChave = new Map()
let porIsbn = new Map()

const chave = (b) => b.isbn13 || `${b.slug}|${norm(b.titulo)}`

function preparar(j) {
  if (!j || j.versao !== 1 || !Array.isArray(j.livros)) throw new Error('índice em formato desconhecido')
  const col = Object.fromEntries(j.colunas.map((c, i) => [c, i]))
  const livros = j.livros.map((r) => {
    const ed = j.editoras[r[col.editora]] || {}
    const b = {
      slug: ed.slug, editora: ed.nome, titulo: r[col.titulo], autor: r[col.autor],
      isbn13: r[col.isbn13], isbn: r[col.isbn], assunto: r[col.assunto],
      preco: r[col.preco], feira: r[col.preco_feira], link: r[col.link],
    }
    b.k = chave(b)
    b.busca = norm(`${b.titulo} ${b.autor} ${b.assunto} ${b.isbn} ${b.isbn13} ${b.editora}`)
    return b
  })
  livros.sort((a, b) => collator.compare(a.titulo, b.titulo))
  return { ...j, livros }
}

function usar(j) {
  D = preparar(j)
  porChave = new Map()
  porIsbn = new Map()
  for (const b of D.livros) {
    if (!porChave.has(b.k)) porChave.set(b.k, b)
    if (b.isbn13 && !porIsbn.has(b.isbn13)) porIsbn.set(b.isbn13, b)
  }
  const com = D.editoras.filter((e) => e.livros).length
  $('status').textContent = `${D.total.toLocaleString('pt-BR')} livros de ${com} editoras · atualizado em ${quando(D.checado_em)}`
  montarEditoras()
  buscar()
  desenharLista()
  abrirLinkCompartilhado()
}

async function carregar() {
  const cache = store.get(K_CACHE)
  if (cache) { try { usar(JSON.parse(cache)) } catch { store.del(K_CACHE) } }
  for (const url of FONTES) {
    try {
      const r = await fetch(url, { cache: 'no-cache' })
      if (!r.ok) throw new Error(String(r.status))
      const txt = await r.text()
      const j = JSON.parse(txt)
      if (D && D.checado_em === j.checado_em && D.total === j.total) return
      usar(j)
      store.set(K_CACHE, txt)
      return
    } catch { /* tenta a próxima fonte */ }
  }
  if (!D) $('status').textContent = 'Não deu para carregar o catálogo. Confira a internet e recarregue a página.'
  else $('status').textContent += ' (sem rede: mostrando a última cópia)'
}

/* ---------- minha lista ---------- */

// guarda uma cópia do livro: se ele sumir do catálogo, continua na lista
let lista = (() => { try { return JSON.parse(store.get(K_LISTA) || '[]') } catch { return [] } })()
let listaSet = new Set(lista.map((x) => x.k))

function salvarLista() {
  listaSet = new Set(lista.map((x) => x.k))
  if (!store.set(K_LISTA, JSON.stringify(lista))) toast('Este navegador não deixa guardar a lista')
  const n = $('lista-n')
  n.hidden = !lista.length
  n.textContent = lista.length
}

const snapshot = (b) => ({ k: b.k, slug: b.slug, editora: b.editora, titulo: b.titulo, autor: b.autor, isbn13: b.isbn13, isbn: b.isbn, assunto: b.assunto, preco: b.preco, feira: b.feira, link: b.link })

function alternar(k) {
  if (listaSet.has(k)) {
    lista = lista.filter((x) => x.k !== k)
    toast('Tirado da lista')
  } else {
    const b = porChave.get(k)
    if (!b) return
    lista.push(snapshot(b))
    toast('Na sua lista ♥')
  }
  salvarLista()
  document.querySelectorAll(`.heart[data-k="${CSS.escape(k)}"]`).forEach((h) => marcar(h, listaSet.has(k)))
  if (!$('pane-lista').hidden) desenharLista()
}

function adicionar(livros) {
  let novos = 0
  for (const b of livros) if (!listaSet.has(b.k)) { lista.push(snapshot(b)); listaSet.add(b.k); novos++ }
  salvarLista()
  return novos
}

/* ---------- desenho ---------- */

function marcar(h, on) {
  h.setAttribute('aria-pressed', on)
  h.textContent = on ? '♥' : '♡'
  h.title = on ? 'Tirar da lista' : 'Pôr na minha lista'
}

function linha(b, { comEditora = true } = {}) {
  const on = listaSet.has(b.k)
  const preco = b.feira || b.preco
  const precoHtml = preco ? `<span class="price">${esc(preco)}${b.feira && b.preco && b.preco !== b.feira ? `<s>${esc(b.preco)}</s>` : ''}</span>` : ''
  const autor = [b.autor, comEditora ? b.editora : ''].filter(Boolean).join(' · ')
  const corpo = `<div class="info"><h3>${esc(b.titulo || '—')}</h3><div class="author">${esc(autor || '—')}</div>` +
    `<div class="meta">${b.assunto ? `<span>${esc(b.assunto)}</span>` : ''}${b.isbn13 || b.isbn ? `<span class="isbn">${esc(b.isbn13 || b.isbn)}</span>` : ''}</div></div>${precoHtml}`
  const main = b.link
    ? `<a class="main" href="${esc(b.link)}" target="_blank" rel="noreferrer">${corpo}</a>`
    : `<div class="main">${corpo}</div>`
  return `<div class="row">${main}<button class="heart" data-k="${esc(b.k)}" aria-pressed="${on}" title="${on ? 'Tirar da lista' : 'Pôr na minha lista'}" aria-label="${esc(b.titulo)}: lista">${on ? '♥' : '♡'}</button></div>`
}

function montarEditoras() {
  const sel = $('editora')
  const atual = sel.value
  const com = D.editoras.filter((e) => e.livros).sort((a, b) => collator.compare(a.nome, b.nome))
  const pdf = D.editoras.filter((e) => !e.livros && e.pdf).sort((a, b) => collator.compare(a.nome, b.nome))
  sel.innerHTML = `<option value="">Todas as editoras · ${D.total.toLocaleString('pt-BR')}</option>` +
    `<optgroup label="Com lista de livros">${com.map((e) => `<option value="${esc(e.slug)}">${esc(e.nome)} · ${e.livros}</option>`).join('')}</optgroup>` +
    (pdf.length ? `<optgroup label="Só catálogo em PDF">${pdf.map((e) => `<option value="${esc(e.slug)}">${esc(e.nome)} (PDF)</option>`).join('')}</optgroup>` : '')
  if ([...sel.options].some((o) => o.value === atual)) sel.value = atual
}

let resultados = []
let limite = PAGINA

function buscar() {
  if (!D) return
  const slug = $('editora').value
  const ed = D.editoras.find((e) => e.slug === slug)
  const info = $('ed-info')
  if (ed) {
    info.hidden = false
    info.innerHTML = ed.livros
      ? (ed.pdf ? `<a href="${esc(ed.pdf)}" target="_blank" rel="noreferrer">catálogo da ${esc(ed.nome)} em PDF</a>` : '') +
        (ed.fonte === 'pdf' ? ' · lista tirada do PDF (alguns livros estão sem ISBN)' : '')
      : `A ${esc(ed.nome)} ainda não cadastrou os livros no site da festa. ` +
        (ed.pdf ? `<a href="${esc(ed.pdf)}" target="_blank" rel="noreferrer">Ver o catálogo em PDF</a>.` : '')
    if (!info.innerHTML) info.hidden = true
  } else info.hidden = true

  const q = $('q').value
  const isbnQ = isbn13(q)
  const termos = norm(q).split(/\s+/).filter(Boolean)
  resultados = D.livros.filter((b) => (!slug || b.slug === slug) &&
    (isbnQ ? b.isbn13 === isbnQ : termos.every((t) => b.busca.includes(t))))
  limite = PAGINA
  desenharResultados()
}

function desenharResultados() {
  const n = resultados.length
  $('contagem').textContent = n ? `${n.toLocaleString('pt-BR')} livro${n > 1 ? 's' : ''}` : ($('q').value ? 'Nada encontrado.' : '')
  const comEditora = !$('editora').value
  $('resultados').innerHTML = resultados.slice(0, limite).map((b) => linha(b, { comEditora })).join('')
  $('mais').hidden = n <= limite
}

let filtroLista = ''

function desenharLista() {
  // preço e link vêm do catálogo atual quando o livro ainda está nele
  const itens = lista.map((x) => (porChave.get(x.k) || x))
  const eds = new Map()
  for (const b of itens) eds.set(b.slug, { nome: b.editora, n: (eds.get(b.slug)?.n || 0) + 1 })
  if (!eds.has(filtroLista)) filtroLista = ''
  const ordem = [...eds].sort((a, b) => collator.compare(a[1].nome, b[1].nome))
  const chip = (slug, nome, n) =>
    `<button class="chip" data-slug="${esc(slug)}" aria-pressed="${slug === filtroLista}">${esc(nome)}<span class="n">${n}</span></button>`
  const chips = $('lista-ed')
  chips.innerHTML = chip('', 'Todas', itens.length) + ordem.map(([s, e]) => chip(s, e.nome, e.n)).join('')
  chips.hidden = eds.size < 2

  const mostrar = itens
    .filter((b) => !filtroLista || b.slug === filtroLista)
    .sort((a, b) => collator.compare(a.editora, b.editora) || collator.compare(a.titulo, b.titulo))

  let html = ''
  let grupo = null
  for (const b of mostrar) {
    if (b.editora !== grupo) { grupo = b.editora; html += `<h2 class="group">${esc(grupo)}</h2>` }
    html += linha(b, { comEditora: false })
  }
  $('lista').innerHTML = html
  $('lista-vazia').hidden = itens.length > 0
  $('lista-acoes').hidden = !itens.length

  let feira = 0, cheio = 0, n = 0
  for (const b of mostrar) {
    const pf = parseBRL(b.feira) ?? parseBRL(b.preco)
    if (pf == null) continue
    n++; feira += pf; cheio += parseBRL(b.preco) ?? pf
  }
  const t = $('total')
  t.hidden = !mostrar.length
  if (mostrar.length) {
    const eco = cheio - feira
    t.innerHTML = `<div class="note">${n === mostrar.length ? `${n} livro${n > 1 ? 's' : ''}` : `${n} de ${mostrar.length} livros têm preço`} · total na feira</div>` +
      `<strong>${brl(feira)}</strong>${eco > 0.004 ? `<s>${brl(cheio)}</s> <span class="eco">economia de ${brl(eco)}</span>` : ''}`
  }
}

function textoLista() {
  const itens = lista.map((x) => porChave.get(x.k) || x)
    .sort((a, b) => collator.compare(a.editora, b.editora) || collator.compare(a.titulo, b.titulo))
  let out = 'Minha lista — Festa do Livro da USP\n'
  let grupo = null
  let total = 0
  for (const b of itens) {
    if (b.editora !== grupo) { grupo = b.editora; out += `\n${grupo}\n` }
    const p = b.feira || b.preco
    total += parseBRL(p) ?? 0
    out += `• ${b.titulo}${b.autor ? ` — ${b.autor}` : ''}${p ? ` (${p})` : ''}\n`
  }
  return out + `\nTotal na feira: ${brl(total)}\n`
}

async function copiar(txt, ok) {
  try { await navigator.clipboard.writeText(txt); toast(ok) } catch { prompt('Copie:', txt) }
}

/* ---------- importar e compartilhar ---------- */

function extrairIsbns(txt) {
  const out = new Set()
  for (const m of String(txt).matchAll(/(?:97[89][-\s]?)?(?:\d[-\s]?){9}[\dXx]/g)) {
    const i = isbn13(m[0])
    if (i) out.add(i)
  }
  return [...out]
}

function importar(txt) {
  const isbns = extrairIsbns(txt)
  const res = $('import-res')
  res.hidden = false
  if (!isbns.length) { res.textContent = 'Não achei nenhum ISBN válido no que você colou.'; return }
  const achados = isbns.map((i) => porIsbn.get(i)).filter(Boolean)
  const novos = adicionar(achados)
  res.textContent = `${isbns.length} ISBN${isbns.length > 1 ? 's' : ''} lido${isbns.length > 1 ? 's' : ''}, ${achados.length} na festa` +
    (achados.length ? `, ${novos} novo${novos === 1 ? '' : 's'} na sua lista.` : '.')
  desenharLista()
  desenharResultados()
}

function linkLista() {
  const isbns = lista.map((x) => x.isbn13).filter(Boolean)
  const fora = lista.length - isbns.length
  const url = `${location.origin}${location.pathname}#lista=${isbns.join(',')}`
  copiar(url, fora ? `Link copiado (${fora} sem ISBN ficaram de fora)` : 'Link da lista copiado')
}

function abrirLinkCompartilhado() {
  const m = /[#&]lista=([\dX,]*)/i.exec(location.hash)
  if (!m || !D) return
  history.replaceState(null, '', location.pathname + location.search)
  const achados = m[1].split(',').map((i) => porIsbn.get(isbn13(i))).filter(Boolean)
  if (!achados.length) return
  if (!confirm(`Adicionar ${achados.length} livro${achados.length > 1 ? 's' : ''} da lista compartilhada à sua lista?`)) return
  const novos = adicionar(achados)
  toast(`${novos} livro${novos === 1 ? '' : 's'} adicionado${novos === 1 ? '' : 's'}`)
  aba('lista')
}

/* ---------- abas e eventos ---------- */

function aba(qual) {
  const lista_ = qual === 'lista'
  $('tab-buscar').setAttribute('aria-selected', !lista_)
  $('tab-lista').setAttribute('aria-selected', lista_)
  $('pane-buscar').hidden = lista_
  $('pane-lista').hidden = !lista_
  store.set(K_ABA, qual)
  if (lista_) desenharLista()
  else desenharResultados()
}

$('tab-buscar').onclick = () => aba('buscar')
$('tab-lista').onclick = () => aba('lista')
$('editora').onchange = buscar
let qT
$('q').oninput = () => { clearTimeout(qT); qT = setTimeout(buscar, 120) }
$('mais').onclick = () => { limite += PAGINA; desenharResultados() }
$('lista-ed').onclick = (e) => {
  const c = e.target.closest('.chip')
  if (!c) return
  filtroLista = c.dataset.slug
  desenharLista()
}
document.addEventListener('click', (e) => {
  const h = e.target.closest('.heart')
  if (h) alternar(h.dataset.k)
})
$('copiar').onclick = () => copiar(textoLista(), 'Lista copiada')
$('link').onclick = linkLista
$('limpar').onclick = () => {
  if (!confirm('Tirar todos os livros da sua lista?')) return
  lista = []
  salvarLista()
  desenharLista()
  desenharResultados()
}
$('import-btn').onclick = () => importar($('import-txt').value)
$('import-file').onchange = async (e) => {
  const f = e.target.files?.[0]
  if (f) importar(await f.text())
  e.target.value = ''
}
window.addEventListener('hashchange', abrirLinkCompartilhado)

salvarLista()
aba(store.get(K_ABA) === 'lista' ? 'lista' : 'buscar')
carregar()
