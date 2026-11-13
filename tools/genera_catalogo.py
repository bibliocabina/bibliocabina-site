#!/usr/bin/env python3
"""Scrive nelle pagine l'elenco dei libri letto dal database (Supabase).

Le pagine contengono già l'elenco in HTML, così lo vedono Google e chi ha JavaScript spento.
In più assets/catalogo.js lo aggiorna dal vivo nel browser. Questo script tiene allineato l'HTML.

Uso (dalla cartella del sito):
    python3 tools/genera_catalogo.py                 legge i libri dal database e riscrive le pagine
    python3 tools/genera_catalogo.py --json righe.json   usa un file JSON invece del database
    python3 tools/genera_catalogo.py --controlla      non scrive: dice se le pagine sono aggiornate

Usa solo la libreria standard di Python. Indirizzo e chiave pubblica del database
sono quelli scritti in assets/catalogo.js (la chiave pubblica può solo leggere).
"""
import argparse
import html
import json
import re
import sys
import urllib.request
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
BASE = "https://bibliocabina.github.io/bibliocabina-site/"
PERCORSO_COPERTINA = re.compile(r"^assets/copertine/[A-Za-z0-9._-]+$")

# pagina -> (modo, prefisso dei percorsi, quanti libri mostrare: 0 = tutti)
PAGINE = {
    "catalogo/index.html": ("catalogo", "../", 0),
    "index.html": ("anteprima", "", 3),
}


# ---------------------------------------------------------------- dati
def leggi_config():
    js = (RADICE / "assets" / "catalogo.js").read_text(encoding="utf-8")
    url = re.search(r"url:\s*'([^']+)'", js).group(1)
    chiave = re.search(r"key:\s*'([^']+)'", js).group(1)
    return url, chiave


