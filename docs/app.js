/* 스킬 라이브러리 — MCP 허브와 같은 Patchbay 디자인.
   데이터 원본은 skills.json 하나. index.html 안의 #skills-data 는 file:// 로 열 때 쓰는 사본이다.
   카드 수, 카테고리 수, 에디터픽 수는 전부 데이터에서 계산한다. 손으로 세지 않는다.
   주소: ?cat=pick · ?cat=lab 은 모아 보기 필터, ?cat=<카테고리 id> 는 그 섹션으로 이동. */

const QUICK_PICKS = ["PPT", "리서치", "투자", "마케팅", "영상"];
const FILTERS = {
  pick: {
    label: "Editor's Pick",
    test: s => !!s.editors_pick,
    note: "<b>Editor's Pick 선정 기준.</b> 효용성·대표성·신뢰성 세 축을 각 5점 만점으로 평가해 평균 4점을 넘는 스킬에만 배지를 답니다. 효용성은 비개발자가 당일 업무에 바로 쓸 수 있는지, 대표성은 같은 카테고리에서 가장 먼저 추천할 만한지, 신뢰성은 별 수와 저자 이력, 유지보수 활동이 믿을 만한지를 봅니다.",
  },
  lab: {
    label: "AI Roasting",
    test: s => !!s.airoasting_lab,
    note: "<b>AI Roasting.</b> AI Roasting이 직접 만들어 공개한 스킬 모음입니다. 비즈니스 현장에서 검증한 흐름을 그대로 옮겨 담았습니다.",
  },
};

/* sort — cat: 카테고리 섹션으로 묶고 섹션 안은 스타순 · stars / forks: 섹션 없이 한 목록.
   한 목록일 때 카테고리 칩은 이동이 아니라 필터로 동작한다 */
const SORTS = { cat: "카테고리순", stars: "스타순", forks: "포크순" };
const state = { query: "", category: "all", filter: "all", sort: "cat" };
let CATS = [], METAS = [], ALL = [], CAT_BY_ID = {};

const $ = id => document.getElementById(id);
const reduceMotion = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmtK = n => n >= 100000 ? Math.round(n / 1000) + "k"
  : n >= 1000 ? (n / 1000).toFixed(1).replace(/\.0$/, "") + "k" : String(n ?? 0);

/* GitHub Octicons: star-fill, repo-forked */
const ICON_STAR = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z"/></svg>';
const ICON_FORK = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M5 5.372v.878c0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75v-.878a2.25 2.25 0 1 1 1.5 0v.878a2.25 2.25 0 0 1-2.25 2.25h-1.5v2.128a2.251 2.251 0 1 1-1.5 0V8.5h-1.5A2.25 2.25 0 0 1 3.5 6.25v-.878a2.25 2.25 0 1 1 1.5 0ZM5 3.25a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Zm6.75.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm-3 8.75a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Z"/></svg>';
const ICON_PATCH = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>';

/* ---- data ---- */
async function loadData() {
  try {
    const res = await fetch("skills.json?v=" + Date.now(), { cache: "no-store" });
    if (res.ok) return await res.json();
  } catch (e) { /* file:// 등. 인라인 사본으로 넘어간다 */ }
  try {
    const d = JSON.parse($("skills-data").textContent);
    if (d && d.skills) return d;
  } catch (e) {}
  return null;
}

function enrich(s) {
  const owner = s.avatar_owner || (s.repo || "").split("/")[0];
  const cat = CAT_BY_ID[s.category];
  return {
    ...s,
    owner,
    url: s.url || "https://github.com/" + s.repo,
    avatar: owner === "airoasting" ? "asset/favicon-256.png" : "https://github.com/" + owner + ".png?size=96",
    mono: (s.name || "?").trim().charAt(0).toUpperCase(),
    /* 이름·설명뿐 아니라 저자, 저장소, 태그, 카테고리 이름으로도 찾는다 */
    hay: [s.name, s.desc, s.author, s.repo, (s.tags || []).join(" "), cat ? cat.name : ""].join(" ").toLowerCase(),
  };
}

function inFilter(items) {
  const f = FILTERS[state.filter];
  return f ? items.filter(f.test) : items;
}
function countByCat(items) {
  const m = {};
  items.forEach(s => { m[s.category] = (m[s.category] || 0) + 1; });
  return m;
}

