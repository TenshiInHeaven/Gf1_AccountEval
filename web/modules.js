'use strict';

/* ------------------------------------------------------------------ */
/* Vehicle components + scheme catalogs (Guihai / Qiushui)             */
/* ------------------------------------------------------------------ */

function buildComponentIndexes() {
  const guide = DATA.components || {};
  const catalog = DATA.vehicleCatalog || {};
  state.componentRecommended = new Map(
    (guide.components || []).map((item) => [String(item.name || ''), list(item.schemes)])
  );
  state.componentRequirements = guide.requirements || {};
  state.componentsMeta = catalog.components || {};
  state.guihaiRows = flattenGuihai(DATA.guihai || {});
  state.qiushuiRows = flattenQiushui(DATA.qiushui || {});
  state.guihaiByWeapon = groupByRows(state.guihaiRows, (row) => row.weapon);
  state.qiushuiByName = groupByRows(state.qiushuiRows, (row) => row.name);
  state.componentFilter = { scheme: 'all', query: '', limit: 120 };
  state.schemeFilter = {
    mode: 'guihai', group: '', weapon: '', activity: '', side: '',
    status: 'all', query: '', limit: 120,
  };
  state.schemeMatches = { guihai: new Map(), qiushui: new Map() };
  state.schemeMatchAccount = null;
}

function list(value) {
  return Array.isArray(value) ? value.slice() : [];
}

function groupByRows(rows, keyFn) {
  const map = new Map();
  for (const row of rows) {
    const key = keyFn(row);
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(row);
  }
  return map;
}

function flattenGuihai(payload) {
  const rows = [];
  for (const group of payload.groups || []) {
    for (const weapon of group.weapons || []) {
      if (Array.isArray(weapon.mains)) {
        for (const main of weapon.mains) {
          for (const combo of main.combos || []) {
            const words = [String(main.word || ''), ...combo.map(String)];
            rows.push({
              id: `gh-${rows.length + 1}`,
              group: String(group.name || ''),
              weapon: String(weapon.name || ''),
              main: String(main.word || ''),
              words,
              label: words.join(' + '),
            });
          }
        }
      } else {
        for (const combo of weapon.combos || []) {
          const words = combo.map(String);
          rows.push({
            id: `gh-${rows.length + 1}`,
            group: String(group.name || ''),
            weapon: String(weapon.name || ''),
            main: '',
            words,
            label: words.join(' + '),
          });
        }
      }
    }
  }
  return rows;
}

function flattenQiushui(payload) {
  const rows = [];
  for (const activity of payload.activities || []) {
    for (const table of activity.tables || []) {
      for (const component of table.components || []) {
        rows.push({
          id: `qs-${rows.length + 1}`,
          activityId: String(activity.id || ''),
          activity: String(activity.name || ''),
          side: String(table.side || ''),
          variant: String(table.variant || ''),
          name: String(component.name || ''),
          stat1: String(component.stat1 || ''),
          stat2: String(component.stat2 || ''),
          optional: String(component.optional || ''),
          reference: false,
        });
      }
    }
  }
  const reference = payload.reference;
  if (reference && Array.isArray(reference.components)) {
    for (const component of reference.components) {
      rows.push({
        id: `qs-ref-${rows.length + 1}`,
        activityId: 'reference',
        activity: '图1 总表（旧版）',
        side: '主战坦克',
        variant: '参考',
        name: String(component.name || ''),
        stat1: String(component.stat1 || ''),
        stat2: String(component.stat2 || ''),
        optional: String(component.optional || ''),
        reference: true,
      });
    }
  }
  return rows;
}

/* ------------------------------------------------------------------ */
/* Snapshot -> component inventory                                     */
/* ------------------------------------------------------------------ */

function rollParts(value, names, skillNames) {
  const text = String(value ?? '').trim();
  if (!text) return '';
  if (!text.includes(':')) return text;
  const [code, number] = text.split(':');
  if (code === 'skill') return `技能 ${(skillNames || {})[number] || number}`;
  return `${(names || {})[code] || code} ${number}`;
}

function laowuMatches(words, rules) {
  if (rules == null) return true;
  if (Array.isArray(rules)) return rules.every((rule) => words.includes(String(rule)));
  if (typeof rules === 'object') {
    const mains = list(rules.main);
    const required = list(rules.required);
    const any = list(rules.any);
    if (mains.length && !mains.some((word) => words.includes(String(word)))) return false;
    if (required.length && !required.every((word) => words.includes(String(word)))) return false;
    if (any.length && !any.some((word) => words.includes(String(word)))) return false;
    return true;
  }
  return false;
}

