// ========= State =========
const state = {
  data: { categories: [], skills: [] },
  activeCat: 'all',
  query: '',
  sort: 'stars',   // 'stars' | 'forks' | 'name' | 'new'
  rankSort: 'stars', // Top 5 panel: 'stars' | 'forks'
  catMap: {}
};

// ========= Category auto-rules (for adder) =========
const CAT_RULES = [
  { cat: 'korea',      kws: ['korea', 'korean', '한국', 'hangul', 'hwp', 'kakao', 'toss', 'srt', 'ktx', 'naver', 'kbo', 'kr-', 'k-skill', 'legalize'] },
  { cat: 'finance',    kws: ['finance', 'trading', 'quant', 'stock', 'invest', 'bank', 'equity', 'portfolio', 'crypto', 'forex'] },
  { cat: 'research',   kws: ['research', 'paper', 'academic', 'notebooklm', 'knowledge', 'graph', 'scientific', 'deep-research'] },
  { cat: 'video',      kws: ['video', 'remotion', 'hyperframes', 'ffmpeg', 'subtitle', 'dubbing', 'motion graphic'] },
  { cat: 'design',     kws: ['design', ' ui', 'ux', 'slide', 'presentation', 'novel', 'writing', 'humaniz', 'creative'] },
  { cat: 'automation', kws: ['playwright', 'browser', 'automation', 'ccpm', 'spec', 'harness', 'jira', 'slack', 'lark'] },
  { cat: 'legal',      kws: ['legal', 'compliance', 'contract', 'nda', 'law'] },
  { cat: 'career',     kws: ['career', 'resume', 'job-search', 'interview', 'hr'] },
  { cat: 'business',   kws: ['business', 'marketing', 'seo', 'geo', 'ceo', 'sales', 'cro', 'exec', 'startup'] },
  { cat: 'workflow',   kws: ['workflow', 'superpower', 'planning', 'memory', 'mem', 'agent', 'skill', 'plugin', 'tdd'] }
];
function classify(meta) {
  const hay = [meta.name, meta.full_name, meta.description, (meta.topics || []).join(' ')]
    .filter(Boolean).join(' ').toLowerCase();
  for (const rule of CAT_RULES) {
    if (rule.kws.some(k => hay.includes(k))) return rule.cat;
  }
  return 'workflow';
}

// ========= Category icons (SVG, line style to match chevrons) =========
// 카테고리·필터 id → 라인 아이콘. 이모지 대신 currentColor 기반 SVG를 쓴다.
const CAT_ICON_PATHS = {
  // 메타: AI 에이전트팀 구축
  harness:    '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
  workflow:   '<path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/>',
  token:      '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
  automation: '<path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/>',
  korea:      '<circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/>',
  // 메타: 비즈니스 성장
  business:   '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>',
  finance:    '<path d="M3 3v16a2 2 0 0 0 2 2h16"/><path d="m19 9-5 5-4-4-3 3"/>',
  geo:        '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
  // 메타: 실행력 제고
  research:   '<path d="M3 3v18h18"/><rect x="7" y="11" width="3" height="7" rx="0.5"/><rect x="12" y="7" width="3" height="11" rx="0.5"/><rect x="17" y="4" width="3" height="14" rx="0.5"/>',
  design:     '<circle cx="13.5" cy="6.5" r=".9" fill="currentColor" stroke="none"/><circle cx="17.5" cy="10.5" r=".9" fill="currentColor" stroke="none"/><circle cx="8.5" cy="7.5" r=".9" fill="currentColor" stroke="none"/><circle cx="6.5" cy="12.5" r=".9" fill="currentColor" stroke="none"/><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.555C21.965 6.012 17.461 2 12 2z"/>',
  video:      '<path d="m16 13 5.223 3.482a.5.5 0 0 0 .777-.416V7.87a.5.5 0 0 0-.752-.432L16 10.5"/><rect x="2" y="6" width="14" height="12" rx="2"/>',
  writing:    '<path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
  legal:      '<path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="M7 21h10"/><path d="M12 3v18"/><path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/>',
  career:     '<circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/>',
  // 상단 필터
  all:  '<rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="14" y="3" rx="1"/><rect width="7" height="7" x="14" y="14" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/>',
  pick: '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
  lab:  '<path d="M17 8h1a4 4 0 1 1 0 8h-1"/><path d="M3 8h14v9a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4Z"/><line x1="6" x2="6" y1="2" y2="4"/><line x1="10" x2="10" y1="2" y2="4"/><line x1="14" x2="14" y1="2" y2="4"/>'
};
function catIcon(id, cls) {
  const p = CAT_ICON_PATHS[id];
  if (!p) return '';
  return `<svg class="cat-ico${cls ? ' ' + cls : ''}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${p}</svg>`;
}