/* ---- signature: skill spectrum ---- */
function renderMeters() {
  const counts = countByCat(ALL);
  const max = Math.max(...CATS.map(c => counts[c.id] || 0));
  const groups = METAS.length ? METAS : [{ id: null, name: "" }];
  $("meters").innerHTML = groups.map(m => {
    const cats = CATS.filter(c => m.id === null || c.meta === m.id);
    if (!cats.length) return "";
    return `<div class="mgroup" style="flex:${cats.length}">
      <div class="mbars">${cats.map(c => {
        const n = counts[c.id] || 0;
        return `<button class="meter" data-cat="${esc(c.id)}" title="${esc(c.name)} ${n}개" aria-label="${esc(c.name)} ${n}개 보기">
          <span class="mval">${n}</span>
          <span class="bar" style="height:100%"><span class="fill" data-h="${Math.round((n / max) * 100)}"></span></span>
          <span class="mlbl">${esc(c.short || c.name)}</span>
        </button>`;
      }).join("")}</div>
      ${m.name ? `<div class="mcap" title="${esc(m.name)}">${esc(m.name)}</div>` : ""}
    </div>`;
  }).join("");
}

/* ---- render ---- */
function renderChips() {
  const pool = inFilter(ALL);
  const counts = countByCat(pool);
  const chips = [{ id: "all", name: "전체", n: pool.length }]
    .concat(CATS.map(c => ({ id: c.id, name: c.short || c.name, full: c.name, n: counts[c.id] || 0 })));
  $("chips").innerHTML = chips.map(c => {
    const on = state.category === c.id;
    return `<button class="chip${on ? " active" : ""}" data-cat="${esc(c.id)}" aria-pressed="${on}"${c.full ? ` title="${esc(c.full)}"` : ""}${c.n ? "" : " disabled"}>${esc(c.name)}<span class="cnt">${c.n}</span></button>`;
  }).join("");
  /* 좁은 화면의 가로 스크롤 칩 바에서 켜진 칩이 보이게 한다 (바 안에서만 움직인다) */
  const bar = $("catalog"), active = bar.querySelector(".chip.active");
  if (active && bar.scrollWidth > bar.clientWidth) {
    const left = active.offsetLeft - (bar.clientWidth - active.offsetWidth) / 2;
    bar.scrollTo({ left: Math.max(0, left), behavior: reduceMotion() ? "auto" : "smooth" });
  }
}

function renderQuick() {
  document.querySelectorAll("#quick button").forEach(b => {
    const on = state.query === b.dataset.q;
    b.classList.toggle("active", on);
    b.setAttribute("aria-pressed", on);
  });
  document.querySelectorAll("#filters button, .legend [data-filter]").forEach(b => {
    const on = state.filter === b.dataset.filter;
    b.classList.toggle("active", on);
    b.setAttribute("aria-pressed", on);
  });
}

function renderSearchAffordance() {
  const hasQuery = state.query.trim().length > 0;
  $("clear").hidden = !hasQuery;
  $("kbd-hint").hidden = hasQuery;
}

function renderNotice() {
  const el = $("notice"), f = FILTERS[state.filter];
  el.hidden = !f;
  if (!f) { el.innerHTML = ""; return; }
  el.className = "notice" + (state.filter === "lab" ? " lab" : "");
  el.innerHTML = `<p>${f.note}</p><button type="button" id="notice-off">전체 보기</button>`;
  $("notice-off").addEventListener("click", () => setFilter("all"));
}