function buildComponentInventory(payload) {
  const raw = payload && payload.vehicle_component_with_user_info;
  let rows = [];
  if (Array.isArray(raw)) rows = raw;
  else if (raw && typeof raw === 'object') rows = Object.values(raw);
  else if (Array.isArray(payload && payload.components)) rows = payload.components;
  if (!rows.length) return [];
  const catalog = DATA.vehicleCatalog || {};
  const components = catalog.components || {};
  const rollNames = catalog.roll_names || {};
  const skillNames = catalog.skill_names || {};
  const recommended = state.componentRecommended || new Map();
  const requirements = state.componentRequirements || {};
  const guihaiByWeapon = state.guihaiByWeapon || new Map();
  const qiushuiByName = state.qiushuiByName || new Map();
  const grouped = new Map();
  for (const row of rows) {
    if (!row || typeof row !== 'object') continue;
    if (Array.isArray(payload.components)) {
      // Already-normalized component export: name / words / count.
      const key = `${row.name || ''}|${row.words || ''}`;
      if (!grouped.has(key)) {
        grouped.set(key, {
          id: key,
          name: String(row.name || ''),
          typeId: Number(row.type_id || 0),
          typeName: String(row.type_name || '其他'),
          words: String(row.words || '无词条'),
          count: 0,
          schemes: [],
          guihaiHits: [],
          qiushuiHits: [],
        });
      }
      grouped.get(key).count += Number(row.count || 1);
      continue;
    }
    const componentId = String(row.component_id ?? '');
    const meta = components[componentId] || {};
    const typeId = Number(meta.type || 0);
    const rolls = [1, 2, 3, 4, 5].map((index) => String(row[`roll_${index}`] ?? ''));
    const key = `${componentId}:${rolls.join('|')}`;
    if (!grouped.has(key)) {
      const words = rolls
        .map((value) => rollParts(value, rollNames, skillNames))
        .filter(Boolean)
        .join(' / ') || '无词条';
      grouped.set(key, {
        id: key,
        name: String(meta.name || componentId),
        typeId,
        typeName: String(meta.type_name || (typeId === 0 ? '通用' : '其他')),
        words,
        count: 0,
        schemes: [],
        guihaiHits: [],
        qiushuiHits: [],
      });
    }
    grouped.get(key).count += 1;
  }
  for (const entry of grouped.values()) {
    const name = entry.name;
    const words = entry.words;
    const schemes = recommended.get(name) || [];
    const matched = [];
    for (const scheme of schemes) {
      if (scheme === 'guihai') {
        const hits = (guihaiByWeapon.get(name) || []).filter((row) => row.words.every((word) => words.includes(word)));
        if (hits.length) {
          matched.push('guihai');
          entry.guihaiHits = hits.map((row) => row.label);
        }
        continue;
      }
      if (scheme === 'qiushui') {
        const hits = (qiushuiByName.get(name) || []).filter(
          (row) => row.stat1 && row.stat2 && words.includes(row.stat1) && words.includes(row.stat2)
        );
        if (hits.length) {
          matched.push('qiushui');
          entry.qiushuiHits = hits.map((row) => `${row.activity} / ${row.side}：${row.stat1} + ${row.stat2}`);
        }
        continue;
      }
      if (scheme === 'laowu') {
        const rules = (requirements.laowu || {})[name];
        if (rules === undefined || laowuMatches(words, rules)) matched.push('laowu');
      }
    }
    entry.schemes = matched;
  }
  return Array.from(grouped.values());
}

function componentLevel(entry) {
  if (entry.schemes.length >= 3) return 'gold';
  if (entry.schemes.length) return 'green';
  return 'gray';
}

function componentSummary(inventory) {
  const counts = { gold: 0, green: 0, gray: 0, guihai: 0, qiushui: 0, laowu: 0 };
  for (const entry of inventory) {
    counts[componentLevel(entry)] += 1;
    for (const scheme of entry.schemes) counts[scheme] = (counts[scheme] || 0) + 1;
  }
  return {
    instances: inventory.reduce((sum, entry) => sum + entry.count, 0),
    unique: inventory.length,
    ...counts,
  };
}

/* ------------------------------------------------------------------ */
/* Components page                                                     */
/* ------------------------------------------------------------------ */