// ========= Theme =========
const THEME_KEY = 'airoasting.theme';
function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  document.querySelectorAll('.icon-sun').forEach(el => { el.style.display = theme === 'light' ? '' : 'none'; });
  document.querySelectorAll('.icon-moon').forEach(el => { el.style.display = theme === 'dark'  ? '' : 'none'; });
  try { localStorage.setItem(THEME_KEY, theme); } catch (e) {}
}
function initTheme() {
  let saved = null;
  try { saved = localStorage.getItem(THEME_KEY); } catch(e) {}
  applyTheme(saved === 'dark' ? 'dark' : 'light');
  const toggle = () => {
    const next = document.documentElement.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
    applyTheme(next);
  };
  document.getElementById('themeBtn')?.addEventListener('click', toggle);
  document.getElementById('themeBtnDrawer')?.addEventListener('click', toggle);
}

// ========= Load =========
async function load() {
  initTheme();
  let loaded = false;
  try {
    const res = await fetch('skills.json?v=' + Date.now(), { cache: 'no-store' });
    if (res.ok) { state.data = await res.json(); loaded = true; }
  } catch (e) { /* fall through to inline fallback */ }
  if (!loaded) {
    const inline = document.getElementById('skills-data');
    if (inline) {
      try { state.data = JSON.parse(inline.textContent); loaded = true; } catch (e) {}
    }
  }
  if (!loaded) {
    document.getElementById('feed').innerHTML =
      `<div class="empty">skills.json을 불러올 수 없습니다.<br/>로컬에서 열 때는 <code>python3 -m http.server</code>로 실행해 주세요.</div>`;
    return;
  }
  state.catMap = Object.fromEntries(state.data.categories.map(c => [c.id, c]));
  state.authors = state.data.authors || {};
  applyCatFromUrl({ replace: true });
  renderCats();
  renderAll();
  wireTabs();
  wireDrawer();
  wireAbout();
  window.addEventListener('popstate', () => {
    applyCatFromUrl({ replace: false });
    highlightActiveCat();
    renderAll();
  });
}

// ========= URL routing =========
function isValidCat(id) {
  if (!id) return false;
  if (id === 'all' || id === 'pick' || id === 'lab') return true;
  return !!state.catMap[id];
}
function readCatFromUrl() {
  try {
    const params = new URLSearchParams(window.location.search);
    return params.get('cat');
  } catch (e) { return null; }
}
function applyCatFromUrl({ replace }) {
  const raw = readCatFromUrl();
  const id = isValidCat(raw) ? raw : 'all';
  state.activeCat = id;
  // Normalize URL: drop ?cat=all so the bare URL stays clean
  if (replace) {
    const params = new URLSearchParams(window.location.search);
    const current = params.get('cat');
    if (id === 'all' && current !== null) {
      params.delete('cat');
      const qs = params.toString();
      const url = window.location.pathname + (qs ? '?' + qs : '') + window.location.hash;
      history.replaceState(null, '', url);
    } else if (current !== id && id !== 'all') {
      params.set('cat', id);
      history.replaceState(null, '', window.location.pathname + '?' + params.toString() + window.location.hash);
    }
  }
}
function pushCatToUrl(id) {
  const params = new URLSearchParams(window.location.search);
  if (id === 'all') params.delete('cat'); else params.set('cat', id);
  const qs = params.toString();
  const url = window.location.pathname + (qs ? '?' + qs : '') + window.location.hash;
  if (url === window.location.pathname + window.location.search + window.location.hash) return;
  history.pushState(null, '', url);
}

