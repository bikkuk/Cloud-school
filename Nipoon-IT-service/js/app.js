(() => {
  const CONSENT_KEY = 'nk_storage_consent';
  const XP_PER_LEVEL = 100;
  const toastWrap = document.querySelector('[data-toast-wrap]');

  const toast = (msg) => {
    if (!toastWrap) return;
    const el = document.createElement('div');
    el.className = 'toast';
    el.textContent = msg;
    toastWrap.append(el);
    setTimeout(() => el.remove(), 2500);
  };

  const safeJsonParse = (storage, key, fallback) => {
    const raw = storage.getItem(key);
    if (!raw) return fallback;
    try { return JSON.parse(raw); }
    catch { storage.setItem(key, JSON.stringify(fallback)); return fallback; }
  };

  const getConsent = () => localStorage.getItem(CONSENT_KEY);
  const hasConsent = () => getConsent() === 'granted';
  const store = () => hasConsent() ? localStorage : sessionStorage;

  const ensureBanner = () => {
    if (getConsent()) return;
    const b = document.createElement('div');
    b.className = 'consent-banner';
    b.innerHTML = '<p><strong>Datenschutz:</strong> Für Konto, Treuepunkte und Gamification benötigen wir Ihre Zustimmung für dauerhafte Speicherung.</p><div class="actions"><button class="btn btn-primary" data-c="y">Zustimmen</button><button class="btn btn-ghost" data-c="n">Ablehnen</button></div>';
    document.body.append(b);
    b.querySelector('[data-c="y"]').addEventListener('click', () => { localStorage.setItem(CONSENT_KEY, 'granted'); location.reload(); });
    b.querySelector('[data-c="n"]').addEventListener('click', () => { localStorage.setItem(CONSENT_KEY, 'denied'); location.reload(); });
  };

  const readAccounts = () => safeJsonParse(store(), 'nk_accounts', []);
  const writeAccounts = (accounts) => store().setItem('nk_accounts', JSON.stringify(accounts));
  const getCurrentEmail = () => store().getItem('nk_current_user') || '';
  const setCurrentEmail = (email) => store().setItem('nk_current_user', email || '');


  const wireAccountEntryLinks = () => {
    const email = getCurrentEmail();
    const loggedIn = Boolean(email);
    document.querySelectorAll('[data-account-entry]').forEach((el) => {
      el.setAttribute('href', loggedIn ? 'dashboard.html' : 'signup.html');
      el.textContent = loggedIn ? 'Dashboard' : 'Konto erstellen';
      el.setAttribute('aria-label', loggedIn ? 'Dashboard öffnen' : 'Kundenkonto öffnen');
    });
  };

  const getGuestState = () => ({
    points: Number(store().getItem('nk_guest_points') || 0),
    level: Number(store().getItem('nk_guest_level') || 1)
  });
  const setGuestState = (points, level) => {
    store().setItem('nk_guest_points', String(points));
    store().setItem('nk_guest_level', String(level));
  };

  const getActiveState = () => {
    const accounts = readAccounts();
    const email = getCurrentEmail();
    const acc = accounts.find(a => a.email === email);
    if (acc) return { accounts, acc, points: Number(acc.points || 0), level: Number(acc.level || 1) };
    const guest = getGuestState();
    return { accounts, acc: null, points: guest.points, level: guest.level };
  };

  const saveActivePoints = (points, level) => {
    const accounts = readAccounts();
    const email = getCurrentEmail();
    const idx = accounts.findIndex(a => a.email === email);
    if (idx >= 0) {
      accounts[idx].points = points;
      accounts[idx].level = level;
      writeAccounts(accounts);
      return;
    }
    setGuestState(points, level);
  };

  const xpLabel = document.querySelector('[data-xp-label]');
  const lvlLabel = document.querySelector('[data-lvl-label]');
  const progress = document.querySelector('[data-xp-progress]');
  const updateTopbar = () => {
    if (!xpLabel || !lvlLabel || !progress) return;
    const st = getActiveState();
    const current = st.points % XP_PER_LEVEL;
    xpLabel.textContent = `${current} Punkte`;
    lvlLabel.textContent = `${st.acc ? st.acc.name : 'Gast'} · Treue Level ${st.level}`;
    progress.style.width = `${(current / XP_PER_LEVEL) * 100}%`;
  };

  const addPoints = (amount, key) => {
    const flags = new Set(safeJsonParse(sessionStorage, 'nk_points_flags', []));
    if (flags.has(key)) return;
    flags.add(key);
    sessionStorage.setItem('nk_points_flags', JSON.stringify([...flags]));

    const st = getActiveState();
    let points = st.points + amount;
    let level = Math.floor(points / XP_PER_LEVEL) + 1;
    saveActivePoints(points, level);
    updateTopbar();
    toast(`+${amount} Treuepunkte`);
  };

  document.querySelectorAll('[data-section-id]').forEach((sec) => {
    const id = sec.dataset.sectionId;
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          addPoints(5, `sec_${id}`);
          io.disconnect();
        }
      });
    }, { threshold: 0.4 });
    io.observe(sec);
  });
  document.querySelectorAll('.btn-primary').forEach((btn) => btn.addEventListener('click', () => addPoints(10, `cta_${btn.textContent.trim()}`)));
  if (new URLSearchParams(location.search).get('success') === '1') addPoints(25, `submit_${location.pathname}`);

  const signupForm = document.querySelector('#signupForm');
  const loginForm = document.querySelector('#loginForm');
  if (signupForm) {
    signupForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const fd = new FormData(signupForm);
      const name = String(fd.get('name') || '').trim();
      const email = String(fd.get('email') || '').trim().toLowerCase();
      const password = String(fd.get('password') || '');
      const accounts = readAccounts();
      if (accounts.some(a => a.email === email)) return toast('E-Mail bereits registriert');
      const guest = getGuestState();
      accounts.push({ name, email, password, points: guest.points, level: guest.level });
      writeAccounts(accounts);
      setCurrentEmail(email);
      setGuestState(0, 1);
      toast('Konto erstellt. Weiter zum Dashboard.');
      setTimeout(() => location.href = 'dashboard.html', 500);
    });
  }

  if (loginForm) {
    loginForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const fd = new FormData(loginForm);
      const email = String(fd.get('email') || '').trim().toLowerCase();
      const password = String(fd.get('password') || '');
      const acc = readAccounts().find(a => a.email === email && a.password === password);
      if (!acc) return toast('Login fehlgeschlagen');
      setCurrentEmail(acc.email);
      location.href = 'dashboard.html';
    });
  }

  const dashName = document.querySelector('[data-dashboard-name]');
  if (dashName) {
    const st = getActiveState();
    if (!st.acc) {
      location.href = 'signup.html';
      return;
    }
    const note = document.querySelector('[data-dashboard-note]');
    document.querySelector('[data-dashboard-points]').textContent = String(st.points);
    document.querySelector('[data-dashboard-level]').textContent = String(st.level);
    if (st.acc) {
      dashName.textContent = `${st.acc.name} (${st.acc.email})`;
      if (note) note.textContent = 'Sie sind eingeloggt. Ihre Treuepunkte werden angezeigt.';
    } else {
      dashName.textContent = 'Gast';
      if (note) note.textContent = 'Nicht eingeloggt. Bitte Konto erstellen oder einloggen.';
    }
    document.querySelector('[data-dashboard-logout]')?.addEventListener('click', () => {
      setCurrentEmail('');
      toast('Abgemeldet');
      setTimeout(() => location.href = 'signup.html', 300);
    });
  }

  updateTopbar();
  wireAccountEntryLinks();
  ensureBanner();
})();