function renderComponentsPage() {
  const inventory = state.account ? state.account.components || [] : [];
  const head = pageHead('组件', '机动装甲组件库 · 归海 / 秋水');
  if (!inventory.length) {
    return `${head}
      <div class="card empty">
        当前快照不含组件数据。<br><br>
        请导入「合并快照」（包含 <code>vehicle_component_with_user_info</code>），
        或用 PC 端导出网页快照后点「导入快照 / 连接」。
      </div>`;
  }
  const summary = componentSummary(inventory);
  const meta = (state.account && state.account.meta) || {};
  const stale = meta.component_stale && meta.component_source
    ? `<div class="grid-count">组件数据来自 ${esc(meta.component_source)}（早于账号快照）</div>`
    : '';
  const stats = [
    ['实例', summary.instances],
    ['去重', summary.unique],
    ['金框', summary.gold],
    ['绿框', summary.green],
    ['归海命中', summary.guihai],
    ['秋水命中', summary.qiushui],
  ].map(([label, value]) => `<div class="comp-stat"><strong>${value}</strong><span>${label}</span></div>`).join('');
  const options = [
    ['all', '全部组件'], ['union', '任一方案'], ['gold', '金框（三套）'], ['green', '绿框（部分）'],
    ['gray', '灰框（无方案）'], ['guihai', '归海'], ['qiushui', '秋水'], ['laowu', '老吴'],
  ].map(([value, label]) => `<option value="${value}"${state.componentFilter.scheme === value ? ' selected' : ''}>${label}</option>`).join('');
  return `${head}
    ${stale}
    <section class="comp-stats">${stats}</section>
    <div class="filter-bar">
      <select class="type-select" data-action="comp-scheme">${options}</select>
      <input class="search-input" type="search" placeholder="搜索组件 / 词条…" value="${esc(state.componentFilter.query)}" data-action="comp-search" autocomplete="off">
      <span class="grid-count" id="comp-count"></span>
    </div>
    <div class="comp-list" id="comp-list"></div>
    <button class="btn ghost more-button" type="button" data-action="comp-more" hidden>加载更多</button>`;
}

function renderComponentRows() {
  const container = $('#comp-list');
  if (!container) return;
  const cfg = state.componentFilter;
  const inventory = state.account ? state.account.components || [] : [];
  const query = cfg.query.trim().toLowerCase();
  const filtered = inventory.filter((entry) => {
    if (cfg.scheme === 'union' && !entry.schemes.length) return false;
    if (['gold', 'green', 'gray'].includes(cfg.scheme) && componentLevel(entry) !== cfg.scheme) return false;
    if (['guihai', 'qiushui', 'laowu'].includes(cfg.scheme) && !entry.schemes.includes(cfg.scheme)) return false;
    if (query && !`${entry.name} ${entry.words}`.toLowerCase().includes(query)) return false;
    return true;
  });
  filtered.sort((a, b) => b.schemes.length - a.schemes.length
    || b.count - a.count
    || a.name.localeCompare(b.name, 'zh-Hans-CN'));
  const shown = filtered.slice(0, cfg.limit);
  container.innerHTML = shown.length ? shown.map(componentCardHTML).join('') : '<div class="empty">没有符合条件的组件</div>';
  const count = $('#comp-count');
  if (count) count.textContent = `${filtered.length} 条 · 显示 ${shown.length}`;
  const more = $('[data-action="comp-more"]');
  if (more) {
    more.hidden = filtered.length <= shown.length;
    more.textContent = `加载更多（剩余 ${Math.max(0, filtered.length - shown.length)}）`;
  }
}

function componentCardHTML(entry) {
  const level = componentLevel(entry);
  const badges = [];
  if (entry.guihaiHits.length) badges.push(`<span class="scheme-badge gh">归海 ${entry.guihaiHits.length}</span>`);
  if (entry.qiushuiHits.length) badges.push(`<span class="scheme-badge qs">秋水 ${entry.qiushuiHits.length}</span>`);
  if (entry.schemes.includes('laowu')) badges.push('<span class="scheme-badge lw">老吴</span>');
  const title = [...entry.guihaiHits, ...entry.qiushuiHits].join('\n');
  return `<article class="comp-card comp-${level}">
    <div class="comp-top"><strong>${esc(entry.name)}</strong><span class="comp-count">×${entry.count}</span><span class="comp-type">${esc(entry.typeName)}</span></div>
    <div class="comp-words">${esc(entry.words)}</div>
    <div class="comp-badges">${badges.join('') || '<span class="scheme-badge none">无方案</span>'}</div>
    ${title ? `<div class="comp-tip" title="${esc(title)}">${esc(entry.guihaiHits[0] || entry.qiushuiHits[0] || '')}</div>` : ''}
  </article>`;
}