// ========= Nav =========
function renderCats() {
  const counts = { all: state.data.skills.length, pick: 0, lab: 0 };
  for (const c of state.data.categories) counts[c.id] = 0;
  for (const s of state.data.skills) {
    counts[s.category] = (counts[s.category] || 0) + 1;
    if (s.editors_pick) counts.pick++;
    if (s.airoasting_lab) counts.lab++;
  }
  const metas = state.data.meta_categories || [];
  const renderCatLink = c =>
    `<a data-cat="${c.id}" tabindex="0" role="button">
       <span class="cat-label">${catIcon(c.id)}${escapeHtml(c.name)}</span>
       <span class="count">${counts[c.id] || 0}</span>
     </a>`;
  state.collapsed = state.collapsed || {};
  const buildCatsHtml = () => {
    if (metas.length) {
      return metas.map(m => {
        const cats = state.data.categories.filter(c => c.meta === m.id);
        if (!cats.length) return '';
        const collapsed = state.collapsed[m.id] ? ' collapsed' : '';
        return `<div class="meta-group${collapsed}" data-meta="${m.id}">
          <button type="button" class="meta-group-label" aria-expanded="${state.collapsed[m.id] ? 'false' : 'true'}">
            <svg class="meta-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg>
            <span>${escapeHtml(m.name)}</span>
          </button>
          <div class="meta-group-body">
            ${cats.map(renderCatLink).join('')}
          </div>
        </div>`;
      }).join('');
    }
    return state.data.categories.map(renderCatLink).join('');
  };
  const catsHtml = buildCatsHtml();
  ['nav-cats', 'drawer-cats'].forEach(id => {
    const host = document.getElementById(id);
    if (host) host.innerHTML = catsHtml;
  });

  // Wire clicks on every category link (sidebar + drawer)
  document.querySelectorAll('#nav-cats a, #drawer-cats a').forEach(a =>
    a.addEventListener('click', () => setCat(a.dataset.cat))
  );
  // Wire meta-group toggle buttons
  document.querySelectorAll('.meta-group-label').forEach(btn => {
    btn.addEventListener('click', () => {
      const group = btn.closest('.meta-group');
      const metaId = group?.dataset?.meta;
      if (!metaId) return;
      state.collapsed[metaId] = !state.collapsed[metaId];
      // Toggle all matching groups (sidebar + drawer)
      document.querySelectorAll(`.meta-group[data-meta="${metaId}"]`).forEach(g => {
        g.classList.toggle('collapsed', state.collapsed[metaId]);
        const b = g.querySelector('.meta-group-label');
        if (b) b.setAttribute('aria-expanded', state.collapsed[metaId] ? 'false' : 'true');
      });
    });
  });
  // Feeds (all/pick/lab) in sidebar + drawer
  document.querySelectorAll('.sidebar-left [data-cat="all"], .sidebar-left [data-cat="pick"], .sidebar-left [data-cat="lab"], .drawer [data-cat="all"], .drawer [data-cat="pick"], .drawer [data-cat="lab"]').forEach(a => {
    a.addEventListener('click', () => setCat(a.dataset.cat));
  });

  // Update counts in any location (IDs for sidebar legacy, data-count for drawer)
  const setCount = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  };
  setCount('count-all', counts.all);
  setCount('count-pick', counts.pick);
  setCount('count-lab', counts.lab);
  document.querySelectorAll('[data-count="all"]').forEach(el => el.textContent = counts.all);
  document.querySelectorAll('[data-count="pick"]').forEach(el => el.textContent = counts.pick);
  document.querySelectorAll('[data-count="lab"]').forEach(el => el.textContent = counts.lab);
  document.getElementById('totalNum').textContent = counts.all;
  highlightActiveCat();
}

function setCat(id) {
  state.activeCat = id;
  pushCatToUrl(id);
  highlightActiveCat();
  renderAll();
  closeDrawer();
}
function highlightActiveCat() {
  document.querySelectorAll('.sidebar-left .nav a, .drawer .nav a').forEach(a => {
    a.classList.toggle('active', a.dataset.cat === state.activeCat);
  });
}

