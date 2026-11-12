(function () {
  var body = document.body;
  var menuBtn = document.getElementById('menu-btn');
  var closeBtn = document.getElementById('close-btn');
  var scrim = document.getElementById('scrim');
  var drawer = document.getElementById('drawer');
  if (!menuBtn || !closeBtn || !scrim || !drawer) return;

  function setMenu(open) {
    body.classList.toggle('menu-open', open);
    menuBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (open) closeBtn.focus();
  }

  menuBtn.addEventListener('click', function () { setMenu(true); });
  closeBtn.addEventListener('click', function () { setMenu(false); menuBtn.focus(); });
  scrim.addEventListener('click', function () { setMenu(false); menuBtn.focus(); });

  document.addEventListener('keydown', function (e) {
    if (!body.classList.contains('menu-open')) return;
    if (e.key === 'Escape') { setMenu(false); menuBtn.focus(); return; }
    if (e.key === 'Tab') {
      var f = drawer.querySelectorAll('a[href], button');
      var first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  });

  /* Tornando indietro dal browser il menu non deve restare aperto. */
  window.addEventListener('pageshow', function () { setMenu(false); });
})();