/* ------------------------------------------------------------------ */
/* Scheme page (Guihai / Qiushui)                                      */
/* ------------------------------------------------------------------ */

function ensureSchemeMatches() {
  if (state.schemeMatchAccount === state.account) return;
  const inventory = state.account ? state.account.components || [] : [];
  const byName = groupByRows(inventory, (entry) => entry.name);
  const guihai = new Map();
  for (const row of state.guihaiRows || []) {
    let count = 0;
    const sources = [];
    for (const entry of byName.get(row.weapon) || []) {
      if (row.words.every((word) => entry.words.includes(word))) {
        count += entry.count;
        sources.push(entry.words);
      }
    }
    if (count) guihai.set(row.id, { count, sources: [...new Set(sources)] });
  }
  const qiushui = new Map();
  for (const row of state.qiushuiRows || []) {
    let count = 0;
    const sources = [];
    for (const entry of byName.get(row.name) || []) {
      if (row.stat1 && row.stat2 && entry.words.includes(row.stat1) && entry.words.includes(row.stat2)) {
        count += entry.count;
        sources.push(entry.words);
      }
    }
    if (count) qiushui.set(row.id, { count, sources: [...new Set(sources)] });
  }
  state.schemeMatches = { guihai, qiushui };
  state.schemeMatchAccount = state.account;
}

function schemeSummary(mode) {
  const rows = mode === 'guihai'
    ? state.guihaiRows || []
    : (state.qiushuiRows || []).filter((row) => !row.reference);
  const matches = state.schemeMatches[mode] || new Map();
  const owned = rows.filter((row) => matches.has(row.id)).length;
  const covered = new Set(rows.filter((row) => matches.has(row.id)).map((row) => mode === 'guihai' ? row.weapon : row.name)).size;
  const totalComponents = mode === 'guihai'
    ? new Set(rows.map((row) => row.weapon)).size
    : new Set(rows.map((row) => row.name)).size;
  return { rows: rows.length, owned, covered, totalComponents };
}

function renderSchemesPage() {
  ensureSchemeMatches();
  const cfg = state.schemeFilter;
  const summary = schemeSummary(cfg.mode);
  const modeButtons = [
    ['guihai', '归海一图流'], ['qiushui', '秋水各关卡'],
  ].map(([value, label]) => `<button class="seg-btn ${cfg.mode === value ? 'active' : ''}" type="button" data-action="scheme-mode" data-mode="${value}">${label}</button>`).join('');
  let toolbar = '';
  if (cfg.mode === 'guihai') {
    const groups = (DATA.guihai && DATA.guihai.groups || []).map((group) => group.name);
    const groupOptions = ['', ...groups].map((value) => `<option value="${esc(value)}"${cfg.group === value ? ' selected' : ''}>${value || '全部组'}</option>`).join('');
    const weaponNames = [...new Set((state.guihaiRows || []).filter((row) => !cfg.group || row.group === cfg.group).map((row) => row.weapon))];
    const weaponOptions = ['', ...weaponNames].map((value) => `<option value="${esc(value)}"${cfg.weapon === value ? ' selected' : ''}>${value || '全部组件'}</option>`).join('');
    toolbar = `<div class="filter-bar">
      <select class="type-select" data-action="scheme-group">${groupOptions}</select>
      <select class="type-select" data-action="scheme-weapon">${weaponOptions}</select>
      ${statusSelect(cfg.status)}
      <input class="search-input" type="search" placeholder="搜索组件 / 主词条 / 词条…" value="${esc(cfg.query)}" data-action="scheme-search" autocomplete="off">
    </div>`;
  } else {
    const activities = (DATA.qiushui && DATA.qiushui.activities || []);
    const activityOptions = [
      ['', '全部活动'],
      ...activities.map((activity) => [activity.id, activity.name]),
      ['reference', '图1 总表（旧版）'],
    ].map(([value, label]) => `<option value="${esc(value)}"${cfg.activity === value ? ' selected' : ''}>${esc(label)}</option>`).join('');
    const sides = ['主战坦克', '战术人型机甲'];
    const sideOptions = ['', ...sides].map((value) => `<option value="${esc(value)}"${cfg.side === value ? ' selected' : ''}>${value || '全部类型'}</option>`).join('');
    toolbar = `<div class="filter-bar">
      <select class="type-select" data-action="scheme-activity">${activityOptions}</select>
      <select class="type-select" data-action="scheme-side">${sideOptions}</select>
      ${statusSelect(cfg.status)}
      <input class="search-input" type="search" placeholder="搜索活动 / 组件 / 词条…" value="${esc(cfg.query)}" data-action="scheme-search" autocomplete="off">
    </div>`;
  }
  const label = cfg.mode === 'guihai'
    ? `归海 ${summary.rows} 条组合 · 已拥有 ${summary.owned} 条 · 覆盖 ${summary.covered}/${summary.totalComponents} 件`
    : `秋水 ${summary.rows} 条需求（8 活动 / 21 表）· 已拥有 ${summary.owned} 条 · 覆盖 ${summary.covered}/${summary.totalComponents} 件`;
  return `${pageHead('方案', cfg.mode === 'guihai' ? '归海一图流 183 条词条组合' : '秋水各积分关卡 8 活动 / 21 张表')}
    <div class="segmented">${modeButtons}</div>
    ${toolbar}
    <div class="grid-count">${esc(label)}</div>
    <div class="scheme-list" id="scheme-list"></div>
    <button class="btn ghost more-button" type="button" data-action="scheme-more" hidden>加载更多</button>`;
}

