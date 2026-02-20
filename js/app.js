(() => {
  const XP_PER_LEVEL = 100;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const toastWrap = document.querySelector('[data-toast-wrap]') || (() => {
    const d = document.createElement('div');
    d.className = 'toast-wrap';
    d.setAttribute('data-toast-wrap', '');
    document.body.append(d);
    return d;
  })();

  const accountState = {
    currentEmail: localStorage.getItem('nk_current_user') || '',
    accounts: JSON.parse(localStorage.getItem('nk_accounts') || '[]')
  };

  const getCurrentAccount = () => accountState.accounts.find(a => a.email === accountState.currentEmail);

  const ensureGuestData = () => {
    if (!localStorage.getItem('nk_guest_points')) localStorage.setItem('nk_guest_points', '0');
    if (!localStorage.getItem('nk_guest_level')) localStorage.setItem('nk_guest_level', '1');
  };
  ensureGuestData();

  const xpState = {
    points: 0,
    level: 1
  };

  const xpLabel = document.querySelector('[data-xp-label]');
  const lvlLabel = document.querySelector('[data-lvl-label]');
  const progress = document.querySelector('[data-xp-progress]');

  const saveAccountState = () => {
    localStorage.setItem('nk_accounts', JSON.stringify(accountState.accounts));
    localStorage.setItem('nk_current_user', accountState.currentEmail || '');
  };

  const savePoints = () => {
    const acc = getCurrentAccount();
    if (acc) {
      acc.points = xpState.points;
      acc.level = xpState.level;
      saveAccountState();
    } else {
      localStorage.setItem('nk_guest_points', String(xpState.points));
      localStorage.setItem('nk_guest_level', String(xpState.level));
    }
  };

  const hydratePoints = () => {
    const acc = getCurrentAccount();
    if (acc) {
      xpState.points = Number(acc.points || 0);
      xpState.level = Number(acc.level || 1);
    } else {
      xpState.points = Number(localStorage.getItem('nk_guest_points') || 0);
      xpState.level = Number(localStorage.getItem('nk_guest_level') || 1);
    }
  };

  const sessionFlags = new Set(JSON.parse(sessionStorage.getItem('nk_points_flags') || '[]'));
  const saveSession = () => sessionStorage.setItem('nk_points_flags', JSON.stringify([...sessionFlags]));

  const toast = (msg) => {
    const el = document.createElement('div');
    el.className = 'toast';
    el.textContent = msg;
    toastWrap.append(el);
    setTimeout(() => el.remove(), 2600);
  };

  const updateUI = () => {
    if (!xpLabel || !lvlLabel || !progress) return;
    const current = xpState.points % XP_PER_LEVEL;
    const acc = getCurrentAccount();
    xpLabel.textContent = `${current} Punkte`;
    lvlLabel.textContent = acc ? `${acc.name} · Treue Level ${xpState.level}` : `Gast · Treue Level ${xpState.level}`;
    progress.style.width = `${(current / XP_PER_LEVEL) * 100}%`;
  };

  const confettiBurst = () => {
    if (reducedMotion) return;
    const canvas = document.createElement('canvas');
    canvas.className = 'confetti-canvas';
    document.body.append(canvas);
    const ctx = canvas.getContext('2d');
    canvas.width = innerWidth;
    canvas.height = innerHeight;
    const pieces = Array.from({ length: 85 }, () => ({ x: innerWidth / 2, y: innerHeight * .35, vx: (Math.random() - .5) * 6, vy: -Math.random() * 7, g: .13, s: Math.random() * 4 + 2, c: ['#ff73c3', '#53d9ff', '#a6f4c5', '#ffe58f'][Math.floor(Math.random() * 4)] }));
    let frame = 0;
    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      pieces.forEach(p => { p.vy += p.g; p.x += p.vx; p.y += p.vy; ctx.fillStyle = p.c; ctx.fillRect(p.x, p.y, p.s, p.s); });
      frame += 1;
      if (frame < 75) requestAnimationFrame(render); else canvas.remove();
    };
    render();
  };

  const addPoints = (amount, reasonKey, oncePerSession = false) => {
    if (oncePerSession && sessionFlags.has(reasonKey)) return;
    if (oncePerSession) sessionFlags.add(reasonKey);
    xpState.points += amount;
    const nextLevel = Math.floor(xpState.points / XP_PER_LEVEL) + 1;
    if (nextLevel > xpState.level) {
      xpState.level = nextLevel;
      toast(`Badge freigeschaltet: Treue Level ${xpState.level}`);
      confettiBurst();
    }
    toast(`+${amount} Treuepunkte`);
    savePoints();
    saveSession();
    updateUI();
    updateQuest();
  };

  const injectAccountModal = () => {
    if (document.querySelector('[data-account-modal]')) return;
    const wrap = document.createElement('div');
    wrap.className = 'modal';
    wrap.setAttribute('data-account-modal', '');
    wrap.innerHTML = `
      <div class="modal-panel">
        <div class="modal-head"><h3>Kundenkonto</h3><button class="close-btn" type="button" data-account-close aria-label="Schließen">×</button></div>
        <p class="muted">Konto lokal im Browser gespeichert. Ihre Treuepunkte bleiben erhalten.</p>
        <div class="card-grid">
          <form class="form-wrap" data-register-form>
            <h4>Neu registrieren</h4>
            <label>Name<input name="name" required></label>
            <label>E-Mail<input type="email" name="email" required></label>
            <label>Passwort<input type="password" name="password" minlength="4" required></label>
            <button class="btn btn-primary" type="submit">Konto erstellen</button>
          </form>
          <form class="form-wrap" data-login-form>
            <h4>Anmelden</h4>
            <label>E-Mail<input type="email" name="email" required></label>
            <label>Passwort<input type="password" name="password" minlength="4" required></label>
            <button class="btn btn-ghost" type="submit">Einloggen</button>
          </form>
        </div>
        <div class="actions">
          <button class="btn btn-ghost" type="button" data-account-logout>Abmelden</button>
        </div>
      </div>`;
    document.body.append(wrap);
  };

  const bindAccountUi = () => {
    injectAccountModal();
    const modal = document.querySelector('[data-account-modal]');
    const openers = document.querySelectorAll('[data-account-open]');
    const close = modal.querySelector('[data-account-close]');

    const closeModal = () => modal.classList.remove('open');
    openers.forEach(btn => btn.addEventListener('click', () => modal.classList.add('open')));
    close.addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });

    modal.querySelector('[data-register-form]').addEventListener('submit', (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const name = String(fd.get('name') || '').trim();
      const email = String(fd.get('email') || '').trim().toLowerCase();
      const password = String(fd.get('password') || '');
      if (accountState.accounts.some(a => a.email === email)) return toast('E-Mail bereits registriert');
      accountState.accounts.push({ name, email, password, points: xpState.points, level: xpState.level });
      accountState.currentEmail = email;
      saveAccountState();
      toast('Konto erstellt – Treuepunkte verknüpft');
      updateUI();
      closeModal();
    });

    modal.querySelector('[data-login-form]').addEventListener('submit', (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const email = String(fd.get('email') || '').trim().toLowerCase();
      const password = String(fd.get('password') || '');
      const acc = accountState.accounts.find(a => a.email === email && a.password === password);
      if (!acc) return toast('Login fehlgeschlagen');
      accountState.currentEmail = acc.email;
      hydratePoints();
      saveAccountState();
      updateUI();
      toast(`Willkommen zurück, ${acc.name}`);
      closeModal();
    });

    modal.querySelector('[data-account-logout]').addEventListener('click', () => {
      accountState.currentEmail = '';
      hydratePoints();
      saveAccountState();
      updateUI();
      toast('Abgemeldet');
      closeModal();
    });
  };

  const observed = document.querySelectorAll('[data-section-id]');
  if ('IntersectionObserver' in window) {
    const obs = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          addPoints(5, `section_${entry.target.dataset.sectionId}`, true);
          obs.unobserve(entry.target);
        }
      });
    }, { threshold: 0.4 });
    observed.forEach(el => obs.observe(el));
  }

  document.querySelectorAll('.btn-primary').forEach(btn => {
    btn.addEventListener('click', () => addPoints(10, `cta_${btn.textContent.trim()}`, true));
  });

  const success = new URLSearchParams(window.location.search).get('success');
  if (success === '1') {
    const target = document.querySelector('[data-form-success]');
    if (target) {
      target.hidden = false;
      target.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'center' });
    }
    addPoints(25, `submit_${window.location.pathname}`, true);
  }

  const modal = document.querySelector('[data-cta-modal]');
  const openers = document.querySelectorAll('[data-open-modal]');
  const close = document.querySelector('[data-close-modal]');
  const closeModal = () => modal?.classList.remove('open');
  openers.forEach(o => o.addEventListener('click', () => modal?.classList.add('open')));
  close?.addEventListener('click', closeModal);
  modal?.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeModal(); });

  const questSteps = {
    pick: sessionStorage.getItem('quest_pick') === '1',
    request: sessionStorage.getItem('quest_request') === '1',
    call: sessionStorage.getItem('quest_call') === '1'
  };

  document.querySelectorAll('[data-quest="pick"]').forEach(el => el.addEventListener('click', () => { questSteps.pick = true; sessionStorage.setItem('quest_pick', '1'); updateQuest(); }));
  document.querySelectorAll('[data-quest="request"]').forEach(el => el.addEventListener('click', () => { questSteps.request = true; sessionStorage.setItem('quest_request', '1'); updateQuest(); }));
  document.querySelectorAll('[data-quest="call"]').forEach(el => el.addEventListener('click', () => { questSteps.call = true; sessionStorage.setItem('quest_call', '1'); updateQuest(); }));

  function updateQuest() {
    const map = [['pick', '[data-quest-step="pick"]', 'Paket auswählen'], ['request', '[data-quest-step="request"]', 'Anfrage senden'], ['call', '[data-quest-step="call"]', 'Termin sichern']];
    map.forEach(([key, selector, label]) => {
      const node = document.querySelector(selector);
      if (!node) return;
      node.classList.toggle('done', questSteps[key]);
      node.textContent = `${questSteps[key] ? '✓' : '○'} ${label}`;
    });
    if (questSteps.pick && questSteps.request && questSteps.call && !sessionFlags.has('quest_complete')) {
      addPoints(20, 'quest_complete', true);
      toast('Badge freigeschaltet: Quest abgeschlossen');
    }
  }

  hydratePoints();
  bindAccountUi();
  updateUI();
  updateQuest();
})();
