(() => {
  const XP_PER_LEVEL = 100;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const xpState = {
    xp: Number(localStorage.getItem('xp') || 0),
    level: Number(localStorage.getItem('level') || 1)
  };
  const sessionFlags = new Set(JSON.parse(sessionStorage.getItem('xp_flags') || '[]'));

  const xpLabel = document.querySelector('[data-xp-label]');
  const lvlLabel = document.querySelector('[data-lvl-label]');
  const progress = document.querySelector('[data-xp-progress]');
  const toastWrap = document.querySelector('[data-toast-wrap]');

  const saveState = () => {
    localStorage.setItem('xp', String(xpState.xp));
    localStorage.setItem('level', String(xpState.level));
    sessionStorage.setItem('xp_flags', JSON.stringify([...sessionFlags]));
  };

  const updateUI = () => {
    if (!xpLabel || !lvlLabel || !progress) return;
    const currentXP = xpState.xp % XP_PER_LEVEL;
    xpLabel.textContent = `${currentXP} XP`;
    lvlLabel.textContent = `Lvl ${xpState.level}`;
    progress.style.width = `${(currentXP / XP_PER_LEVEL) * 100}%`;
  };

  const toast = (msg) => {
    if (!toastWrap) return;
    const el = document.createElement('div');
    el.className = 'toast';
    el.textContent = msg;
    toastWrap.append(el);
    setTimeout(() => el.remove(), 2500);
  };

  const confettiBurst = () => {
    if (reducedMotion) return;
    const canvas = document.createElement('canvas');
    canvas.className = 'confetti-canvas';
    document.body.append(canvas);
    const ctx = canvas.getContext('2d');
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    const pieces = Array.from({ length: 90 }, () => ({
      x: window.innerWidth / 2,
      y: window.innerHeight * 0.35,
      vx: (Math.random() - 0.5) * 6,
      vy: Math.random() * -6 - 2,
      g: 0.12,
      s: Math.random() * 5 + 2,
      c: ['#ff73c3', '#53d9ff', '#a6f4c5', '#ffe58f'][Math.floor(Math.random() * 4)]
    }));

    let frame = 0;
    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      pieces.forEach(p => {
        p.vy += p.g;
        p.x += p.vx;
        p.y += p.vy;
        ctx.fillStyle = p.c;
        ctx.fillRect(p.x, p.y, p.s, p.s);
      });
      frame += 1;
      if (frame < 75) requestAnimationFrame(render);
      else canvas.remove();
    };
    render();
  };

  const addXP = (amount, reasonKey, oncePerSession = false) => {
    if (oncePerSession && sessionFlags.has(reasonKey)) return;
    if (oncePerSession) sessionFlags.add(reasonKey);
    xpState.xp += amount;
    const nextLevel = Math.floor(xpState.xp / XP_PER_LEVEL) + 1;
    if (nextLevel > xpState.level) {
      xpState.level = nextLevel;
      toast(`Badge freigeschaltet: Level ${xpState.level}`);
      confettiBurst();
    }
    toast(`+${amount} XP`);
    updateUI();
    saveState();
    updateQuest();
  };

  const observed = document.querySelectorAll('[data-section-id]');
  if ('IntersectionObserver' in window) {
    const obs = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          addXP(5, `section_${entry.target.dataset.sectionId}`, true);
          obs.unobserve(entry.target);
        }
      });
    }, { threshold: 0.4 });
    observed.forEach(el => obs.observe(el));
  }

  document.querySelectorAll('.btn-primary').forEach(btn => {
    btn.addEventListener('click', () => addXP(10, `cta_${btn.textContent.trim()}`, true));
  });

  const success = new URLSearchParams(window.location.search).get('success');
  if (success === '1') {
    const target = document.querySelector('[data-form-success]');
    if (target) {
      target.hidden = false;
      target.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'center' });
    }
    addXP(25, `submit_${window.location.pathname}`, true);
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
  document.querySelectorAll('[data-quest="pick"]').forEach(el => el.addEventListener('click', () => {
    questSteps.pick = true; sessionStorage.setItem('quest_pick', '1'); updateQuest();
  }));
  document.querySelectorAll('[data-quest="request"]').forEach(el => el.addEventListener('click', () => {
    questSteps.request = true; sessionStorage.setItem('quest_request', '1'); updateQuest();
  }));
  document.querySelectorAll('[data-quest="call"]').forEach(el => el.addEventListener('click', () => {
    questSteps.call = true; sessionStorage.setItem('quest_call', '1'); updateQuest();
  }));

  function updateQuest() {
    const map = [
      ['pick', '[data-quest-step="pick"]', 'Paket auswählen'],
      ['request', '[data-quest-step="request"]', 'Anfrage senden'],
      ['call', '[data-quest-step="call"]', 'Termin sichern']
    ];
    map.forEach(([key, selector, label]) => {
      const node = document.querySelector(selector);
      if (!node) return;
      node.classList.toggle('done', questSteps[key]);
      node.textContent = `${questSteps[key] ? '✓' : '○'} ${label}`;
    });
    if (questSteps.pick && questSteps.request && questSteps.call && !sessionFlags.has('quest_complete')) {
      addXP(20, 'quest_complete', true);
      toast('Badge freigeschaltet: Quest abgeschlossen');
    }
  }

  updateUI();
  updateQuest();
})();
