# bibliocabina-site

Sito statico della Bibliocabina di Castelforte. Indirizzo principale (quello che dichiarano canonical,
sitemap e dati strutturati): https://bibliocabina.pages.dev/ (Cloudflare Pages).
La copia su GitHub Pages (bibliocabina.github.io/bibliocabina-site) dichiara lo stesso canonical.

## Struttura

- `index.html` e le cartelle `chi-siamo/`, `catalogo/`, `come-funziona/`, `dove-siamo/`, `contatti/`: una pagina per cartella
- `assets/`: stile (`style.css`), menu (`menu.js`), catalogo (`catalogo.js`), font Inter, immagini, `copertine/`
- `sitemap.xml` e `robots.txt`: la sitemap va aggiornata (`lastmod`) quando cambia una pagina

## Catalogo dei libri

I libri stanno nel database Supabase (progetto `bibliocabina`, tabella `libri`).
Il sito li mostra in due modi, che lavorano insieme:

1. **HTML già pronto nella pagina.** L'elenco in `catalogo/index.html` e l'anteprima in `index.html`
   (tra i commenti `libri:inizio` e `libri:fine`) sono scritti dallo script `tools/genera_catalogo.py`.
   È quello che vedono Google e chi ha JavaScript spento.
2. **Aggiornamento dal vivo.** `assets/catalogo.js` legge la tabella dal browser del visitatore e
   ridisegna l'elenco solo se i dati sono diversi da quelli già nella pagina. Se il database non risponde,
   resta l'elenco già presente. Per spegnerlo basta `live: false` in `assets/catalogo.js`.

Dopo aver cambiato i libri nel database, per riallineare l'HTML:

```
python3 tools/genera_catalogo.py            # legge dal database e riscrive le pagine
python3 tools/genera_catalogo.py --controlla  # dice se le pagine sono già aggiornate
```

Poi commit e push. Le copertine sono file in `assets/copertine/`, indicati nella colonna `copertina_url`
del database (es. `assets/copertine/peter-pan.jpg`).

Più copie dello stesso libro (stesso titolo, autore e ISBN) compaiono come un solo libro con il numero di copie.
L'ISBN da solo non identifica un libro: nelle collane diversi titoli possono condividerlo.

La chiave nel file `catalogo.js` è la chiave pubblica del database: può solo leggere i libri
(la sicurezza è nelle regole della tabella). La chiave segreta non va mai messa nel sito.
