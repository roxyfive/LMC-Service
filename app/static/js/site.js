(function () {
  'use strict';
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const CSRF = $('meta[name=csrf]').content;
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const post = async (url, data) => {
    try {
      const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': CSRF }, body: JSON.stringify(data) });
      return { ok: r.ok, data: await r.json().catch(() => ({})) };
    } catch (e) { return { ok: false, data: { error: 'Connessione assente. Riprova.' } }; }
  };
  const ready = () => document.documentElement.classList.add('ready');

  /* ---------- menu ---------- */
  const burger = $('.burger'), menu = $('#menu'), nav = $('.nav');
  burger.addEventListener('click', () => { const o = menu.classList.toggle('open'); burger.setAttribute('aria-expanded', o); if (o) nav.classList.add('solid'); else onScroll(); });
  $$('#menu a').forEach(a => a.addEventListener('click', () => { menu.classList.remove('open'); burger.setAttribute('aria-expanded', 'false'); }));

  /* ---------- barra di avanzamento, menu chiaro dopo la hero, menu nascosto scorrendo ---------- */
  const sp = $('#sp'); let lastY = 0, tick = false;
  function onScroll() {
    const y = scrollY, max = document.documentElement.scrollHeight - innerHeight;
    sp.style.transform = 'scaleX(' + (max > 0 ? Math.min(1, y / max) : 0) + ')';
    nav.classList.toggle('solid', y > 60 || menu.classList.contains('open'));
    nav.classList.toggle('hide', y > lastY && y > 500 && !menu.classList.contains('open'));
    lastY = y; tick = false;
  }
  addEventListener('scroll', () => { if (!tick) { tick = true; requestAnimationFrame(onScroll); } }, { passive: true });
  onScroll();

  /* ---------- animazioni allo scroll ---------- */
  const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } }), { threshold: .12 });
  $$('.reveal').forEach(el => io.observe(el));

  /* ---------- video lazy ---------- */
  const vio = new IntersectionObserver(es => es.forEach(e => {
    const v = e.target;
    if (e.isIntersecting) { if (!v.src) v.src = v.dataset.src; v.play().catch(() => { }); } else v.pause();
  }), { threshold: .3 });
  $$('.lazyvid').forEach(v => vio.observe(v));

  /* ---------- portfolio + lightbox accessibile ---------- */
  $$('.filters .chip').forEach(b => b.addEventListener('click', () => {
    $$('.filters .chip').forEach(x => x.classList.remove('on')); b.classList.add('on');
    $$('.pf').forEach(i => { const hide = b.dataset.cat !== '*' && i.dataset.cat !== b.dataset.cat; i.classList.toggle('hide', hide); if (!hide) i.classList.add('in'); });
  }));
  const lb = $('#lb'), lbImg = $('img', lb), lbCap = $('figcaption', lb);
  let cur = 0, list = [], opener = null;
  const show = i => { cur = (i + list.length) % list.length; lbImg.src = list[cur].href; lbImg.alt = list[cur].dataset.cap; lbCap.textContent = list[cur].dataset.cap; };
  const closeLb = () => { lb.hidden = true; document.body.style.overflow = ''; if (opener) opener.focus(); };
  $$('.pf').forEach(a => a.addEventListener('click', e => {
    e.preventDefault(); opener = a; list = $$('.pf:not(.hide)'); show(list.indexOf(a)); lb.hidden = false; document.body.style.overflow = 'hidden'; $('.lb-x').focus();
  }));
  $('.lb-x').onclick = closeLb; $('.lb-p').onclick = () => show(cur - 1); $('.lb-n').onclick = () => show(cur + 1);
  lb.addEventListener('click', e => { if (e.target === lb) closeLb(); });
  document.addEventListener('keydown', e => {
    if (lb.hidden) return;
    if (e.key === 'Escape') closeLb(); if (e.key === 'ArrowLeft') show(cur - 1); if (e.key === 'ArrowRight') show(cur + 1);
    if (e.key === 'Tab') { const f = $$('button', lb), i = f.indexOf(document.activeElement); e.preventDefault(); f[(i + (e.shiftKey ? -1 : 1) + f.length) % f.length].focus(); }  // focus intrappato nel dialogo
  });

  /* ---------- prenotazione + preventivo ---------- */
  const bf = $('#bookForm'), dateIn = bf.date, timeSel = bf.time, info = $('#slotInfo');
  dateIn.min = new Date(Date.now() + 864e5).toISOString().slice(0, 10);
  const setInfo = t => { info.textContent = t; info.hidden = !t; };
  dateIn.addEventListener('change', async () => {
    timeSel.innerHTML = '<option value="">Caricamento…</option>';
    try {
      const slots = await (await fetch('/api/slots?date=' + dateIn.value)).json();
      timeSel.innerHTML = slots.length ? '<option value="">Scegli orario</option>' + slots.map(s => `<option>${s}</option>`).join('') : '<option value="">Nessun orario</option>';
      setInfo(slots.length ? '' : 'Nessuna disponibilità in questo giorno: prova un altro giorno.');
    } catch (e) { timeSel.innerHTML = '<option value="">Errore</option>'; }
  });
  const setMsg = (f, t, ok) => { const m = $('.msg', f); m.textContent = t; m.className = 'msg ' + (ok ? 'ok' : 'err'); };
  bf.addEventListener('submit', async e => {
    e.preventDefault();
    const d = Object.fromEntries(new FormData(bf)); d.consent = bf.consent.checked;
    if (!d.date || !d.time) return setMsg(bf, 'Scegli giorno e orario.', false);
    const r = await post('/api/appuntamento', d);
    if (r.ok) { setMsg(bf, 'Richiesta inviata! Controlla l\'email: contiene il link per modificare o annullare.', true); bf.reset(); timeSel.innerHTML = '<option value="">Scegli prima il giorno</option>'; }
    else setMsg(bf, r.data.error || 'Errore, riprova.', false);
  });
  const qf = $('#quoteForm');
  qf.addEventListener('submit', async e => {
    e.preventDefault();
    const d = Object.fromEntries(new FormData(qf)); d.services = $$('input[name=services]:checked', qf).map(x => x.value); d.consent = qf.consent.checked;
    const r = await post('/api/preventivo', d);
    if (r.ok) { setMsg(qf, 'Richiesta inviata! Ti risponderemo al più presto.', true); qf.reset(); }
    else setMsg(qf, r.data.error || 'Errore, riprova.', false);
  });

  /* ---------- chat (solo testo: nessuna voce sintetica) ---------- */
  const chat = $('#chat'), log = $('#chatLog'), act = $('#chatAct'), inp = $('#chatIn'), chatBtn = $('#chatBtn');
  const toggleChat = open => { chat.hidden = !open; chatBtn.setAttribute('aria-expanded', open); if (open) inp.focus(); };
  chatBtn.onclick = () => toggleChat(chat.hidden);
  $('#chatX').onclick = () => { toggleChat(false); chatBtn.focus(); };
  const hist = [];
  const add = (cls, t) => { const p = document.createElement('p'); p.className = cls; p.textContent = t; log.appendChild(p); log.scrollTop = log.scrollHeight; };
  async function ask(text) {
    if (!text.trim()) return;
    add('me', text); hist.push({ role: 'user', content: text }); act.innerHTML = '';
    const r = await post('/api/chat', { messages: hist });
    const reply = r.ok ? r.data.reply : 'Al momento non riesco a rispondere. Usa la sezione Contatti.';
    add('bot', reply); hist.push({ role: 'assistant', content: reply });
    if (r.ok && r.data.action) {
      const b = document.createElement('a'); b.className = 'btn btn-gold'; b.href = r.data.action === 'prenota' ? '#prenota' : '#preventivo';
      b.textContent = r.data.action === 'prenota' ? 'Prenota ora' : 'Richiedi preventivo'; b.onclick = () => toggleChat(false); act.appendChild(b);
    }
  }
  $('#chatForm').addEventListener('submit', e => { e.preventDefault(); const t = inp.value; inp.value = ''; ask(t); });
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition, mic = $('#mic');
  if (SR) {   // dettatura (input vocale dell'utente): non produce alcuna voce
    const rec = new SR(); rec.lang = 'it-IT'; rec.interimResults = false;
    rec.onresult = e => ask(e.results[0][0].transcript); rec.onend = () => mic.classList.remove('rec');
    mic.onclick = () => { try { mic.classList.add('rec'); rec.start(); } catch (e) { mic.classList.remove('rec'); } };
  } else mic.style.display = 'none';

  /* ---------- PWA ---------- */
  if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => { });
  let dp; const inst = $('#install');
  window.addEventListener('beforeinstallprompt', e => { e.preventDefault(); dp = e; setTimeout(() => inst.hidden = false, 20000); });
  $('#installBtn').onclick = async () => { inst.hidden = true; if (dp) { dp.prompt(); dp = null; } };
  $('#installX').onclick = () => inst.hidden = true;

  /* ---------- titolo hero: comparsa lettera per lettera ---------- */
  (function () {
    const h = $('#heroTitle'); if (!h) return;
    h.setAttribute('aria-label', h.textContent.replace(/\s+/g, ' ').trim());
    let k = 0;
    $$('.ln', h).forEach(ln => {
      const words = ln.textContent.trim().split(/\s+/); ln.textContent = '';
      words.forEach((w, wi) => {
        const wd = document.createElement('span'); wd.className = 'wd'; wd.setAttribute('aria-hidden', 'true');
        [...w].forEach(c => { const s = document.createElement('span'); s.className = 'ch'; s.style.setProperty('--k', k++); s.textContent = c; wd.appendChild(s); });
        ln.appendChild(wd); if (wi < words.length - 1) ln.appendChild(document.createTextNode(' '));
      });
    });
  })();

  /* ---------- hero: slide automatiche con Ken Burns ---------- */
  (function () {
    const slides = $$('#heroSlides .hs'), dots = $('#heroDots');
    if (slides.length < 2 || reduce) return;
    const DUR = 6500; dots.style.setProperty('--dur', DUR + 'ms');
    slides.forEach(() => dots.appendChild(document.createElement('i')));
    const D = [...dots.children]; let n = 0, timer, visible = true;
    const mark = () => { D.forEach(d => d.classList.remove('on')); void dots.offsetWidth; D[n].classList.add('on'); };
    const go = i => {
      const old = slides[n]; old.classList.remove('on'); old.classList.add('leaving'); setTimeout(() => old.classList.remove('leaving'), 1900);
      n = i % slides.length; slides[n].classList.add('on'); mark();
    };
    const start = () => { clearInterval(timer); if (visible && !document.hidden) { mark(); timer = setInterval(() => go(n + 1), DUR); } };
    new IntersectionObserver(es => { visible = es[0].isIntersecting; start(); }, { threshold: .15 }).observe($('#hero'));
    document.addEventListener('visibilitychange', start);
    dots.style.pointerEvents = 'auto';
    D.forEach((d, k) => d.addEventListener('click', () => { go(k); start(); }));
  })();

  /* ---------- intro: musica + didascalie animate (voce.mp3 solo se presente) ---------- */
  const intro = $('#intro');
  let data = {}; try { data = JSON.parse($('#introData').textContent || '{}'); } catch (e) { }
  const steps = data.steps || [];
  let seen = false; try { seen = !!sessionStorage.getItem('introSeen'); } catch (e) { }
  const force = /[?&]intro=1/.test(location.search);
  if (!steps.length || reduce || (!force && (seen || location.hash))) { intro.hidden = true; ready(); }
  else startIntro();

  function startIntro() {
    document.body.style.overflow = 'hidden';
    const slides = $$('.slide', intro), cap = $('#introCap'), sub = $('#introSub'), num = $('#introNum'),
      bars = $$('#introBars i'), btnAudio = $('#introAudio'), btnSkip = $('#introSkip');
    const STEP = 4800, sleep = ms => new Promise(r => setTimeout(r, ms));
    const music = new Audio('/static/media/music.mp3'); music.loop = true; music.volume = .55; music.preload = 'none';
    const voce = data.voce ? new Audio(data.voce) : null; if (voce) voce.preload = 'metadata';
    let sound = false, run = 0, cur = -1, ended = false;
    setTimeout(() => slides.forEach(s => { if (!s.src && s.dataset.src) s.src = s.dataset.src; }), 500);
    btnSkip.focus({ preventScroll: true });

    const reset = () => { slides.forEach(s => s.classList.remove('on', 'leaving')); void intro.offsetWidth; cur = -1; bars.forEach(b => b.classList.remove('on', 'done')); };
    const showStep = (i, ms) => {
      const prev = slides[cur];
      if (prev) { prev.classList.remove('on'); prev.classList.add('leaving'); setTimeout(() => prev.classList.remove('leaving'), 1900); }
      cur = i; const sl = slides[i]; if (!sl.src && sl.dataset.src) sl.src = sl.dataset.src; sl.classList.add('on');
      cap.textContent = '';
      steps[i].cap.split(' ').forEach((w, k) => { const s = document.createElement('span'); s.className = 'w'; s.style.setProperty('--k', k); s.textContent = w; cap.appendChild(s); });
      sub.classList.remove('in'); sub.textContent = steps[i].sub; void sub.offsetWidth; sub.classList.add('in');
      num.textContent = String(i + 1).padStart(2, '0');
      bars.forEach((b, k) => { b.classList.toggle('done', k < i); b.classList.toggle('on', k === i); b.style.setProperty('--dur', ms + 'ms'); });
    };
    async function play() {
      const my = ++run; reset();
      if (sound && voce) { voce.currentTime = 0; voce.play().catch(() => { }); music.volume = .22; }
      const ms = sound && voce && isFinite(voce.duration) && voce.duration > 3 ? voce.duration * 1000 / steps.length : STEP;
      for (let i = 0; i < steps.length; i++) { if (my !== run) return; showStep(i, ms); await sleep(ms); }
      if (my === run) { await sleep(900); if (my === run) endIntro(); }
    }
    function endIntro() {
      if (ended) return; ended = true; run++;
      if (voce) voce.pause();
      const f = setInterval(() => { music.volume = Math.max(0, music.volume - .05); if (music.volume <= .01) { music.pause(); clearInterval(f); } }, 90);
      intro.classList.add('out'); document.body.style.overflow = ''; ready();
      setTimeout(() => { intro.hidden = true; }, 1200);
      try { sessionStorage.setItem('introSeen', '1'); } catch (e) { }
    }
    btnSkip.onclick = endIntro;
    document.addEventListener('keydown', e => { if (!ended && e.key === 'Escape') endIntro(); });
    btnAudio.onclick = () => {
      sound = !sound; btnAudio.setAttribute('aria-pressed', sound); btnAudio.classList.add('live');
      if (sound) {
        btnAudio.textContent = '♪ Musica attiva'; music.volume = voce ? .22 : .55; music.play().catch(() => { });
        if (voce) play();                          // con voce.mp3 si riparte da capo per sincronizzare
      } else {
        btnAudio.textContent = '♪ Musica disattivata'; music.pause(); if (voce) voce.pause();
      }
    };
    play();
  }
})();