function statusOptions(value) {
  return [['all', '全部状态'], ['owned', '已拥有'], ['missing', '缺口']]
    .map(([key, label]) => `<option value="${key}"${value === key ? ' selected' : ''}>${label}</option>`).join('');
}

function statusSelect(value) {
  return `<select class="type-select" data-action="scheme-status">${statusOptions(value)}</select>`;
}

function renderSchemeRows() {
  ensureSchemeMatches();
  const cfg = state.schemeFilter;
  const container = $('#scheme-list');
  if (!container) return;
  const matches = state.schemeMatches[cfg.mode] || new Map();
  const query = cfg.query.trim().toLowerCase();
  let rows = cfg.mode === 'guihai' ? (state.guihaiRows || []) : (state.qiushuiRows || []);
  rows = rows.filter((row) => {
    if (cfg.mode === 'qiushui') {
      if (cfg.activity === 'reference') { if (!row.reference) return false; }
      else if (row.reference) return false;
      if (cfg.activity && cfg.activity !== 'reference' && row.activityId !== cfg.activity) return false;
      if (cfg.side && row.side !== cfg.side) return false;
    } else {
      if (cfg.group && row.group !== cfg.group) return false;
      if (cfg.weapon && row.weapon !== cfg.weapon) return false;
    }
    const owned = matches.has(row.id);
    if (cfg.status === 'owned' && !owned) return false;
    if (cfg.status === 'missing' && owned) return false;
    const haystack = cfg.mode === 'guihai'
      ? `${row.weapon}${row.main}${row.label}`
      : `${row.activity}${row.name}${row.stat1}${row.stat2}${row.optional}`;
    if (query && !haystack.toLowerCase().includes(query)) return false;
    return true;
  });
  const shown = rows.slice(0, cfg.limit);
  container.innerHTML = shown.length
    ? `<div class="scheme-head ${cfg.mode}">${schemeHeadHTML(cfg.mode)}</div>${shown.map((row) => schemeRowHTML(row, cfg.mode, matches)).join('')}`
    : '<div class="empty">没有符合条件的方案条目</div>';
  const more = $('[data-action="scheme-more"]');
  if (more) {
    more.hidden = rows.length <= shown.length;
    more.textContent = `加载更多（剩余 ${Math.max(0, rows.length - shown.length)}）`;
  }
}

function schemeHeadHTML(mode) {
  const columns = mode === 'guihai'
    ? ['组', '组件', '主词条', '词条组合', '状态', '仓库词条']
    : ['活动', '表', '组件', '词条1', '词条2', '任意', '状态', '仓库词条'];
  return columns.map((label) => `<span>${label}</span>`).join('');
}

function schemeRowHTML(row, mode, matches) {
  const info = matches.get(row.id);
  const owned = Boolean(info);
  const cells = mode === 'guihai'
    ? [row.group, row.weapon, row.main || '—', row.label, owned ? `×${info.count}` : '缺失', owned ? info.sources.join('；') : '']
    : [row.activity, `${row.side}·${row.variant}`, row.name, row.stat1, row.stat2, row.optional || '—', owned ? `×${info.count}` : '缺失', owned ? info.sources.join('；') : ''];
  const labels = mode === 'guihai'
    ? ['组', '组件', '主词条', '词条组合', '状态', '仓库词条']
    : ['活动', '表', '组件', '词条1', '词条2', '任意', '状态', '仓库词条'];
  return `<div class="scheme-row ${owned ? 'owned' : ''} ${mode}">
    ${cells.map((value, index) => `<span data-label="${labels[index]}" class="${index === cells.length - 2 ? 'status' : ''}" title="${esc(value)}">${esc(value)}</span>`).join('')}
  </div>`;
}