// ========= Drawer =========
function openDrawer() {
  const d = document.getElementById('drawer');
  const b = document.getElementById('drawerBackdrop');
  const btn = document.getElementById('hamburgerBtn');
  if (!d || !b) return;
  b.hidden = false;
  requestAnimationFrame(() => {
    d.classList.add('open');
    b.classList.add('open');
  });
  d.setAttribute('aria-hidden', 'false');
  btn?.setAttribute('aria-expanded', 'true');
  document.body.style.overflow = 'hidden';
}
function closeDrawer() {
  const d = document.getElementById('drawer');
  const b = document.getElementById('drawerBackdrop');
  const btn = document.getElementById('hamburgerBtn');
  if (!d || !b) return;
  d.classList.remove('open');
  b.classList.remove('open');
  d.setAttribute('aria-hidden', 'true');
  btn?.setAttribute('aria-expanded', 'false');
  document.body.style.overflow = '';
  setTimeout(() => { if (!d.classList.contains('open')) b.hidden = true; }, 260);
}
function wireDrawer() {
  document.getElementById('hamburgerBtn')?.addEventListener('click', openDrawer);
  document.getElementById('drawerClose')?.addEventListener('click', closeDrawer);
  document.getElementById('drawerBackdrop')?.addEventListener('click', closeDrawer);
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && document.getElementById('drawer')?.classList.contains('open')) {
      closeDrawer();
    }
  });
}

// ========= About modal =========
function openAbout() {
  const b = document.getElementById('aboutBackdrop');
  if (!b) return;
  b.hidden = false;
  requestAnimationFrame(() => b.classList.add('open'));
  document.body.style.overflow = 'hidden';
}
function closeAbout() {
  const b = document.getElementById('aboutBackdrop');
  if (!b) return;
  b.classList.remove('open');
  document.body.style.overflow = '';
  setTimeout(() => { if (!b.classList.contains('open')) b.hidden = true; }, 220);
}
function wireAbout() {
  const b = document.getElementById('aboutBackdrop');
  document.getElementById('aboutBtn')?.addEventListener('click', openAbout);
  document.getElementById('aboutLink')?.addEventListener('click', e => { e.preventDefault(); openAbout(); });
  document.getElementById('aboutBtnDrawer')?.addEventListener('click', () => { closeDrawer(); openAbout(); });
  document.getElementById('repoBtnDrawer')?.addEventListener('click', () => { closeDrawer(); });
  document.getElementById('aboutClose')?.addEventListener('click', closeAbout);
  b?.addEventListener('click', e => { if (e.target === b) closeAbout(); });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && b?.classList.contains('open')) closeAbout();
  });
}

// ========= Tabs / Sort =========
function wireTabs() {
  document.querySelectorAll('.tabs .tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tabs .tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      state.sort = tab.dataset.sort;
      const hint = { stars: '★ 스타순', forks: '⑂ 포크순', name: 'A-Z' };
      document.getElementById('sortHint').textContent = hint[state.sort] || '';
      renderAll();
    });
  });
  document.querySelectorAll('.rank-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      state.rankSort = pill.dataset.rank;
      renderRank();
    });
  });
}

// ========= Filter & Sort =========
function filtered() {
  const q = state.query.trim().toLowerCase();
  let items = state.data.skills.slice();
  if (state.activeCat === 'pick') {
    items = items.filter(s => s.editors_pick);
  } else if (state.activeCat === 'lab') {
    items = items.filter(s => s.airoasting_lab);
  } else if (state.activeCat !== 'all') {
    items = items.filter(s => s.category === state.activeCat);
  }
  if (q) items = items.filter(s =>
    (s.name + ' ' + (s.desc||'') + ' ' + (s.tags||[]).join(' ') + ' ' + (s.author||'') + ' ' + (s.repo||''))
      .toLowerCase().includes(q)
  );
  const sorter = {
    stars: (a,b) => (b.stars||0) - (a.stars||0),
    forks: (a,b) => (b.forks||0) - (a.forks||0),
    name:  (a,b) => a.name.localeCompare(b.name, 'ko')
  }[state.sort] || ((a,b) => (b.stars||0) - (a.stars||0));
  items.sort((a,b) => (b.pinned?1:0) - (a.pinned?1:0) || sorter(a,b));
  return items;
}

// ========= Render =========
function renderAll() {
  const items = filtered();
  renderHeroTitle();
  renderCatIntro();
  renderFeatured(items[0]);
  renderFeed(items.slice(1));
  renderRank();
  updateTotalNum();
}

