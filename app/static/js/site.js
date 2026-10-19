(function () {
  'use strict';
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
    const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const csrfMeta = $('meta[name=csrf]');
  const send = (url, data) => fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfMeta.content }, body: JSON.stringify(data) });
  const post = async (url, data) => {
    try {
      let r = await send(url, data);
      if (r.status === 400) {          // token scaduto: ne chiede uno nuovo e ritenta
        const t = await (await fetch('/api/csrf', { cache: 'no-store' })).json();
        if (t.token) { csrfMeta.content = t.token; r = await send(url, data); }
      }
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

  /* ---------- configurazione pubblica (nessun segreto) ---------- */
  let CFG = { wa_ready: false, admin: false, vapi: { enabled: false }, emergency: { on: false }, contact_wa: '' };
  const cfgReady = fetch('/api/config', { cache: 'no-store' }).then(r => r.json()).then(c => { CFG = c; return c; }).catch(() => CFG);

  /* ---------- chat + assistente vocale ---------- */
  const chat = $('#chat'), log = $('#chatLog'), act = $('#chatAct'), inp = $('#chatIn'), chatBtn = $('#chatBtn');
  const voiceBtn = $('#voiceBtn'), vapiBtn = $('#vapiBtn'), waBtn = $('#waBtn'), waForm = $('#waForm'), vStatus = $('#voiceStatus');
  const toggleChat = open => { chat.hidden = !open; chatBtn.setAttribute('aria-expanded', open); if (open) { inp.focus(); initTools(); } else stopVoice(); };
  chatBtn.onclick = () => toggleChat(chat.hidden);
  $('#chatX').onclick = () => { toggleChat(false); chatBtn.focus(); };
  const hist = [];
  const add = (cls, t) => { const p = document.createElement('p'); p.className = cls; p.textContent = t; log.appendChild(p); log.scrollTop = log.scrollHeight; };
  const setStatus = t => { vStatus.hidden = !t; vStatus.textContent = t || ''; };

  async function ask(text) {
    if (!text.trim()) return '';
    add('me', text); hist.push({ role: 'user', content: text }); act.innerHTML = '';
    const r = await post('/api/chat', { messages: hist });
    const reply = r.ok ? r.data.reply : 'Al momento non riesco a rispondere. Usa la sezione Contatti.';
    add('bot', reply); hist.push({ role: 'assistant', content: reply });
    if (r.ok && r.data.action) {
      const b = document.createElement('a'); b.className = 'btn btn-gold'; b.href = r.data.action === 'prenota' ? '#prenota' : '#preventivo';
      b.textContent = r.data.action === 'prenota' ? 'Prenota ora' : 'Richiedi preventivo'; b.onclick = () => toggleChat(false); act.appendChild(b);
    }
    showSummaryBtn(r.ok && !!r.data.action);
    return reply;
  }
  $('#chatForm').addEventListener('submit', e => { e.preventDefault(); const t = inp.value; inp.value = ''; ask(t); });

  /* dettatura singola (microfono nel campo di testo) */
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition, mic = $('#mic');
  if (SR) {
    const rec = new SR(); rec.lang = 'it-IT'; rec.interimResults = false;
    rec.onresult = e => ask(e.results[0][0].transcript); rec.onend = () => mic.classList.remove('rec');
    mic.onclick = () => { try { mic.classList.add('rec'); rec.start(); } catch (e) { mic.classList.remove('rec'); } };
  } else mic.style.display = 'none';

  /* conversazione a voce: ascolta (riconoscimento del browser) -> risponde -> legge la risposta -> ascolta ancora.
     Parte SOLO quando il cliente tocca "Parla con l'assistente"; la sintesi vocale del browser è la base, Vapi dà una voce più naturale. */
  const synth = window.speechSynthesis;
  let voiceOn = false, curRec = null, tts = null;
  const pickVoice = () => {
    const vs = (synth ? synth.getVoices() : []).filter(v => /^it/i.test(v.lang));
    return vs.find(v => /(natural|neural|online|premium)/i.test(v.name)) || vs.find(v => /(google|elsa|isabella|alice|luca|cosimo)/i.test(v.name)) || vs[0] || null;
  };
  const speak = text => new Promise(res => {
    if (!synth) return res();
    const u = new SpeechSynthesisUtterance(text.replace(/https?:\/\/\S+/g, '').replace(/\s+/g, ' '));
    u.lang = 'it-IT'; u.rate = .98; const v = pickVoice(); if (v) u.voice = v;
    let done = false; const fin = () => { if (!done) { done = true; clearTimeout(tm); tts = null; res(); } };
    const tm = setTimeout(fin, 25000); u.onend = fin; u.onerror = fin; tts = fin;
    synth.cancel(); synth.speak(u);
  });
  const listenOnce = () => new Promise(res => {
    const r = new SR(); curRec = r; r.lang = 'it-IT'; r.interimResults = false; r.maxAlternatives = 1;
    let out = '', err = '';
    r.onresult = e => { out = e.results[0][0].transcript; };
    r.onerror = e => { err = e.error; };
    r.onend = () => { curRec = null; res({ text: out, err }); };
    try { r.start(); } catch (e) { res({ text: '', err: 'start' }); }
  });
  function stopVoice(msg) {
    voiceOn = false; voiceBtn.setAttribute('aria-pressed', 'false'); voiceBtn.textContent = '🎙️ Parla con l\'assistente';
    if (curRec) { try { curRec.abort(); } catch (e) { } } if (synth) synth.cancel(); if (tts) tts(); setStatus(msg || '');
    if (vapiCall) { try { vapiCall.stop(); } catch (e) { } vapiCall = null; if (vapiBtn) vapiBtn.setAttribute('aria-pressed', 'false'); }
  }
  async function voiceLoop() {
    let silent = 0;
    while (voiceOn) {
      setStatus('Ti ascolto… parla pure');
      const { text, err } = await listenOnce();
      if (!voiceOn) return;
      if (err === 'not-allowed' || err === 'service-not-allowed') return stopVoice('Il microfono è bloccato: consentilo nelle impostazioni del browser, oppure scrivi.');
      if (!text) { if (++silent >= 2) return stopVoice('Non ti sento: tocca di nuovo "Parla con l\'assistente" per riprovare.'); continue; }
      silent = 0; setStatus('Sto pensando…');
      const reply = await ask(text);
      if (!voiceOn) return;
      setStatus('Sto rispondendo…'); await speak(reply);
    }
  }
  voiceBtn.onclick = async () => {
    if (voiceOn) return stopVoice();
    if (!SR) { add('bot', 'Il tuo browser non supporta il riconoscimento vocale: usa Chrome, Edge o Safari, oppure scrivi qui sotto.'); return; }
    if (!window.isSecureContext) { add('bot', 'Il microfono funziona solo su connessione sicura (https). Puoi scrivere qui sotto.'); return; }
    voiceOn = true; voiceBtn.setAttribute('aria-pressed', 'true'); voiceBtn.textContent = '⏹ Termina conversazione vocale';
    if (synth && !synth.getVoices().length) await new Promise(r => { synth.onvoiceschanged = r; setTimeout(r, 600); });
    voiceLoop();
  };

  /* voce naturale con Vapi (solo se configurato in Admin); il SDK si scarica solo al tocco */
  let vapiCall = null, vapiLoaded = null;
  const loadVapi = () => vapiLoaded || (vapiLoaded = new Promise((res, rej) => {
    const sc = document.createElement('script'); sc.src = '/static/vendor/vapi-web.js'; sc.onload = () => res(window.VapiWeb); sc.onerror = () => rej(new Error('vapi')); document.head.appendChild(sc);
  }));
  async function startVapi(emergency) {
    const c = await cfgReady; if (!c.vapi.enabled) return false;
    try {
      const Vapi = await loadVapi(); const v = new Vapi(c.vapi.public_key); vapiCall = v;
      setStatus('Mi collego all\'assistente vocale…');
      v.on('call-start', () => { setStatus('In linea: parla pure. Tocca di nuovo per terminare.'); if (vapiBtn) vapiBtn.setAttribute('aria-pressed', 'true'); });
      v.on('call-end', () => { vapiCall = null; setStatus(''); if (vapiBtn) vapiBtn.setAttribute('aria-pressed', 'false'); });
      v.on('message', m => { if (m && m.type === 'transcript' && m.transcriptType === 'final' && m.transcript) { const me = m.role === 'user'; add(me ? 'me' : 'bot', m.transcript); hist.push({ role: me ? 'user' : 'assistant', content: m.transcript }); showSummaryBtn(false); } });
      v.on('error', () => { vapiCall = null; setStatus(''); add('bot', 'La voce naturale non è disponibile in questo momento: puoi usare la conversazione vocale standard o scrivere.'); });
      await v.start((emergency && c.vapi.emergency_assistant_id) || c.vapi.assistant_id);
      return true;
    } catch (e) { vapiCall = null; setStatus(''); add('bot', 'Non riesco ad avviare la voce naturale. Uso la conversazione vocale standard.'); return false; }
  }
  vapiBtn.onclick = async () => { if (vapiCall) return stopVoice(); if (voiceOn) stopVoice(); if (!(await startVapi(false))) voiceBtn.click(); };

  /* riepilogo su WhatsApp */
  let summaryShown = false;
  function showSummaryBtn(highlight) {
    const users = hist.filter(m => m.role === 'user').length;
    if (users < 1 || !waBtn) return; waBtn.hidden = false;
    waBtn.classList.toggle('pulse', highlight || users >= 3);
  }
  async function initTools() {
    if (summaryShown) return; summaryShown = true;
    const c = await cfgReady;
    vapiBtn.hidden = !c.vapi.enabled;
    if (!c.wa_ready && c.admin) {          // chi gestisce il sito vede come attivarlo
      waBtn.textContent = 'Configura WhatsApp'; waBtn.dataset.admin = '1';
    }
  }
  waBtn.onclick = () => { if (waBtn.dataset.admin) { location.href = '/admin/impostazioni#wa'; return; } waForm.hidden = !waForm.hidden; if (!waForm.hidden) waForm.phone.focus(); };
  waForm.addEventListener('submit', async e => {
    e.preventDefault(); const m = $('#waMsg');
    const d = Object.fromEntries(new FormData(waForm)); d.consent = waForm.consent.checked; d.messages = hist;
    if (!d.phone.trim() || !d.consent) { m.textContent = 'Inserisci il telefono e dai il consenso.'; m.className = 'msg err'; return; }
    const r = await post('/api/chat/riepilogo', d);
    if (!r.ok) { m.textContent = r.data.error || 'Invio non riuscito, riprova.'; m.className = 'msg err'; return; }
    waForm.hidden = true; waBtn.hidden = true;
    if (r.data.configured && r.data.sent > 0) add('bot', 'Perfetto! Ho inviato il riepilogo al team su WhatsApp: ti richiamiamo al più presto.');
    else {
      add('bot', 'Ho registrato la tua richiesta. Per essere più veloce puoi anche scriverci direttamente su WhatsApp con il riepilogo già pronto:');
      if (r.data.wa_link) { const a = document.createElement('a'); a.className = 'btn btn-gold'; a.href = r.data.wa_link; a.target = '_blank'; a.rel = 'noopener'; a.textContent = 'Apri WhatsApp'; act.innerHTML = ''; act.appendChild(a); }
    }
  });

  /* ---------- pulsante Emergenza 24h ---------- */
  (function () {
    const sos = $('#sos'), sheet = $('#sosSheet'); if (!sos || !sheet) return;
    const form = $('#sosForm'), msg = $('#sosMsg'), vbtn = $('#sosVapi');
    const open = () => { sheet.hidden = false; document.body.style.overflow = 'hidden'; $('.sheet-call', sheet).focus(); };
    const close = () => { sheet.hidden = true; document.body.style.overflow = ''; sos.focus(); };
    sos.addEventListener('click', e => { e.preventDefault(); open(); });
    $('#sosX').onclick = close; sheet.addEventListener('click', e => { if (e.target === sheet) close(); });
    document.addEventListener('keydown', e => { if (!sheet.hidden && e.key === 'Escape') close(); });
    cfgReady.then(c => { if (c.vapi.enabled) vbtn.hidden = false; if (c.emergency && c.emergency.open_now === false) sos.classList.add('closed'); });
    vbtn.onclick = async () => { close(); toggleChat(true); if (!(await startVapi(true))) add('bot', 'Per un’urgenza chiama direttamente il numero indicato nel pulsante rosso.'); };
    form.addEventListener('submit', async e => {
      e.preventDefault(); const d = Object.fromEntries(new FormData(form));
      if (!d.phone.trim()) { msg.textContent = 'Inserisci il numero su cui richiamarti.'; msg.className = 'msg err'; return; }
      msg.textContent = 'Invio in corso…'; msg.className = 'msg';
      const r = await post('/api/emergenza', d);
      if (r.ok) { msg.textContent = r.data.configured && r.data.sent > 0 ? 'Richiesta inviata: chi è di turno ti richiama subito.' : 'Richiesta registrata. Se è urgente chiama anche il numero qui sopra.'; msg.className = 'msg ok'; form.reset(); }
      else { msg.textContent = r.data.error || 'Invio non riuscito: chiama il numero indicato.'; msg.className = 'msg err'; }
    });
    if (/[?&]sos=1/.test(location.search)) setTimeout(open, 400);   // scorciatoia dell'app installata
  })();

  /* ---------- configuratore evento (nessun prezzo: prepara la richiesta di preventivo) ---------- */
  (function () {
    const root = $('#conf'); if (!root) return;
    const val = { tipo: '', ospiti: '', servizi: new Set() }, out = $('#confOut'), go = $('#confGo');
    const HINT = {
      Audio: 'impianto audio dimensionato su sala e pubblico, microfoni e regia', Luci: 'luci d\'atmosfera e scenografiche con programmazione',
      Video: 'ledwall/proiezioni e regia video', Allestimenti: 'palco, strutture e allestimento scenico', Videosorveglianza: 'telecamere e controllo degli spazi',
      Progettazione: 'progetto tecnico su misura con sopralluogo'
    };
    const render = () => {
      const s = [...val.servizi]; go.disabled = !(val.tipo && s.length);
      if (!val.tipo || !s.length) { out.innerHTML = '<p class="mut">Seleziona almeno tipo di evento e servizi: qui comparirà la tua proposta.</p>'; return; }
      out.innerHTML = '<h3>La tua proposta di partenza</h3><p><b>' + val.tipo + '</b>' + (val.ospiti ? ' · ' + val.ospiti + ' ospiti' : '') + '</p><ul>' +
        s.map(x => '<li>' + (HINT[x] || x) + '</li>').join('') + '</ul><p class="mut">Verrà inserita nelle note del preventivo: la rifiniamo insieme dopo il tuo messaggio.</p>';
    };
    $$('.opts', root).forEach(g => g.addEventListener('click', e => {
      const b = e.target.closest('.opt'); if (!b) return; const name = g.dataset.name, v = b.dataset.v, multi = g.classList.contains('multi');
      if (multi) { const on = b.getAttribute('aria-pressed') !== 'true'; b.setAttribute('aria-pressed', on); on ? val.servizi.add(v) : val.servizi.delete(v); }
      else { $$('.opt', g).forEach(x => x.setAttribute('aria-pressed', 'false')); b.setAttribute('aria-pressed', 'true'); val[name] = v; }
      render();
    }));
    go.onclick = () => {
      const f = $('#quoteForm'), s = [...val.servizi];
      const sel = f.event_type; if ([...sel.options].some(o => o.value === val.tipo || o.text === val.tipo)) sel.value = val.tipo;
      $$('input[name=services]', f).forEach(c => { c.checked = s.includes(c.value); });
      const g = { 'Fino a 50': 50, '50–150': 100, '150–400': 250, 'Oltre 400': 500 }[val.ospiti]; if (g) f.guests.value = g;
      f.notes.value = 'Configurazione dal sito: ' + val.tipo + (val.ospiti ? ', ospiti ' + val.ospiti : '') + '. Servizi: ' + s.map(x => (HINT[x] ? x + ' (' + HINT[x] + ')' : x)).join('; ') + '.';
      $('#preventivo').scrollIntoView({ behavior: 'smooth', block: 'start' });
    };
  })();

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

  /* ---------- contatori animati ---------- */
  (function () {
    const nums = $$('.num[data-to]'); if (!nums.length) return;
    const fmt = (el, v) => { el.textContent = v.toLocaleString('it-IT') + (el.dataset.suffix || ''); };
    const cio = new IntersectionObserver(es => es.forEach(e => {
      if (!e.isIntersecting) return; cio.unobserve(e.target);
      const el = e.target, to = +el.dataset.to, t0 = performance.now(), D = 1700;
      if (reduce) return fmt(el, to);
      (function step(t) { const k = Math.min(1, (t - t0) / D), v = Math.round(to * (1 - Math.pow(1 - k, 3))); fmt(el, v); if (k < 1) requestAnimationFrame(step); })(t0);
    }), { threshold: .6 });
    nums.forEach(n => { n.setAttribute('aria-label', n.textContent); if (!reduce) fmt(n, 0); cio.observe(n); });
  })();

  /* ---------- particelle dorate nella hero (leggere: sprite pre-renderizzato, pausa fuori vista) ---------- */
  (function () {
    const cv = $('#heroFx'), hero = $('#hero'); if (!cv || reduce) return;
    const g = cv.getContext('2d'), sprite = document.createElement('canvas'); sprite.width = sprite.height = 32;
    const sg = sprite.getContext('2d'), gr = sg.createRadialGradient(16, 16, 0, 16, 16, 16);
    gr.addColorStop(0, 'rgba(255,236,190,1)'); gr.addColorStop(.35, 'rgba(230,207,154,.45)'); gr.addColorStop(1, 'rgba(230,207,154,0)');
    sg.fillStyle = gr; sg.fillRect(0, 0, 32, 32);
    let W = 0, H = 0, P = [], run = false, last = 0;
    const N = () => (innerWidth < 700 ? 14 : 30);
    const fit = () => { W = cv.width = hero.clientWidth; H = cv.height = hero.clientHeight;
      P = Array.from({ length: N() }, () => ({ x: Math.random() * W, y: Math.random() * H, r: 3 + Math.random() * 8, vy: 6 + Math.random() * 14, vx: (Math.random() - .5) * 6, ph: Math.random() * 6.28, a: .25 + Math.random() * .5 })); };
    fit(); addEventListener('resize', fit);
    const frame = t => {
      if (!run) return; const dt = Math.min(.05, (t - last) / 1000); last = t;
      g.clearRect(0, 0, W, H);
      for (const p of P) {
        p.y -= p.vy * dt; p.x += p.vx * dt; p.ph += dt * 1.6; if (p.y < -20) { p.y = H + 20; p.x = Math.random() * W; }
        g.globalAlpha = p.a * (.55 + .45 * Math.sin(p.ph)); g.drawImage(sprite, p.x - p.r, p.y - p.r, p.r * 2, p.r * 2);
      }
      requestAnimationFrame(frame);
    };
    const upd = vis => { const go = vis && !document.hidden; if (go && !run) { run = true; last = performance.now(); requestAnimationFrame(frame); } else if (!go) run = false; };
    let vis = true; new IntersectionObserver(es => { vis = es[0].isIntersecting; upd(vis); }, { threshold: .05 }).observe(hero);
    document.addEventListener('visibilitychange', () => upd(vis));
  })();

  /* ---------- intro: musica + didascalie animate (voce.mp3 e voce.json solo se presenti) ---------- */
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
      bars = $$('#introBars i'), btnAudio = $('#introAudio'), txtAudio = $('#introAudioTxt'), btnSkip = $('#introSkip');
    const music = $('#introMusic'), voce = $('#introVoce'), cues = data.cues || [];
    const STEP = 4800, MUSIC_VOL = .75, DUCK_VOL = .2, sleep = ms => new Promise(r => setTimeout(r, ms));
    let sound = false, run = 0, cur = -1, ended = false, fade = null;
    setTimeout(() => slides.forEach(s => { if (!s.src && s.dataset.src) s.src = s.dataset.src; }), 500);
    btnSkip.focus({ preventScroll: true });

    /* volume con dissolvenza (su iOS il volume è fisso: lì la musica resta al livello pieno) */
    const fadeTo = (el, v, ms = 600) => {
      if (!el) return; clearInterval(fade); const from = el.volume, n = Math.max(1, ms / 40); let k = 0;
      fade = setInterval(() => { k++; el.volume = Math.min(1, Math.max(0, from + (v - from) * k / n)); if (k >= n) clearInterval(fade); }, 40);
    };
    const label = (t, state) => { txtAudio.textContent = t; btnAudio.dataset.state = state; btnAudio.setAttribute('aria-pressed', state === 'on'); };
    music.addEventListener('error', () => { sound = false; label('♪ Audio non disponibile · riprova', 'error'); });

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
      const withVoice = sound && voce && !voce.error;
      if (withVoice) { voce.currentTime = 0; try { await voce.play(); fadeTo(music, DUCK_VOL, 500); } catch (e) { } }
      const dur = withVoice && isFinite(voce.duration) ? voce.duration : 0;
      for (let i = 0; i < steps.length; i++) {
        if (my !== run) return;
        let ms = STEP;
        if (withVoice && dur > 3) {   // con la voce: ogni slide dura quanto la sua frase (cue da voce.json, altrimenti parti uguali)
          const t0 = cues.length === steps.length ? cues[i] : dur * i / steps.length;
          const t1 = i + 1 < steps.length ? (cues.length === steps.length ? cues[i + 1] : dur * (i + 1) / steps.length) : dur + .6;
          ms = Math.max(1200, (t1 - Math.max(t0, voce.currentTime || 0)) * 1000);
        }
        showStep(i, ms); await sleep(ms);
      }
      if (my === run) { await sleep(700); if (my === run) endIntro(); }
    }
    function endIntro() {
      if (ended) return; ended = true; run++;
      if (voce) voce.pause();
      clearInterval(fade); const f = setInterval(() => { music.volume = Math.max(0, music.volume - .05); if (music.volume <= .01) { music.pause(); clearInterval(f); } }, 60);
      intro.classList.add('out'); document.body.style.overflow = '';
      setTimeout(ready, 350);                      // il titolo della hero parte mentre la "tenda" si alza
      setTimeout(() => { intro.hidden = true; }, 1500);
      try { sessionStorage.setItem('introSeen', '1'); } catch (e) { }
    }
    btnSkip.onclick = endIntro;
    document.addEventListener('keydown', e => { if (!ended && e.key === 'Escape') endIntro(); });
    if (voce) voce.addEventListener('ended', () => fadeTo(music, MUSIC_VOL, 800));

    btnAudio.onclick = async () => {
      btnAudio.classList.add('live');
      if (sound) {                                  // spegni
        sound = false; music.pause(); if (voce) voce.pause(); label('♪ Audio disattivato · tocca per riattivare', 'off'); return;
      }
      try {
        music.volume = voce ? DUCK_VOL : MUSIC_VOL; music.currentTime = 0;
        label('♪ Caricamento audio…', 'loading');
        const started = new Promise((res, rej) => {        // "attivo" solo quando il suono parte davvero
          const done = ok => { clearTimeout(tm); music.removeEventListener('playing', yes); music.removeEventListener('error', no); ok ? res() : rej(new Error('audio')); };
          const yes = () => done(true), no = () => done(false), tm = setTimeout(no, 9000);
          music.addEventListener('playing', yes); music.addEventListener('error', no);
          if (!music.paused && music.readyState > 2 && music.currentTime > 0) yes();
        });
        await music.play();
        await started;
        sound = true; label('♪ Audio attivo · tocca per spegnere', 'on');
        if (voce) play();                           // con la voce si riparte da capo: immagini e frasi restano sincronizzate
      } catch (e) {
        sound = false; music.pause(); label('♪ Audio non riproducibile · riprova', 'error');
      }
    };
    play();
  }
})();
