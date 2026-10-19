(function () {
  'use strict';
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const CSRF = $('meta[name=csrf]').content;
  const post = async (url, data) => {
    try {
      const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': CSRF }, body: JSON.stringify(data) });
      return { ok: r.ok, data: await r.json().catch(() => ({})) };
    } catch (e) { return { ok: false, data: { error: 'Connessione assente. Riprova.' } }; }
  };

  /* ---------- menu ---------- */
  const burger = $('.burger'), menu = $('#menu');
  burger.addEventListener('click', () => { const o = menu.classList.toggle('open'); burger.setAttribute('aria-expanded', o); });
  $$('#menu a').forEach(a => a.addEventListener('click', () => menu.classList.remove('open')));

  /* ---------- reveal ---------- */
  const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } }), { threshold: .12 });
  $$('.reveal').forEach(el => io.observe(el));

  /* ---------- video lazy ---------- */
  const vio = new IntersectionObserver(es => es.forEach(e => {
    const v = e.target;
    if (e.isIntersecting) { if (!v.src) v.src = v.dataset.src; v.play().catch(() => { }); } else v.pause();
  }), { threshold: .3 });
  $$('.lazyvid').forEach(v => vio.observe(v));

  /* ---------- galleria + lightbox ---------- */
  $$('.filters .chip').forEach(b => b.addEventListener('click', () => {
    $$('.filters .chip').forEach(x => x.classList.remove('on')); b.classList.add('on');
    $$('.g-item').forEach(i => i.classList.toggle('hide', b.dataset.cat !== '*' && i.dataset.cat !== b.dataset.cat));
  }));
  const lb = $('#lb'), lbImg = $('img', lb), lbCap = $('figcaption', lb);
  let cur = 0, list = [];
  const show = i => { cur = (i + list.length) % list.length; lbImg.src = list[cur].href; lbImg.alt = list[cur].dataset.cap; lbCap.textContent = list[cur].dataset.cap; };
  $$('.g-item').forEach(a => a.addEventListener('click', e => {
    e.preventDefault(); list = $$('.g-item:not(.hide)'); show(list.indexOf(a)); lb.hidden = false;
  }));
  $('.lb-x').onclick = () => lb.hidden = true; $('.lb-p').onclick = () => show(cur - 1); $('.lb-n').onclick = () => show(cur + 1);
  document.addEventListener('keydown', e => { if (lb.hidden) return; if (e.key === 'Escape') lb.hidden = true; if (e.key === 'ArrowLeft') show(cur - 1); if (e.key === 'ArrowRight') show(cur + 1); });

  /* ---------- prenotazione ---------- */
  const bf = $('#bookForm'), dateIn = bf.date, timeSel = bf.time, info = $('#slotInfo');
  const tomorrow = new Date(Date.now() + 864e5).toISOString().slice(0, 10);
  dateIn.min = tomorrow;
  dateIn.addEventListener('change', async () => {
    timeSel.innerHTML = '<option value="">Caricamento…</option>';
    try {
      const slots = await (await fetch('/api/slots?date=' + dateIn.value)).json();
      timeSel.innerHTML = slots.length ? '<option value="">Scegli orario</option>' + slots.map(s => `<option>${s}</option>`).join('') : '<option value="">Nessun orario</option>';
      info.textContent = slots.length ? '' : 'Nessuna disponibilità in questo giorno: prova un altro giorno.';
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

  /* ---------- chat + voce ---------- */
  const chat = $('#chat'), log = $('#chatLog'), act = $('#chatAct'), inp = $('#chatIn');
  $('#chatBtn').onclick = () => { chat.hidden = !chat.hidden; if (!chat.hidden) inp.focus(); };
  $('#chatX').onclick = () => chat.hidden = true;
  const hist = [];
  const add = (cls, t) => { const p = document.createElement('p'); p.className = cls; p.textContent = t; log.appendChild(p); log.scrollTop = log.scrollHeight; };
  const speak = t => {
    if (!$('#speak').checked || !('speechSynthesis' in window)) return;
    const u = new SpeechSynthesisUtterance(t); u.lang = 'it-IT';
    const v = speechSynthesis.getVoices().find(v => v.lang.startsWith('it')); if (v) u.voice = v;
    speechSynthesis.cancel(); speechSynthesis.speak(u);
  };
  async function ask(text) {
    if (!text.trim()) return;
    add('me', text); hist.push({ role: 'user', content: text }); act.innerHTML = '';
    const r = await post('/api/chat', { messages: hist });
    const reply = r.ok ? r.data.reply : 'Al momento non riesco a rispondere. Usa la sezione Contatti.';
    add('bot', reply); hist.push({ role: 'assistant', content: reply }); speak(reply);
    if (r.ok && r.data.action) {
      const b = document.createElement('a'); b.className = 'btn btn-gold'; b.href = r.data.action === 'prenota' ? '#prenota' : '#preventivo';
      b.textContent = r.data.action === 'prenota' ? 'Prenota ora' : 'Richiedi preventivo'; b.onclick = () => chat.hidden = true; act.appendChild(b);
    }
  }
  $('#chatForm').addEventListener('submit', e => { e.preventDefault(); const t = inp.value; inp.value = ''; ask(t); });
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition, mic = $('#mic');
  if (SR) {
    const rec = new SR(); rec.lang = 'it-IT'; rec.interimResults = false;
    rec.onresult = e => ask(e.results[0][0].transcript); rec.onend = () => mic.classList.remove('rec');
    mic.onclick = () => { try { mic.classList.add('rec'); rec.start(); } catch (e) { mic.classList.remove('rec'); } };
  } else mic.style.display = 'none';

  /* ---------- PWA ---------- */
  if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => { });
  let dp; const inst = $('#install');
  window.addEventListener('beforeinstallprompt', e => { e.preventDefault(); dp = e; setTimeout(() => inst.hidden = false, 15000); });
  $('#installBtn').onclick = async () => { inst.hidden = true; if (dp) { dp.prompt(); dp = null; } };
  $('#installX').onclick = () => inst.hidden = true;

  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const ready = () => document.documentElement.classList.add('ready');

  /* ---------- barra di avanzamento + menu che si nasconde scorrendo ---------- */
  const sp = $('#sp'), nav = $('.nav'); let lastY = 0, tick = false;
  addEventListener('scroll', () => {
    if (tick) return; tick = true;
    requestAnimationFrame(() => {
      const y = scrollY, max = document.documentElement.scrollHeight - innerHeight;
      sp.style.transform = 'scaleX(' + (max > 0 ? Math.min(1, y / max) : 0) + ')';
      nav.classList.toggle('hide', y > lastY && y > 400 && !menu.classList.contains('open'));
      lastY = y; tick = false;
    });
  }, { passive: true });

  /* ---------- hero: slide automatiche con Ken Burns ---------- */
  (function () {
    const slides = $$('#heroSlides .hs'), dots = $('#heroDots');
    if (slides.length < 2 || reduce) return;
    const DUR = 6500; dots.style.setProperty('--dur', DUR + 'ms');
    slides.forEach(() => dots.appendChild(document.createElement('i')));
    const D = [...dots.children]; let n = 0, timer, visible = true;
    const mark = () => { D.forEach(d => d.classList.remove('on')); void dots.offsetWidth; D[n].classList.add('on'); };
    const go = i => {
      const old = slides[n]; old.classList.remove('on'); old.classList.add('leaving'); setTimeout(() => old.classList.remove('leaving'), 1800);
      n = i % slides.length; slides[n].classList.add('on'); mark();
    };
    const start = () => { clearInterval(timer); if (visible && !document.hidden) { mark(); timer = setInterval(() => go(n + 1), DUR); } else clearInterval(timer); };
    new IntersectionObserver(es => { visible = es[0].isIntersecting; start(); }, { threshold: .15 }).observe($('#hero'));
    document.addEventListener('visibilitychange', start);
    D.forEach((d, k) => { d.style.cursor = 'pointer'; d.addEventListener('click', () => { go(k); start(); }); });
    dots.style.pointerEvents = 'auto';
  })();

  /* ---------- intro cinematografica ---------- */
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
    const MIN = 5600, sleep = ms => new Promise(r => setTimeout(r, ms));
    const music = new Audio('/static/media/music.mp3'); music.loop = true; music.volume = .5; music.preload = 'none';
    const voceFile = data.voce ? new Audio(data.voce) : null; if (voceFile) voceFile.preload = 'metadata';
    let sound = false, run = 0, cur = -1, ended = false, stopSpeak = null;
    setTimeout(() => slides.forEach(s => { if (!s.src && s.dataset.src) s.src = s.dataset.src; }), 500);
    btnSkip.focus({ preventScroll: true });

    const reset = () => {
      slides.forEach(s => s.classList.remove('on', 'leaving')); void intro.offsetWidth; cur = -1;
      bars.forEach(b => b.classList.remove('on', 'done'));
    };
    const showStep = (i, ms) => {
      const prev = slides[cur];
      if (prev) { prev.classList.remove('on'); prev.classList.add('leaving'); setTimeout(() => prev.classList.remove('leaving'), 1800); }
      cur = i; const sl = slides[i];
      if (!sl.src && sl.dataset.src) sl.src = sl.dataset.src;
      sl.classList.add('on');
      const st = steps[i];
      cap.textContent = '';
      st.cap.split(' ').forEach((w, k) => { const sp = document.createElement('span'); sp.className = 'w'; sp.style.setProperty('--k', k); sp.textContent = w; cap.appendChild(sp); });
      sub.classList.remove('in'); sub.textContent = st.sub; void sub.offsetWidth; sub.classList.add('in');
      num.textContent = String(i + 1).padStart(2, '0');
      bars.forEach((b, k) => { b.classList.toggle('done', k < i); b.classList.toggle('on', k === i); b.style.setProperty('--dur', ms + 'ms'); });
    };
    /* voce narrante: voce.mp3 se presente, altrimenti la voce di sistema (Web Speech API) */
    const speak = text => new Promise(res => {
      if (!sound || !('speechSynthesis' in window)) return res();
      const u = new SpeechSynthesisUtterance(text); u.lang = 'it-IT'; u.rate = .96;
      const v = speechSynthesis.getVoices().find(v => /^it/i.test(v.lang)); if (v) u.voice = v;
      let done = false, guard, hard;
      const fin = () => { if (done) return; done = true; clearTimeout(guard); clearTimeout(hard); stopSpeak = null; music.volume = .5; res(); };
      guard = setTimeout(fin, 2500);              // la voce non parte (nessuna voce installata)
      hard = setTimeout(fin, 16000);
      u.onstart = () => clearTimeout(guard); u.onend = fin; u.onerror = fin;
      stopSpeak = fin; music.volume = .22; speechSynthesis.cancel(); speechSynthesis.speak(u);
    });
    async function play() {
      const my = ++run; reset();
      if (stopSpeak) stopSpeak();
      if (sound && voceFile) { voceFile.currentTime = 0; voceFile.play().catch(() => { }); }
      const fileMs = sound && voceFile && isFinite(voceFile.duration) && voceFile.duration > 3 ? voceFile.duration * 1000 / steps.length : 0;
      const ms = fileMs || MIN;
      for (let i = 0; i < steps.length; i++) {
        if (my !== run) return;
        showStep(i, ms);
        await Promise.all([sleep(ms), sound && !voceFile ? speak(steps[i].voce) : null]);
      }
      if (my === run) { await sleep(900); if (my === run) endIntro(); }
    }
    function endIntro() {
      if (ended) return; ended = true; run++;
      if ('speechSynthesis' in window) speechSynthesis.cancel();
      if (voceFile) voceFile.pause();
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
        btnAudio.textContent = '🔊 Musica e voce attive';
        music.volume = .5; music.play().catch(() => { });
        play();                                   // riparte dall'inizio, così voce e immagini restano sincronizzate
      } else {
        btnAudio.textContent = '🔇 Audio disattivato';
        music.pause(); if (voceFile) voceFile.pause(); if ('speechSynthesis' in window) speechSynthesis.cancel(); if (stopSpeak) stopSpeak();
      }
    };
    play();

    /* polvere di luce */
    const cv = $('#smoke'), g = cv.getContext('2d');
    const fit = () => { cv.width = innerWidth; cv.height = innerHeight; }; fit(); addEventListener('resize', fit);
    const P = Array.from({ length: 36 }, (_, k) => ({ x: Math.random() * innerWidth, y: Math.random() * innerHeight, r: 30 + Math.random() * 90,
      vx: (Math.random() - .5) * .25, vy: -.08 - Math.random() * .25, c: k % 3 ? '217,178,94' : '77,163,255' }));
    (function loop() {
      if (ended || intro.hidden) return;
      g.clearRect(0, 0, cv.width, cv.height);
      P.forEach(p => {
        p.x += p.vx; p.y += p.vy; if (p.y < -p.r) { p.y = cv.height + p.r; p.x = Math.random() * cv.width; }
        const gr = g.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r); gr.addColorStop(0, 'rgba(' + p.c + ',.11)'); gr.addColorStop(1, 'rgba(' + p.c + ',0)');
        g.fillStyle = gr; g.beginPath(); g.arc(p.x, p.y, p.r, 0, 7); g.fill();
      });
      requestAnimationFrame(loop);
    })();
  }
})();