function renderHeroTitle() {
  const h1 = document.querySelector('.hero h1');
  if (!h1) return;
  const id = state.activeCat;
  if (id === 'all') {
    h1.innerHTML = '비즈니스 리더를 위해<br/>엄선한 AI 스킬';
    return;
  }
  const builtin = {
    pick: "Editor's Pick",
    lab: 'AI Roasting'
  };
  const cat = state.catMap[id];
  const text = builtin[id] || (cat ? cat.name : '');
  if (!text) {
    h1.innerHTML = '비즈니스 리더를 위해<br/>엄선한 AI 스킬';
    return;
  }
  h1.textContent = text;
}

function updateTotalNum() {
  const el = document.getElementById('totalNum');
  if (!el) return;
  const id = state.activeCat;
  const skills = state.data.skills;
  const n = id === 'all' ? skills.length
    : id === 'pick' ? skills.filter(s => s.editors_pick).length
    : id === 'lab' ? skills.filter(s => s.airoasting_lab).length
    : skills.filter(s => s.category === id).length;
  el.textContent = n;
}

function renderCatIntro() {
  const host = document.getElementById('catIntro');
  if (!host) return;
  const id = state.activeCat;
  const introByBuiltin = {
    all:  { emoji: '✨', name: '전체 스킬', desc: '지금까지 등록된 모든 스킬을 한자리에서 둘러볼 수 있어요.' },
    pick: { emoji: '✦', name: "Editor's Pick", desc: '' },
    lab:  { emoji: '☕', name: 'AI Roasting', desc: 'AI Roasting이 직접 만들어 공개한 자체 스킬 모음이에요. 비즈니스 현장에서 검증한 흐름을 그대로 옮겨 담았어요.' }
  };
  const cat = introByBuiltin[id] || state.catMap[id];
  host.classList.toggle('cat-intro-long', id === 'pick');
  host.classList.toggle('cat-intro-lab', id === 'lab');
  if (id === 'pick') {
    host.hidden = false;
    host.innerHTML = `
      <div class="cat-intro-head">
        ${catIcon('pick', 'cat-intro-ico')}
        <strong>Editor's Pick 선정 기준</strong>
      </div>
      <p class="pick-lede">이 라이브러리는 비개발자 비즈니스 리더를 위해 만들어졌습니다. 그래서 에디터 픽도 <strong>효용성·대표성·신뢰성</strong> 세 축을 각 5점 만점으로 평가해 <strong>평균 4점을 넘는 스킬</strong>에만 배지를 답니다. 효용성은 비개발자가 당일 업무에 바로 쓸 수 있는지, 대표성은 같은 카테고리에서 가장 먼저 추천할 만한지, 신뢰성은 별 수와 저자 이력, 유지보수 활동이 믿을 만한지를 봅니다.</p>`;
    return;
  }
  if (!cat || !cat.desc) { host.hidden = true; host.innerHTML = ''; return; }
  host.hidden = false;
  host.innerHTML = `${catIcon(id, 'cat-intro-ico')}<span><strong>${escapeHtml(cat.name)}</strong>${escapeHtml(cat.desc)}</span>`;
}

function renderFeatured(s) {
  const host = document.getElementById('featured');
  if (!s) { host.innerHTML = ''; return; }
  const cat = state.catMap[s.category];
  const linkUrl = s.url || (s.repo ? `https://github.com/${s.repo}` : '#');
  host.innerHTML = `
    <a class="featured${s.editors_pick ? ' featured-pick' : ' featured-plain'}${s.author === 'airoasting' ? ' featured-airoasting' : ''}" href="${escapeHtml(linkUrl)}" target="_blank" rel="noopener" aria-label="${escapeHtml(s.name)}">
      <div class="avatar${s.author === 'airoasting' ? ' avatar-airoasting' : ''}">${avatarImg(s)}</div>
      <div>
        <h2>${escapeHtml(s.name)} ${s.editors_pick ? `<span class="badge-pick">✦ PICK</span>` : ''} <span class="author-pill"><span>${escapeHtml(s.author || '—')}</span>${authorBadges(s.author)}</span></h2>
        <div class="author">
          ${cat ? `<span class="cat-pill">${catIcon(cat.id, 'cat-pill-ico')}${escapeHtml(cat.name)}</span>` : ''}
        </div>
        <p>${escapeHtml(s.desc || '')}</p>
        <div class="tags" style="display:flex; flex-wrap:wrap; gap:6px;">${(s.tags||[]).slice(0,3).map(t => `<span class="tag">${escapeHtml(t)}</span>`).join('')}</div>
      </div>
      <div class="stars">
        <strong>${fmt(s.stars)}</strong><span>stars</span>
      </div>
      <div class="forks">
        <strong>${fmt(s.forks)}</strong><span>forks</span>
      </div>
    </a>`;
}