/* ------------------------------------------------------------------ */
/* Feature events (called from app.js)                                 */
/* ------------------------------------------------------------------ */

function onFeatureEvent(event) {
  const node = event.target.closest('[data-action]');
  if (!node) return false;
  const action = node.dataset.action;
  if (action === 'settings-import-snapshot') {
    const input = $('#fileInput');
    if (input) input.click();
    return true;
  }
  if (action === 'settings-connect') {
    connectSnapshot();
    return true;
  }
  if (action === 'settings-export-snapshot') {
    if (!state.rawPayload) return true;
    downloadJSON('gf_snapshot.json', state.rawPayload);
    toast('快照已导出');
    return true;
  }
  if (action === 'settings-export-ratings') {
    downloadJSON('gf_ratings_export.json', { schema: 1, kinds: DATA.tiers });
    toast('评分 JSON 已导出');
    return true;
  }
  if (action === 'settings-import-ratings') {
    const input = document.querySelector('[data-action="settings-ratings-file"]');
    if (input) input.click();
    return true;
  }
  if (action === 'settings-reset-ratings') {
    resetRatings();
    return true;
  }
  if (action === 'settings-export-favorites') {
    const grouped = { doll: [], fairy: [], sangvis: [] };
    for (const key of state.favorites) {
      const [kind, code] = String(key).split(':');
      if (grouped[kind] && code) grouped[kind].push(code);
    }
    downloadJSON('gf_favorites.json', {
      version: 1,
      exported_at: new Date().toISOString(),
      favorites: grouped,
    });
    toast('收藏 JSON 已导出');
    return true;
  }
  if (action === 'settings-import-favorites') {
    const input = document.querySelector('[data-action="settings-favorites-file"]');
    if (input) input.click();
    return true;
  }
  if (action === 'settings-copy-pair') {
    copyPairing();
    return true;
  }
  if (action === 'comp-more') {
    state.componentFilter.limit += 120;
    renderComponentRows();
    return true;
  }
  if (action === 'scheme-mode') {
    state.schemeFilter.mode = node.dataset.mode === 'qiushui' ? 'qiushui' : 'guihai';
    state.schemeFilter.limit = 120;
    renderPage();
    return true;
  }
  if (action === 'scheme-more') {
    state.schemeFilter.limit += 120;
    renderSchemeRows();
    return true;
  }
  return false;
}

function onFeatureChange(event) {
  const node = event.target.closest('[data-action]');
  if (!node) return false;
  const action = node.dataset.action;
  if (action === 'settings-ratings-file') {
    importRatingsFile(node);
    return true;
  }
  if (action === 'settings-favorites-file') {
    importFavoritesFile(node);
    return true;
  }
  if (action === 'eq-activity') {
    state.equipmentActivity = node.value;
    renderPage();
    return true;
  }
  if (action === 'comp-scheme') {
    state.componentFilter.scheme = node.value;
    state.componentFilter.limit = 120;
    renderComponentRows();
    return true;
  }
  if (action === 'scheme-group') {
    state.schemeFilter.group = node.value;
    state.schemeFilter.weapon = '';
    state.schemeFilter.limit = 120;
    renderPage();
    return true;
  }
  if (action === 'scheme-weapon') {
    state.schemeFilter.weapon = node.value;
    state.schemeFilter.limit = 120;
    renderSchemeRows();
    return true;
  }
  if (action === 'scheme-activity') {
    state.schemeFilter.activity = node.value;
    state.schemeFilter.limit = 120;
    renderPage();
    return true;
  }
  if (action === 'scheme-side') {
    state.schemeFilter.side = node.value;
    state.schemeFilter.limit = 120;
    renderSchemeRows();
    return true;
  }
  if (action === 'scheme-status') {
    state.schemeFilter.status = node.value;
    state.schemeFilter.limit = 120;
    renderSchemeRows();
    return true;
  }
  return false;
}

function onFeatureInput(event) {
  const node = event.target.closest('[data-action]');
  if (!node) return false;
  const action = node.dataset.action;
  if (action === 'comp-search') {
    state.componentFilter.query = node.value;
    state.componentFilter.limit = 120;
    renderComponentRows();
    return true;
  }
  if (action === 'scheme-search') {
    state.schemeFilter.query = node.value;
    state.schemeFilter.limit = 120;
    renderSchemeRows();
    return true;
  }
  return false;
}

