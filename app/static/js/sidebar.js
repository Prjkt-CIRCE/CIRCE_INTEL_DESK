/* ============================================================
   sidebar.js -- CIRCE Intel Desk WORKBENCH-01
   Toggle expandido/recolhido da sidebar global.
   Estado persiste em localStorage sob a chave 'circe_sidebar'.
   ============================================================ */
(function () {
  'use strict';

  var STORAGE_KEY = 'circe_sidebar_collapsed';
  var shell = document.querySelector('.app-shell');
  var toggle = document.getElementById('sidebar-toggle');
  var sidebar = document.getElementById('app-sidebar');

  if (!shell || !toggle || !sidebar) return;

  /* --- Restaurar estado salvo --- */
  var collapsed = localStorage.getItem(STORAGE_KEY) === 'true';
  applyState(collapsed);

  /* --- Toggle ao clicar --- */
  toggle.addEventListener('click', function () {
    collapsed = !collapsed;
    localStorage.setItem(STORAGE_KEY, String(collapsed));
    applyState(collapsed);
  });

  function applyState(isCollapsed) {
    if (isCollapsed) {
      shell.classList.add('app-shell--sidebar-collapsed');
      toggle.setAttribute('aria-label', 'Expandir sidebar');
      toggle.setAttribute('aria-expanded', 'false');
      document.body.setAttribute('data-sidebar-collapsed', 'true');
    } else {
      shell.classList.remove('app-shell--sidebar-collapsed');
      toggle.setAttribute('aria-label', 'Recolher sidebar');
      toggle.setAttribute('aria-expanded', 'true');
      document.body.setAttribute('data-sidebar-collapsed', 'false');
    }
  }

  /* --- Tooltips no modo recolhido --- */
  var items = sidebar.querySelectorAll('.app-sidebar__item');
  items.forEach(function (item) {
    var label = item.querySelector('.app-sidebar__label');
    if (!label) return;
    var text = label.textContent.trim();

    var tip = null;

    item.addEventListener('mouseenter', function () {
      if (!shell.classList.contains('app-shell--sidebar-collapsed')) return;
      tip = document.createElement('div');
      tip.className = 'app-sidebar__tooltip';
      tip.textContent = text;
      document.body.appendChild(tip);
      var rect = item.getBoundingClientRect();
      tip.style.top = (rect.top + rect.height / 2 - tip.offsetHeight / 2) + 'px';
      tip.style.left = (rect.right + 8) + 'px';
    });

    item.addEventListener('mouseleave', function () {
      if (tip) { tip.remove(); tip = null; }
    });
  });

})();