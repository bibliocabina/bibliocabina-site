/* Catalogo della Bibliocabina: legge i libri dal database (Supabase) e aggiorna l'elenco.
   L'HTML della pagina contiene già l'elenco (lo vedono Google e chi ha JavaScript spento):
   questo script lo sostituisce solo se i dati nel database sono cambiati.
   Se la chiamata fallisce, resta l'elenco già presente nella pagina.
   Per spegnere la lettura dal database basta mettere live: false. */
(function () {
  'use strict';

  var CFG = {
    live: true,
    url: 'https://kbacpvylupvwlesjpulw.supabase.co',
    key: 'sb_publishable_H-ySmiy1RDkohfEil3YIoQ_wy_uD0en', // chiave pubblica: può solo leggere i libri
    timeout: 8000
  };

  var host = document.querySelector('[data-libri]');
  if (!host || !CFG.live || !window.fetch) return;

  var MODO = host.getAttribute('data-libri');            // 'catalogo' oppure 'anteprima'
  var PREFISSO = host.getAttribute('data-prefisso') || ''; // '' dalla home, '../' dalle altre pagine
  var MAX = parseInt(host.getAttribute('data-max'), 10) || 0;
  var PERCORSO_COPERTINA = /^assets\/copertine\/[A-Za-z0-9._-]+$/;

  /* ---- dati: righe del database -> libri raggruppati (stesso titolo, autore e ISBN = più copie) ---- */
  function raggruppa(righe) {
    var gruppi = [], indice = {};
    righe.forEach(function (r) {
      if (!r || typeof r.titolo !== 'string' || !r.titolo.trim()) return;
      var chiave = [r.titolo.trim().toLowerCase(), (r.autore || '').trim().toLowerCase(), r.isbn || ''].join('\u001f');
      var g = indice[chiave];
      if (!g) {
        g = indice[chiave] = {
          titolo: r.titolo.trim(),
          autore: (r.autore || '').trim(),
          genere: (r.genere || '').trim(),
          isbn: r.isbn || '',
          img: PERCORSO_COPERTINA.test(r.copertina_url || '') ? r.copertina_url : '',
          copie: 0,
          incabina: 0
        };
        gruppi.push(g);
      }
      g.copie += 1;
      if (r.stato === 'in cabina') g.incabina += 1;
      if (!g.img && PERCORSO_COPERTINA.test(r.copertina_url || '')) g.img = r.copertina_url;
    });
    return MAX ? gruppi.slice(0, MAX) : gruppi;
  }

  function testoStato(g) {
    var copie = g.copie > 1 ? ' (' + g.copie + ' copie)' : '';
    if (g.incabina === g.copie) return 'In cabina' + copie;
    if (g.incabina === 0) return 'In viaggio' + copie;
    return 'In cabina (' + g.incabina + ' di ' + g.copie + ' copie)';
  }

  /* Impronta dei dati (FNV-1a sui byte UTF-8). Deve dare lo stesso risultato di tools/genera_catalogo.py. */
  function impronta(gruppi) {
    var s = gruppi.map(function (g) {
      return [g.titolo, g.autore, g.genere, g.isbn, g.img, g.copie, g.incabina].join('\u001f');
    }).join('\u001e');
    var h = 0x811c9dc5, b = new TextEncoder().encode(s);
    for (var i = 0; i < b.length; i++) {
      h ^= b[i];
      h = Math.imul(h, 0x01000193) >>> 0;
    }
    return ('00000000' + h.toString(16)).slice(-8);
  }

  /* ---- HTML (stessa struttura di quello generato da tools/genera_catalogo.py) ---- */
  function el(tag, classe, testo) {
    var e = document.createElement(tag);
    if (classe) e.className = classe;
    if (testo != null) e.textContent = testo;
    return e;
  }

  function copertinaTesto(titolo) {
    var s = el('span', 'cover cover-text');
    s.appendChild(el('span', null, titolo));
    return s;
  }

  function copertina(g) {
    if (!g.img) return copertinaTesto(g.titolo);
    var s = el('span', 'cover cover-photo');
    var im = document.createElement('img');
    im.src = PREFISSO + g.img;
    im.alt = 'Copertina di ' + g.titolo;
    im.loading = 'lazy';
    im.decoding = 'async';
    s.appendChild(im);
    return s;
  }

  function voceCatalogo(g) {
    var li = el('li', 'book');
    li.appendChild(copertina(g));
    var info = el('div', 'book-info');
    info.appendChild(el('h2', null, g.titolo));
    if (g.autore) info.appendChild(el('p', 'author', g.autore));
    var meta = el('p', 'meta');
    if (g.genere) meta.appendChild(el('span', 'genre', g.genere));
    meta.appendChild(el('span', g.incabina === 0 ? 'status out' : 'status', testoStato(g)));
    info.appendChild(meta);
    li.appendChild(info);
    return li;
  }

  function voceAnteprima(g) {
    var li = document.createElement('li');
    var a = el('a');
    a.href = PREFISSO + 'catalogo/';
    a.appendChild(copertina(g));
    a.appendChild(el('span', 'cover-label', g.titolo));
    li.appendChild(a);
    return li;
  }

  function disegna(gruppi) {
    host.textContent = '';
    gruppi.forEach(function (g) {
      host.appendChild(MODO === 'catalogo' ? voceCatalogo(g) : voceAnteprima(g));
    });
    sistemaImmaginiRotte();
  }

  /* Se un file di copertina non si carica, al suo posto compare la copertina con il solo titolo. */
  function sistemaImmaginiRotte() {
    host.querySelectorAll('.cover-photo img').forEach(function (im) {
      if (im.complete && im.naturalWidth === 0) sostituisci(im);
    });
  }
  function sostituisci(im) {
    var cornice = im.parentNode;
    if (!cornice || !cornice.classList.contains('cover-photo')) return;
    var titolo = (im.alt || '').replace(/^Copertina di /, '');
    cornice.parentNode.replaceChild(copertinaTesto(titolo), cornice);
  }
  host.addEventListener('error', function (e) {
    if (e.target && e.target.tagName === 'IMG') sostituisci(e.target);
  }, true);
  sistemaImmaginiRotte();

  /* ---- lettura dal database ---- */
  var ctrl = window.AbortController ? new AbortController() : null;
  var timer = ctrl ? setTimeout(function () { ctrl.abort(); }, CFG.timeout) : null;

  fetch(CFG.url + '/rest/v1/libri?select=id,titolo,autore,genere,isbn,stato,copertina_url&order=id.desc', {
    headers: { apikey: CFG.key, Accept: 'application/json' },
    signal: ctrl ? ctrl.signal : undefined
  })
    .then(function (r) {
      if (!r.ok) throw new Error('risposta ' + r.status);
      return r.json();
    })
    .then(function (righe) {
      if (!Array.isArray(righe)) throw new Error('formato inatteso');
      var gruppi = raggruppa(righe);
      if (impronta(gruppi) === host.getAttribute('data-sig')) return; // già aggiornato: non tocca nulla
      disegna(gruppi);
      host.setAttribute('data-sig', impronta(gruppi));
    })
    .catch(function () { /* database non raggiungibile: resta l'elenco già nella pagina */ })
    .then(function () { if (timer) clearTimeout(timer); });
})();
