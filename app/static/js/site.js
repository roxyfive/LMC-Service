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
      const b = document.createElement('a'); b.className = 'btn btn-red'; b.href = r.data.action === 'prenota' ? '#prenota' : '#preventivo';
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

  /* ---------- intro cinematografica ---------- */
  const intro = $('#intro');
  const lines = JSON.parse($('#introData').textContent || '[]');
  const slides = $$('.slide', intro), line = $('#introLine');
  let timer, audio;
  const endIntro = () => {
    clearInterval(timer); if (audio) audio.pause();
    document.body.style.overflow = '';
    intro.classList.add('out'); setTimeout(() => intro.hidden = true, 800);
    try { sessionStorage.setItem('introSeen', '1'); } catch (e) { }
  };
  try { if (sessionStorage.getItem('introSeen')) intro.hidden = true; } catch (e) { }
  if (!intro.hidden) {
    document.body.style.overflow = 'hidden';
    $('#introSkip').onclick = endIntro;
    const play = () => {
      slides.forEach(s => s.src = s.dataset.src);
      let n = 0;
      const step = () => {
        if (n >= lines.length) return endIntro();
        line.style.animation = 'none'; void line.offsetWidth; line.style.animation = ''; line.textContent = lines[n];
        if (slides.length) { slides.forEach(s => s.classList.remove('on')); slides[n % slides.length].classList.add('on'); }
        n++;
      };
      step(); timer = setInterval(step, 3200);
    };
    $('#introStart').onclick = () => {
      $('#introStart').style.display = 'none';
      audio = new Audio('/static/media/music.mp3'); audio.loop = true; audio.volume = .6;
      audio.play().then(() => { $('#introAudio').textContent = '🔊 Audio'; $('#introAudio').setAttribute('aria-pressed', 'true'); }).catch(() => { });
      play();
    };
    $('#introAudio').onclick = e => {
      if (!audio) return; const b = e.currentTarget;
      if (audio.paused) { audio.play(); b.textContent = '🔊 Audio'; b.setAttribute('aria-pressed', 'true'); } else { audio.pause(); b.textContent = '🔇 Audio'; b.setAttribute('aria-pressed', 'false'); }
    };
    /* fumo / particelle */
    const cv = $('#smoke'), g = cv.getContext('2d');
    const fit = () => { cv.width = innerWidth; cv.height = innerHeight; }; fit(); addEventListener('resize', fit);
    const P = Array.from({ length: 50 }, () => ({ x: Math.random() * innerWidth, y: Math.random() * innerHeight, r: 40 + Math.random() * 90, vx: (Math.random() - .5) * .3, vy: -.1 - Math.random() * .3 }));
    (function loop() {
      if (intro.hidden) return;
      g.clearRect(0, 0, cv.width, cv.height);
      P.forEach(p => {
        p.x += p.vx; p.y += p.vy; if (p.y < -p.r) { p.y = cv.height + p.r; p.x = Math.random() * cv.width; }
        const gr = g.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r); gr.addColorStop(0, 'rgba(255,40,30,.10)'); gr.addColorStop(1, 'rgba(255,40,30,0)');
        g.fillStyle = gr; g.beginPath(); g.arc(p.x, p.y, p.r, 0, 7); g.fill();
      });
      requestAnimationFrame(loop);
    })();
  }
})();