/* ------------------------------------------------------------------ */
/* Settings / ratings / favorites                                      */
/* ------------------------------------------------------------------ */

function applySavedRatings() {
  try {
    const raw = localStorage.getItem(TIERS_KEY);
    if (!raw) return;
    const kinds = JSON.parse(raw);
    applyRatings(kinds, { persist: false, rerender: false });
  } catch (error) {
    console.warn('saved ratings failed', error);
  }
}

function validRatings(kinds) {
  if (!kinds || typeof kinds !== 'object') return false;
  return ['doll', 'fairy', 'sangvis'].some((kind) => {
    const value = kinds[kind];
    return value && Array.isArray(value.tiers) && Array.isArray(value.entries);
  });
}

function applyRatings(kinds, options = {}) {
  if (!validRatings(kinds)) throw new Error('评分 JSON 缺少 kinds.doll/fairy/sangvis');
  for (const kind of ['doll', 'fairy', 'sangvis']) {
    if (kinds[kind] && Array.isArray(kinds[kind].tiers) && Array.isArray(kinds[kind].entries)) {
      DATA.tiers[kind] = kinds[kind];
    }
  }
  buildTierLookup();
  if (options.persist !== false) {
    try { localStorage.setItem(TIERS_KEY, JSON.stringify(DATA.tiers)); } catch (_error) { /* ignore */ }
  }
  if (options.rerender !== false) reapplyAccount();
}

function resetRatings() {
  DATA.tiers = JSON.parse(JSON.stringify(DATA.baseTiers));
  try { localStorage.removeItem(TIERS_KEY); } catch (_error) { /* ignore */ }
  buildTierLookup();
  reapplyAccount();
  toast('已恢复内置评分');
}

function reapplyAccount() {
  if (!state.rawPayload) return;
  state.account = buildAccount(state.rawPayload);
  state.evaluation = evaluateAccount(state.account);
  if (state.tab === 'settings') renderPage();
  else renderPage();
}