def righe_dal_database():
    url, chiave = leggi_config()
    q = "/rest/v1/libri?select=id,titolo,autore,genere,isbn,stato,copertina_url&order=id.desc"
    req = urllib.request.Request(url + q, headers={"apikey": chiave, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def raggruppa(righe, massimo=0):
    """Stesso titolo, autore e ISBN = più copie dello stesso libro. Mai solo per ISBN."""
    gruppi, indice = [], {}
    for r in sorted(righe, key=lambda r: -r["id"]):
        titolo = (r.get("titolo") or "").strip()
        if not titolo:
            continue
        autore = (r.get("autore") or "").strip()
        isbn = r.get("isbn") or ""
        chiave = (titolo.lower(), autore.lower(), isbn)
        img = r.get("copertina_url") or ""
        img = img if PERCORSO_COPERTINA.match(img) else ""
        g = indice.get(chiave)
        if g is None:
            g = indice[chiave] = {"titolo": titolo, "autore": autore, "genere": (r.get("genere") or "").strip(),
                                  "isbn": isbn, "img": img, "copie": 0, "incabina": 0}
            gruppi.append(g)
        g["copie"] += 1
        if r.get("stato") == "in cabina":
            g["incabina"] += 1
        if not g["img"] and img:
            g["img"] = img
    return gruppi[:massimo] if massimo else gruppi


def testo_stato(g):
    copie = f" ({g['copie']} copie)" if g["copie"] > 1 else ""
    if g["incabina"] == g["copie"]:
        return "In cabina" + copie
    if g["incabina"] == 0:
        return "In viaggio" + copie
    return f"In cabina ({g['incabina']} di {g['copie']} copie)"


def impronta(gruppi):
    """FNV-1a a 32 bit sui byte UTF-8. Identica a quella calcolata in assets/catalogo.js."""
    s = "\x1e".join("\x1f".join([g["titolo"], g["autore"], g["genere"], g["isbn"], g["img"],
                                 str(g["copie"]), str(g["incabina"])]) for g in gruppi)
    h = 0x811C9DC5
    for b in s.encode("utf-8"):
        h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    return f"{h:08x}"


# ---------------------------------------------------------------- HTML
def e(testo):
    return html.escape(testo, quote=True)


def copertina(g, prefisso):
    if not g["img"]:
        return f'<span class="cover cover-text"><span>{e(g["titolo"])}</span></span>'
    return (f'<span class="cover cover-photo"><img src="{e(prefisso + g["img"])}" '
            f'alt="Copertina di {e(g["titolo"])}" loading="lazy" decoding="async"></span>')


def voce_catalogo(g, prefisso):
    righe = ['        <li class="book">', f"          {copertina(g, prefisso)}",
             '          <div class="book-info">', f"            <h2>{e(g['titolo'])}</h2>"]
    if g["autore"]:
        righe.append(f'            <p class="author">{e(g["autore"])}</p>')
    meta = ""
    if g["genere"]:
        meta += f'<span class="genre">{e(g["genere"])}</span>'
    classe = "status out" if g["incabina"] == 0 else "status"
    meta += f'<span class="{classe}">{e(testo_stato(g))}</span>'
    righe += [f'            <p class="meta">{meta}</p>', "          </div>", "        </li>"]
    return "\n".join(righe)


def voce_anteprima(g, prefisso):
    return "\n".join([f'        <li><a href="{prefisso}catalogo/">',
                      f"          {copertina(g, prefisso)}",
                      f'          <span class="cover-label">{e(g["titolo"])}</span>',
                      "        </a></li>"])


def blocco_elenco(gruppi, modo, prefisso, massimo):
    tag_classe = "books" if modo == "catalogo" else "covers"
    voce = voce_catalogo if modo == "catalogo" else voce_anteprima
    attr_max = f' data-max="{massimo}"' if massimo else ""
    testa = (f'<ul class="{tag_classe}" data-libri="{modo}" data-prefisso="{prefisso}"{attr_max} '
             f'data-sig="{impronta(gruppi)}">')
    corpo = "\n".join(voce(g, prefisso) for g in gruppi)
    return f"      {testa}\n{corpo}\n      </ul>" if gruppi else f"      {testa}\n      </ul>"


def json_ld(gruppi):
    elementi = []
    for i, g in enumerate(gruppi, 1):
        libro = {"@type": "Book", "name": g["titolo"]}
        if g["autore"]:
            libro["author"] = [{"@type": "Person", "name": a.strip()} for a in g["autore"].split(",") if a.strip()]
        if g["isbn"]:
            libro["isbn"] = g["isbn"]
        if g["genere"]:
            libro["genre"] = g["genere"]
        if g["img"]:
            libro["image"] = BASE + g["img"]
        elementi.append({"@type": "ListItem", "position": i, "item": libro})
    dati = {"@context": "https://schema.org", "@type": "ItemList",
            "name": "Catalogo della Bibliocabina di Castelforte", "itemListElement": elementi}
    testo = json.dumps(dati, ensure_ascii=False, indent=2).replace("</", "<\\/")
    return '<script type="application/ld+json">\n' + testo + "\n</script>"


# ---------------------------------------------------------------- pagine
def sostituisci(testo, nome, nuovo):
    modello = re.compile(rf"(<!-- {nome}:inizio -->\n)(.*?)(\n[ \t]*<!-- {nome}:fine -->)", re.S)
    if not modello.search(testo):
        raise SystemExit(f"errore: mancano i segnaposto «{nome}:inizio» e «{nome}:fine»")
    return modello.sub(lambda m: m.group(1) + nuovo + m.group(3), testo, count=1)


def genera(righe):
    risultato = {}
    for pagina, (modo, prefisso, massimo) in PAGINE.items():
        percorso = RADICE / pagina
        testo = percorso.read_text(encoding="utf-8")
        gruppi = raggruppa(righe, massimo)
        testo = sostituisci(testo, "libri", blocco_elenco(gruppi, modo, prefisso, massimo))
        if modo == "catalogo":
            testo = sostituisci(testo, "libri-jsonld", json_ld(gruppi))
        risultato[percorso] = testo
    return risultato


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", help="file JSON con le righe della tabella libri (invece del database)")
    ap.add_argument("--controlla", action="store_true", help="non scrive: esce con 1 se le pagine sono da aggiornare")
    a = ap.parse_args()
    righe = json.loads(Path(a.json).read_text(encoding="utf-8")) if a.json else righe_dal_database()
    nuove = genera(righe)
    da_aggiornare = [p for p, t in nuove.items() if p.read_text(encoding="utf-8") != t]
    if a.controlla:
        for p in da_aggiornare:
            print("da aggiornare:", p.relative_to(RADICE))
        print("pagine aggiornate" if not da_aggiornare else "")
        sys.exit(1 if da_aggiornare else 0)
    for p, t in nuove.items():
        if p in da_aggiornare:
            p.write_text(t, encoding="utf-8")
            print("aggiornata:", p.relative_to(RADICE))
    if not da_aggiornare:
        print("nessuna modifica: le pagine erano già aggiornate")


if __name__ == "__main__":
    main()