function renderFeed(items) {
  const host = document.getElementById('feed');
  if (!items.length) {
    host.innerHTML = `<div class="empty">조건에 맞는 스킬이 없습니다.</div>`;
    return;
  }
  host.innerHTML = items.map((s, i) => card(s, i + 2)).join('');
}

function card(s, rank) {
  const cat = state.catMap[s.category];
  const tags = (s.tags || []).slice(0, 3).map(t => `<span class="tag">${escapeHtml(t)}</span>`).join('');
  const badge = (s.editors_pick ? `<span class="badge-pick">✦ PICK</span>` : '');
  const repoUrl = s.url || (s.repo ? `https://github.com/${s.repo}` : '#');
  return `
    <a class="card${s.editors_pick ? ' card-pick' : ''}${s.author === 'airoasting' ? ' card-airoasting' : ''}" href="${repoUrl}" target="_blank" rel="noopener" aria-label="${escapeHtml(s.name)}">
      <div class="rank">${String(rank).padStart(2,'0')}</div>
      <div class="avatar${s.author === 'airoasting' ? ' avatar-airoasting' : ''}">${avatarImg(s)}</div>
      <div class="body">
        <h3>${escapeHtml(s.name)} ${badge} <span class="author-pill"><span>${escapeHtml(s.author || '—')}</span>${authorBadges(s.author)}</span></h3>
        <div class="meta-row">
          ${cat ? `<span class="cat-pill">${catIcon(cat.id, 'cat-pill-ico')}${escapeHtml(cat.name)}</span>` : ''}
        </div>
        <p class="desc">${escapeHtml(s.desc || '')}</p>
        <div class="tags">${tags}</div>
      </div>
      <div class="stars"><strong>${fmt(s.stars)}</strong>stars</div>
      <div class="forks"><strong>${fmt(s.forks)}</strong>forks</div>
    </a>`;
}

function renderRank() {
  const host = document.getElementById('topRank');
  const key = state.rankSort === 'forks' ? 'forks' : 'stars';
  const top = state.data.skills.slice().sort((a,b) => (b[key]||0) - (a[key]||0)).slice(0, 5);
  host.innerHTML = top.map((s, i) => {
    const url = s.url || (s.repo ? `https://github.com/${s.repo}` : '#');
    return `
    <a class="rank-row" href="${escapeHtml(url)}" target="_blank" rel="noopener" aria-label="${escapeHtml(s.name)}">
      <div class="r-num">${String(i+1).padStart(2,'0')}</div>
      <div class="r-av">${avatarImg(s)}</div>
      <div class="r-info">
        <div class="name">${escapeHtml(s.name)}</div>
        <div class="author">${escapeHtml(s.author || '')}</div>
      </div>
      <div class="star">${key === 'forks' ? `⑂${fmt(s.forks)}<span class="fork-mini"> · ★${fmt(s.stars)}</span>` : `★${fmt(s.stars)}<span class="fork-mini"> · ⑂${fmt(s.forks)}</span>`}</div>
    </a>`;
  }).join('');
  document.querySelectorAll('.rank-pill').forEach(p => {
    p.classList.toggle('active', p.dataset.rank === key);
  });
}