function modHTML(m, showCat) {
  const cat = CAT_BY_ID[m.category];
  const flag = m.editors_pick ? `<span class="flag"><span class="led led-pick"></span>Editor's Pick</span>`
    : m.airoasting_lab ? `<span class="flag"><span class="led led-lab"></span>AI Roasting</span>`
    : (showCat && cat) ? `<span class="tag tag-cat">${esc(cat.name)}</span>`
    : (m.tags && m.tags[0]) ? `<span class="tag">${esc(m.tags[0])}</span>` : "";
  const cls = m.editors_pick ? " pick" : m.airoasting_lab ? " lab" : "";
  return `
  <a class="mod${cls}" href="${esc(m.url)}" target="_blank" rel="noopener">
    <span class="mod-head">
      <span class="jack"><span class="jack-mono">${esc(m.mono)}</span><img src="${esc(m.avatar)}" alt="" loading="lazy" onerror="this.remove()"></span>
      <span class="mod-ht">
        <span class="mod-name" title="${esc(m.name)}">${esc(m.name)}</span>
        <span class="mod-meta">
          <span class="src">${esc(m.author || m.owner)}</span>
          <span class="owner">${esc(m.repo)}</span>
        </span>
      </span>
    </span>
    <span class="mod-desc" title="${esc(m.desc)}">${esc(m.desc)}</span>
    <span class="mod-foot">
      ${flag}
      <span class="stats">
        <span class="star" title="GitHub 스타">${ICON_STAR}${fmtK(m.stars)}</span>
        <span class="fork" title="GitHub 포크">${ICON_FORK}${fmtK(m.forks)}</span>
      </span>
      <span class="patch" aria-hidden="true">${ICON_PATCH}</span>
    </span>
  </a>`;
}

function renderResults() {
  const q = state.query.trim().toLowerCase();
  let items = inFilter(ALL);
  if (q) items = items.filter(m => m.hay.includes(q));
  const flat = state.sort !== "cat";
  if (flat && state.category !== "all") items = items.filter(m => m.category === state.category);
  const key = state.sort === "forks" ? "forks" : "stars";
  items = items.slice().sort((a, b) => (b[key] || 0) - (a[key] || 0));

  const sections = flat ? (items.length ? [1] : []) : CATS.map((c, i) => ({ c, i, items: items.filter(m => m.category === c.id) }))
    .filter(s => s.items.length);

  const el = $("results");
  if (!sections.length) {
    const what = state.query.trim() ? `“${esc(state.query)}”에 해당하는 스킬이 없습니다.` : "조건에 맞는 스킬이 없습니다.";
    el.innerHTML = `
      <div class="empty">
        <div class="msg">${what}</div>
        <div class="sub">다른 검색어를 입력하거나 검색을 초기화하세요.</div>
        <button id="reset" type="button">검색 초기화</button>
      </div>`;
    $("reset").addEventListener("click", () => { state.filter = "all"; syncUrl(); clearSearch(); renderNotice(); renderChips(); });
    return;
  }
  if (flat) {
    const c = CAT_BY_ID[state.category];
    el.innerHTML = `
    <section class="sec">
      <div class="sec-head">
        <span class="sec-idx">${state.sort === "forks" ? "⑂" : "★"}</span>
        <h2>${SORTS[state.sort]}</h2>
        ${c ? `<span class="sec-meta">${esc(c.name)}</span>` : ""}
        <span class="sec-rule"></span>
        <span class="sec-count">${items.length} skills</span>
      </div>
      <p class="sec-desc">${c ? esc(c.desc || "") : "카테고리 구분 없이 전체를 한 목록으로 봅니다. 위의 카테고리를 누르면 그 분야만 남습니다."}</p>
      <div class="grid">${items.map(m => modHTML(m, !c)).join("")}</div>
    </section>`;
    return;
  }
  const metaName = id => (METAS.find(m => m.id === id) || {}).name || "";
  el.innerHTML = sections.map(({ c, i, items }) => `
    <section class="sec" id="sec-${esc(c.id)}" data-cat="${esc(c.id)}">
      <div class="sec-head">
        <span class="sec-idx">${String(i + 1).padStart(2, "0")}</span>
        <h2>${esc(c.name)}</h2>
        ${metaName(c.meta) ? `<span class="sec-meta">${esc(metaName(c.meta))}</span>` : ""}
        <span class="sec-rule"></span>
        <span class="sec-count">${items.length} skills</span>
      </div>
      <p class="sec-desc">${esc(c.desc || "")}</p>
      <div class="grid">${items.map(m => modHTML(m)).join("")}</div>
    </section>`).join("");
}

function renderSort() {
  document.querySelectorAll("#sort button").forEach(b => {
    const on = state.sort === b.dataset.sort;
    b.classList.toggle("active", on);
    b.setAttribute("aria-pressed", on);
  });
}

function render() {
  renderSort();
  renderChips();
  renderQuick();
  renderSearchAffordance();
  renderNotice();
  renderResults();
}