function downloadJSON(name, payload) {
  const blob = new Blob([JSON.stringify(payload, null, 1)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 3000);
}

function renderSettingsPage() {
  const meta = (state.rawPayload && state.rawPayload.meta) || {};
  const components = state.account ? state.account.components || [] : [];
  const favorites = state.favorites.size;
  const version = (DATA.buildInfo && DATA.buildInfo.version) || '—';
  const tierSources = ['doll', 'fairy', 'sangvis']
    .map((kind) => `<div class="source-row"><strong>${KIND_LABEL[kind]}</strong><span>${esc((DATA.tiers[kind] || {}).source || '内置榜单')}</span></div>`)
    .join('');
  const componentNote = components.length
    ? `${components.reduce((sum, entry) => sum + entry.count, 0)} 个实例 / ${components.length} 条去重`
    : '当前快照不含组件（导入含 vehicle_component_with_user_info 的合并快照，或连接 PC）';
  return `${pageHead('设置', '数据源 / 评分 / 快照 / 缓存')}
    <div class="settings-grid">
      <section class="card settings-card">
        <h3>当前账号</h3>
        <div class="hero-meta">${esc(meta.nickname || '未载入')} · UID ${esc(meta.uid || '—')} · Lv.${esc(meta.level || '—')}</div>
        <div class="hero-meta">${esc(meta.source || '')}</div>
        <div class="settings-note">组件：${esc(componentNote)}${meta.component_stale ? `（来自 ${esc(meta.component_source || '旧索引')}）` : ''}<br>可先导入 account 快照，再单独导入 index_*.json 合并组件。</div>
        <div class="settings-actions">
          <button class="btn primary" type="button" data-action="settings-import-snapshot">导入快照</button>
          <button class="btn ghost" type="button" data-action="settings-connect">连接 PC</button>
          <button class="btn ghost" type="button" data-action="settings-export-snapshot">导出快照</button>
        </div>
      </section>
      <section class="card settings-card">
        <h3>评分数据</h3>
        <div class="settings-note">修改 JSON 后导入即可覆盖内置榜单；导出格式与桌面端「评分数据」一致。</div>
        <div class="settings-actions">
          <button class="btn ghost" type="button" data-action="settings-export-ratings">导出评分 JSON</button>
          <button class="btn ghost" type="button" data-action="settings-import-ratings">导入评分 JSON</button>
          <button class="btn ghost" type="button" data-action="settings-reset-ratings">恢复内置评分</button>
        </div>
        <input type="file" accept=".json,application/json" data-action="settings-ratings-file" hidden>
      </section>
      <section class="card settings-card">
        <h3>收藏</h3>
        <div class="settings-note">已收藏 ${favorites} 个单位；收藏保存在本机 localStorage。</div>
        <div class="settings-actions">
          <button class="btn ghost" type="button" data-action="settings-export-favorites">导出收藏 JSON</button>
          <button class="btn ghost" type="button" data-action="settings-import-favorites">导入收藏 JSON</button>
        </div>
        <input type="file" accept=".json,application/json" data-action="settings-favorites-file" hidden>
      </section>
      <section class="card settings-card">
        <h3>手机配对</h3>
        <div class="settings-note">手机与电脑同一 Wi-Fi；PC 用 <code>run_web.ps1 --host 0.0.0.0</code> 启动，手机扫码即可打开 PWA 并自动载入最新快照。</div>
        <div class="pair-box">
          <img class="pair-qr" src="/api/qr" alt="手机配对二维码" onerror="this.closest('.pair-box').hidden=true">
          <div class="settings-note" id="pair-url">/api/latest</div>
        </div>
        <div class="settings-actions">
          <button class="btn ghost" type="button" data-action="settings-copy-pair">复制配对链接</button>
        </div>
      </section>
      <section class="card settings-card">
        <h3>数据来源</h3>
        ${tierSources}
        <div class="source-row"><strong>装备</strong><span>${esc((DATA.equipmentTargets || {}).source || '')}</span></div>
        <div class="source-row"><strong>归海</strong><span>机动装甲武器.png（2025/11/16）</span></div>
        <div class="source-row"><strong>秋水</strong><span>腾讯文档 8 个活动 / 21 张积分关卡表</span></div>
        <div class="settings-note">版本 ${esc(version)} · PWA 静态数据 · 头像按需缓存</div>
      </section>
    </div>
    <div class="settings-note" style="margin-top:12px">
      快照包含 UID / 昵称 / 仓库，请勿公开分享。离线缓存由 Service Worker 管理；清理站点数据会同时清空本地快照和收藏。
    </div>`;
}

async function importRatingsFile(input) {
  const file = input.files && input.files[0];
  if (!file) return;
  try {
    const payload = JSON.parse(await file.text());
    const kinds = payload.kinds || payload;
    applyRatings(kinds);
    toast('评分 JSON 已导入');
  } catch (error) {
    toast(`评分导入失败：${error.message}`);
  } finally {
    input.value = '';
  }
}

async function importFavoritesFile(input) {
  const file = input.files && input.files[0];
  if (!file) return;
  try {
    const payload = JSON.parse(await file.text());
    const rows = new Set();
    if (Array.isArray(payload)) {
      for (const value of payload) rows.add(String(value));
    } else if (payload && typeof payload.favorites === 'object' && !Array.isArray(payload.favorites)) {
      for (const kind of ['doll', 'fairy', 'sangvis']) {
        for (const code of payload.favorites[kind] || []) rows.add(`${kind}:${code}`);
      }
    } else if (payload && Array.isArray(payload.favorites)) {
      for (const value of payload.favorites) rows.add(String(value));
    } else {
      throw new Error('收藏 JSON 格式不支持');
    }
    state.favorites = rows;
    saveFavorites();
    renderPage();
    toast('收藏已导入');
  } catch (error) {
    toast(`收藏导入失败：${error.message}`);
  } finally {
    input.value = '';
  }
}

async function hydratePairing() {
  const node = $('#pair-url');
  if (!node) return;
  try {
    const response = await fetch('/api/pair', { cache: 'no-store' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    const suffix = data.reachable_from_phone ? '' : '（当前绑定 127.0.0.1，手机访问不到，请用 --host 0.0.0.0）';
    node.textContent = `${data.url}${suffix}`;
    node.dataset.pairUrl = data.url;
  } catch (_error) {
    node.textContent = '当前不是 serve.py 环境；可用「连接」手动填 http://<PC IP>:8770/api/latest';
  }
}

async function copyPairing() {
  const node = $('#pair-url');
  let url = (node && node.dataset.pairUrl) || '';
  if (!url) {
    try {
      const response = await fetch('/api/pair', { cache: 'no-store' });
      if (response.ok) url = (await response.json()).url || '';
    } catch (_error) { /* ignore */ }
  }
  if (!url) url = `${location.origin}/?snapshot=/api/latest`;
  try {
    await navigator.clipboard.writeText(url);
    toast('配对链接已复制');
  } catch (_error) {
    window.prompt('复制配对链接', url);
  }
}