// ========= Helpers =========
function isNew(s) {
  if (!s.pushed_at) return false;
  const days = (Date.now() - new Date(s.pushed_at).getTime()) / 86400000;
  return days <= 14;
}
function fmt(n) {
  if (n == null) return '—';
  if (n >= 100000) return (n / 1000).toFixed(0) + 'k';
  if (n >= 1000)   return (n / 1000).toFixed(1) + 'k';
  return String(n);
}
function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function fbBadgeInline(url) {
  if (!url) return '';
  const safe = escapeHtml(url);
  return `<span class="fb-inline" role="link" tabindex="0" title="만든 사람 페이스북" onclick="event.preventDefault(); event.stopPropagation(); window.open('${safe}','_blank','noopener');"><svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M22 12a10 10 0 1 0-11.56 9.88v-6.99H7.9V12h2.54V9.8c0-2.5 1.49-3.89 3.77-3.89 1.09 0 2.24.2 2.24.2v2.46h-1.26c-1.24 0-1.63.77-1.63 1.56V12h2.77l-.44 2.89h-2.33v6.99A10 10 0 0 0 22 12z"/></svg></span>`;
}
function fmtDate(s) {
  if (!s) return '';
  const d = new Date(s);
  if (isNaN(d)) return escapeHtml(s);
  return `${d.getFullYear()}.${String(d.getMonth()+1).padStart(2,'0')}.${String(d.getDate()).padStart(2,'0')}`;
}
function fbBadge(url) {
  if (!url) return '';
  const safe = escapeHtml(url);
  return `<span class="fb-link" role="link" tabindex="0" title="만든 사람 페이스북" onclick="event.preventDefault(); event.stopPropagation(); window.open('${safe}','_blank','noopener');"><svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M22 12a10 10 0 1 0-11.56 9.88v-6.99H7.9V12h2.54V9.8c0-2.5 1.49-3.89 3.77-3.89 1.09 0 2.24.2 2.24.2v2.46h-1.26c-1.24 0-1.63.77-1.63 1.56V12h2.77l-.44 2.89h-2.33v6.99A10 10 0 0 0 22 12z"/></svg></span>`;
}
function liBadge(url) {
  if (!url) return '';
  const safe = escapeHtml(url);
  return `<span class="li-link" role="link" tabindex="0" title="만든 사람 링크드인" onclick="event.preventDefault(); event.stopPropagation(); window.open('${safe}','_blank','noopener');"><svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M20.45 20.45h-3.56v-5.57c0-1.33-.03-3.04-1.85-3.04-1.86 0-2.14 1.45-2.14 2.95v5.66H9.34V9h3.42v1.56h.05c.48-.9 1.64-1.85 3.38-1.85 3.61 0 4.28 2.38 4.28 5.47v6.27zM5.34 7.43a2.07 2.07 0 1 1 0-4.14 2.07 2.07 0 0 1 0 4.14zM7.12 20.45H3.56V9h3.56v11.45zM22.23 0H1.77C.79 0 0 .78 0 1.73v20.54C0 23.22.79 24 1.77 24h20.46c.98 0 1.77-.78 1.77-1.73V1.73C24 .78 23.21 0 22.23 0z"/></svg></span>`;
}
function xBadge(url) {
  if (!url) return '';
  const safe = escapeHtml(url);
  return `<span class="x-link" role="link" tabindex="0" title="만든 사람 X" onclick="event.preventDefault(); event.stopPropagation(); window.open('${safe}','_blank','noopener');"><svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg></span>`;
}
function authorBadges(author) {
  const a = (state.authors || {})[author];
  if (!a) return '';
  return fbBadge(a.facebook) + liBadge(a.linkedin) + xBadge(a.x || a.twitter);
}
function avatarImg(s) {
  const owner = s.avatar_owner || (s.repo || '').split('/')[0];
  if (!owner) return '';
  if (owner === 'airoasting') {
    return `<img src="asset/logo1-transparent.png" alt="" loading="lazy" onerror="this.style.display='none'" />`;
  }
  const url = `https://github.com/${owner}.png?size=88`;
  return `<img src="${url}" alt="" loading="lazy" onerror="this.style.display='none'" />`;
}
let toastTimer;
function toast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('show'), 2200);
}

// ========= Search & keys =========
document.getElementById('q').addEventListener('input', e => {
  state.query = e.target.value; renderAll();
});
document.addEventListener('keydown', e => {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault(); document.getElementById('q').focus();
  }
  if (e.key === 'Escape') {
    const q = document.getElementById('q');
    if (document.activeElement === q) { q.value = ''; state.query = ''; renderAll(); }
  }
});

load();