/* ---- url ---- */
function syncUrl() {
  const p = new URLSearchParams(location.search);
  const v = state.filter !== "all" ? state.filter : state.category !== "all" ? state.category : null;
  if (v) p.set("cat", v); else p.delete("cat");
  if (state.sort !== "cat") p.set("sort", state.sort); else p.delete("sort");
  const qs = p.toString();
  history.replaceState(null, "", location.pathname + (qs ? "?" + qs : "") + location.hash);
}

/* ---- interactions ---- */
const searchInput = $("search");

function clearSearch() {
  state.query = "";
  searchInput.value = "";
  renderQuick();
  renderSearchAffordance();
  renderResults();
  searchInput.focus();
}

function setFilter(f) {
  state.filter = f;
  state.category = "all";
  syncUrl();
  render();
}

/* 카테고리 칩·스펙트럼 미터: 카테고리순이면 해당 섹션으로 스크롤, 한 목록이면 그 카테고리만 남긴다 */
function jumpTo(cat, instant) {
  state.category = cat;
  const flat = state.sort !== "cat";
  if (flat) render(); else renderChips();
  const target = (flat || cat === "all") ? $("results") : $("sec-" + cat);
  if (!target) return;
  /* 스티키 칩 바에 섹션 제목이 가리지 않도록 바의 실제 높이만큼 위로 보정한다 */
  const barH = $("catalog").offsetHeight;
  const y = target.getBoundingClientRect().top + window.scrollY - barH - 12;
  window.scrollTo({ top: Math.max(0, y), behavior: instant ? "instant" : reduceMotion() ? "auto" : "smooth" });
}

function wire() {
  searchInput.addEventListener("input", e => {
    state.query = e.target.value;
    renderQuick();
    renderSearchAffordance();
    renderResults();
  });
  $("clear").addEventListener("click", clearSearch);

  window.addEventListener("keydown", e => {
    const typing = /^(INPUT|TEXTAREA)$/.test(document.activeElement.tagName);
    if ((e.key === "/" && !typing) || ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k")) {
      e.preventDefault();
      searchInput.focus();
    }
    if (e.key === "Escape" && document.activeElement === searchInput && state.query) clearSearch();
  });

  $("chips").addEventListener("click", e => {
    const btn = e.target.closest(".chip");
    if (!btn || btn.disabled) return;
    jumpTo(btn.dataset.cat);
    syncUrl();
  });
  $("meters").addEventListener("click", e => {
    const btn = e.target.closest(".meter");
    if (!btn) return;
    /* 미터 숫자는 전체 기준이므로 검색과 필터를 풀고 이동한다 */
    if (state.query.trim() || state.filter !== "all") {
      state.query = ""; searchInput.value = ""; state.filter = "all";
      render();
    }
    jumpTo(btn.dataset.cat);
    syncUrl();
  });

  /* 정렬: 카테고리순 / 스타순 / 포크순 */
  const sortEl = $("sort");
  Object.entries(SORTS).forEach(([id, label]) => {
    const b = document.createElement("button");
    b.type = "button";
    b.dataset.sort = id;
    b.textContent = label;
    b.addEventListener("click", () => {
      if (state.sort === id) return;
      state.sort = id;
      state.category = "all"; // 스크롤 위치로 켜져 있던 칩이 필터로 넘어가지 않게 한다
      syncUrl();
      render();
      /* 이미 목록 중간까지 내려와 있으면 새 목록의 처음으로 올린다 */
      if ($("results").getBoundingClientRect().top < 0) jumpTo("all");
    });
    sortEl.appendChild(b);
  });

  /* 모아 보기: 누르면 필터 + 점등, 다시 누르면 해제 */
  const filtersEl = $("filters");
  Object.entries(FILTERS).forEach(([id, f]) => {
    const b = document.createElement("button");
    b.type = "button";
    b.dataset.filter = id;
    b.innerHTML = `${esc(f.label)}<span class="cnt">${ALL.filter(f.test).length}</span>`;
    b.addEventListener("click", () => setFilter(state.filter === id ? "all" : id));
    filtersEl.appendChild(b);
  });

  /* 범례의 Editor's Pick, AI Roasting 버튼도 같은 필터를 켜고 끈다 */
  document.querySelectorAll(".legend [data-filter]").forEach(b => {
    b.addEventListener("click", () => setFilter(state.filter === b.dataset.filter ? "all" : b.dataset.filter));
  });

  /* 자주 찾는: 누르면 그 키워드로 검색 + 점등, 다시 누르면 해제 */
  const quickEl = $("quick");
  QUICK_PICKS.forEach(name => {
    const b = document.createElement("button");
    b.type = "button";
    b.dataset.q = name;
    b.textContent = name;
    b.addEventListener("click", () => {
      state.query = state.query === name ? "" : name;
      state.category = "all";
      searchInput.value = state.query;
      render();
    });
    quickEl.appendChild(b);
  });

  /* about */
  const about = $("about");
  const openAbout = () => about.showModal();
  $("about-open").addEventListener("click", openAbout);
  $("about-open-2").addEventListener("click", openAbout);
  $("about-close").addEventListener("click", () => about.close());
  about.addEventListener("click", e => { if (e.target === about) about.close(); }); // 바깥(backdrop) 클릭

  /* floating back-to-top */
  const toTop = $("to-top");
  toTop.addEventListener("click", () => window.scrollTo({ top: 0, behavior: reduceMotion() ? "auto" : "smooth" }));

  let tick = false;
  window.addEventListener("scroll", () => {
    if (tick) return;
    tick = true;
    requestAnimationFrame(() => {
      syncChipToScroll();
      toTop.hidden = window.scrollY < 700;
      tick = false;
    });
  }, { passive: true });
}

