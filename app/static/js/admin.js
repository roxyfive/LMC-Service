/* LMC Admin: menu attivo, editor righe fattura/preventivo, conferme. Nessuna dipendenza esterna. */
(function () {
  'use strict';
  const here = location.pathname.replace(/\/$/, '') || '/';
  let best = null;
  document.querySelectorAll('.side a').forEach(a => {
    const u = (a.dataset.url || '').replace(/\/$/, '') || '/';
    if (here === u || (u !== '/admin' && here.startsWith(u))) { if (!best || u.length > best.u.length) best = { a, u }; }
  });
  if (best) { best.a.classList.add('on'); best.a.setAttribute('aria-current', 'page'); }
  document.addEventListener('click', e => { if (e.target.closest('.side a')) document.body.classList.remove('nav-open'); });

  /* conferme dichiarative: <button data-confirm="Eliminare?"> */
  document.addEventListener('click', e => {
    const b = e.target.closest('[data-confirm]');
    if (b && !confirm(b.dataset.confirm)) { e.preventDefault(); e.stopPropagation(); }
  }, true);

  /* editor righe (fatture e preventivi) */
  const box = document.getElementById('lines');
  if (box) {
    const money = n => (isFinite(n) ? n : 0).toLocaleString('it-IT', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    const num = v => parseFloat(String(v).replace(/\./g, '').replace(',', '.')) || (String(v).includes(',') ? 0 : parseFloat(v) || 0);
    const tb = box.querySelector('tbody');
    const rowHtml = (d = '', q = 1, p = 0) => `<tr><td><input name="desc" value="${String(d).replace(/"/g, '&quot;')}" placeholder="Descrizione" aria-label="Descrizione"></td>
      <td class="q"><input name="qty" value="${q}" inputmode="decimal" aria-label="Quantità"></td><td class="p"><input name="price" value="${p}" inputmode="decimal" aria-label="Prezzo"></td>
      <td class="t num">0,00</td><td><button type="button" class="btn s d" data-del aria-label="Togli la riga">✕</button></td></tr>`;
    const calc = () => {
      let imp = 0;
      tb.querySelectorAll('tr').forEach(tr => {
        const t = num(tr.querySelector('[name=qty]').value) * num(tr.querySelector('[name=price]').value);
        tr.querySelector('.t').textContent = money(t); imp += t;
      });
      const ivaEl = document.getElementById('iva_pct'), pct = ivaEl ? num(ivaEl.value) : 0;
      const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = money(v); };
      set('t_imp', imp); set('t_iva', imp * pct / 100); set('t_tot', imp * (1 + pct / 100));
    };
    const add = (d, q, p) => { tb.insertAdjacentHTML('beforeend', rowHtml(d, q, p)); calc(); };
    box.addEventListener('input', calc);
    box.addEventListener('click', e => { if (e.target.closest('[data-del]')) { const tr = e.target.closest('tr'); if (tb.children.length > 1) tr.remove(); else tr.querySelectorAll('input').forEach(i => i.value = ''); calc(); } });
    const addBtn = document.getElementById('addLine'); if (addBtn) addBtn.addEventListener('click', () => add());
    const pick = document.getElementById('tarPick');
    if (pick) pick.addEventListener('change', () => {
      const o = pick.selectedOptions[0]; if (!o || !o.value) return;
      const first = tb.querySelector('tr:last-child [name=desc]'); const empty = first && !first.value.trim();
      if (empty) { first.value = o.dataset.name; tb.querySelector('tr:last-child [name=price]').value = o.dataset.price; } else add(o.dataset.name, 1, o.dataset.price);
      pick.value = ''; calc();
    });
    const iva = document.getElementById('iva_pct'); if (iva) iva.addEventListener('input', calc);
    calc();
  }

  /* anteprima del cambio di stato SDI, tabelle larghe: nessuna logica aggiuntiva */
})();