/* ---- scrollspy : 화면에 보이는 섹션과 카테고리 칩을 동기화 ---- */
function syncChipToScroll() {
  if (state.query.trim() || state.sort !== "cat") return; // 검색 중이거나 한 목록일 때는 칩 상태를 건드리지 않는다
  const panels = [...document.querySelectorAll("#results .sec")];
  if (!panels.length) return;
  const line = $("catalog").offsetHeight + 24; // 스티키 칩 바 바로 아래 기준선
  let current = "all";
  for (const p of panels) {
    if (p.getBoundingClientRect().top <= line) current = p.dataset.cat;
  }
  if (state.category !== current) { state.category = current; renderChips(); }
}

/* ---- init ---- */
function animateCount(el, to, ms) {
  if (reduceMotion()) { el.textContent = to; return; }
  const start = performance.now();
  /* 백그라운드 탭에서는 rAF가 멈춘다. 그때 0에 머물지 않도록 끝 값을 타이머로도 넣는다 */
  setTimeout(() => { el.textContent = to; }, ms + 150);
  (function step(t) {
    const p = Math.min(1, (t - start) / ms);
    el.textContent = Math.round(to * (1 - Math.pow(1 - p, 3)));
    if (p < 1) requestAnimationFrame(step);
  })(start);
}

(async function init() {
  const data = await loadData();
  if (!data) {
    $("results").innerHTML = `<div class="empty"><div class="msg">skills.json을 불러올 수 없습니다.</div>
      <div class="sub">로컬에서 열 때는 python3 -m http.server 8000 --directory docs 로 실행해 주세요.</div></div>`;
    return;
  }
  CATS = data.categories || [];
  METAS = data.meta_categories || [];
  CAT_BY_ID = Object.fromEntries(CATS.map(c => [c.id, c]));
  ALL = (data.skills || []).map(enrich);

  /* 주소의 ?cat= 읽기 */
  const params = new URLSearchParams(location.search);
  const want = params.get("cat");
  if (FILTERS[want]) state.filter = want;
  if (SORTS[params.get("sort")]) state.sort = params.get("sort");

  $("stat-cats").textContent = CATS.length;
  $("stat-picks").textContent = ALL.filter(s => s.editors_pick).length;
  renderMeters();
  wire();
  render();
  if (CAT_BY_ID[want]) jumpTo(want, true);
  else syncUrl(); // 모르는 값(?cat=all 포함)은 주소에서 지운다

  /* 로드 연출: 카운트업 + 미터 상승 한 번 */
  animateCount($("stat-count"), ALL.length, 900);
  document.querySelectorAll("#meters .fill").forEach((f, i) => {
    const scale = "scaleY(" + (f.dataset.h / 100) + ")";
    if (reduceMotion()) { f.style.transform = scale; return; }
    setTimeout(() => { f.style.transform = scale; }, 90 + i * 45);
  });
})();
