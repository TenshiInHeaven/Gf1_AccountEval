'use strict';

/* ------------------------------------------------------------------ */
/* Constants / state                                                   */
/* ------------------------------------------------------------------ */
const STORAGE_KEY = 'gf-account-forge-snapshot-v1';
const KIND_LABEL = { doll: '人形', fairy: '妖精', sangvis: '融合势力' };
const TYPE_LABEL = { 1: 'HG', 2: 'SMG', 3: 'RF', 4: 'AR', 5: 'MG', 6: 'SG' };
const UNIT_TABS = new Set(['doll', 'fairy', 'sangvis']);
const TITLES = {
  dashboard: ['总览', '四维评分与下一步建议'],
  doll: ['人形', '仓库人形 / 三体人与常用好手'],
  fairy: ['妖精', '空降与战略妖精储备'],
  sangvis: ['融合势力', '铁血捕获单位'],
  equipment: ['装备', '目标个数 vs 当前个数'],
  codex: ['图鉴', '全量单位与拥有状态'],
};

const DATA = { codex: {}, tiers: {}, equipmentItems: [], equipmentTargets: null, sample: null };
const state = {
  tab: 'dashboard',
  codexKind: 'doll',
  account: null,
  evaluation: null,
  codexByKind: { doll: [], fairy: [], sangvis: [] },
  codexByCode: { doll: new Map(), fairy: new Map(), sangvis: new Map() },
  alias: new Map(),
  tierLookup: {},
  equipment: null,
  grid: {
    doll: makeGrid(true),
    fairy: makeGrid(true),
    sangvis: makeGrid(true),
    codex_doll: makeGrid(false),
    codex_fairy: makeGrid(false),
    codex_sangvis: makeGrid(false),
  },
};

function makeGrid(ownedOnly) {
  return { query: '', tiers: new Set(), ownedOnly, limit: 120, type: 0 };
}

/* ------------------------------------------------------------------ */
/* Utilities                                                           */
/* ------------------------------------------------------------------ */
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[char]));
}

function normalize(value) {
  return String(value ?? '')
    .normalize('NFKC')
    .replace(/[ⅠⅡⅢⅣⅤⅥ]/g, (char) => ({ 'Ⅰ': 'I', 'Ⅱ': 'II', 'Ⅲ': 'III', 'Ⅳ': 'IV', 'Ⅴ': 'V', 'Ⅵ': 'VI' }[char]))
    .toLowerCase()
    .replace(/&/g, 'and')
    .replace(/[^\p{L}\p{N}]/gu, '');
}

function num(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? Math.trunc(parsed) : 0;
}

function pct(value) {
  return Math.max(0, Math.min(100, Number(value) || 0));
}

function groupBy(rows, keyFn) {
  const map = new Map();
  for (const row of rows) {
    const key = keyFn(row);
    if (!key) continue;
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(row);
  }
  return map;
}

function tierClass(tierId) {
  return tierId === 'A-' ? 'Aminus' : tierId;
}

function tierBadge(tierId) {
  const cls = tierClass(tierId || 'C');
  return `<span class="tier-badge tier-${esc(cls)}">${esc(tierId || 'C')}</span>`;
}

function typeLabel(type) {
  return TYPE_LABEL[type] || '其他';
}

function avatarMarkup(item, name, className = 'unit-avatar') {
  const src = item && item.avatar ? item.avatar : '';
  const letter = esc((name || '?').slice(0, 2));
  if (!src) return `<div class="${className}"><span>${letter}</span></div>`;
  return `<div class="${className}"><span>${letter}</span><img src="${esc(src)}" alt="" loading="lazy" onerror="this.remove()"></div>`;
}

function toast(message) {
  const node = $('#toast');
  if (!node) return;
  node.textContent = message;
  node.hidden = false;
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => { node.hidden = true; }, 2200);
}

/* ------------------------------------------------------------------ */
/* Data loading / indexes                                              */
/* ------------------------------------------------------------------ */
async function fetchJSON(path) {
  const response = await fetch(path, { cache: 'no-cache' });
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
  return response.json();
}

async function loadData() {
  const [
    dolls, fairies, sangvis,
    dollTiers, fairyTiers, sangvisTiers,
    equipmentItems, equipmentTargets, sample,
  ] = await Promise.all([
    fetchJSON('data/codex/dolls.json'),
    fetchJSON('data/codex/fairies.json'),
    fetchJSON('data/codex/sangvis.json'),
    fetchJSON('data/tierlists/dolls.json'),
    fetchJSON('data/tierlists/fairies.json'),
    fetchJSON('data/tierlists/sangvis.json'),
    fetchJSON('data/equipment_items.json'),
    fetchJSON('data/equipment_targets.json'),
    fetchJSON('data/sample_account.json'),
  ]);
  DATA.codex = { doll: dolls, fairy: fairies, sangvis: sangvis };
  DATA.tiers = { doll: dollTiers, fairy: fairyTiers, sangvis: sangvisTiers };
  DATA.equipmentItems = equipmentItems;
  DATA.equipmentTargets = equipmentTargets;
  DATA.sample = sample;
  buildCodexIndexes();
  buildTierLookup();
  buildEquipmentIndex();
}

function buildCodexIndexes() {
  for (const kind of ['doll', 'fairy', 'sangvis']) {
    const items = DATA.codex[kind] || [];
    state.codexByKind[kind] = items.map((row) => ({ ...row, kind }));
    const byCode = new Map();
    for (const item of state.codexByKind[kind]) {
      byCode.set(item.code, item);
      const keys = new Set([item.code, item.name, item.en_name, ...(item.aliases || [])].filter(Boolean));
      for (const key of keys) {
        const norm = normalize(key);
        if (!norm) continue;
        if (!state.alias.has(norm)) state.alias.set(norm, []);
        const bucket = state.alias.get(norm);
        if (!bucket.some((entry) => entry.kind === kind && entry.code === item.code)) bucket.push(item);
      }
    }
    state.codexByCode[kind] = byCode;
  }
}

function buildTierLookup() {
  for (const kind of ['doll', 'fairy', 'sangvis']) {
    const raw = DATA.tiers[kind];
    const tierById = new Map();
    for (const tier of raw.tiers || []) tierById.set(tier.id, tier);
    const codeTier = new Map();
    const nameTier = new Map();
    for (const entry of raw.entries || []) {
      const tierId = entry.tier || raw.default_tier || 'C';
      if (!tierById.has(tierId)) continue;
      const names = [entry.name, ...(entry.aliases || [])].filter(Boolean);
      for (const name of names) {
        const norm = normalize(name);
        if (norm) nameTier.set(norm, tierId);
        for (const item of (state.alias.get(norm) || [])) {
          if (item.kind === kind) codeTier.set(item.code, tierId);
        }
      }
      if (entry.code) codeTier.set(entry.code, tierId);
    }
    const fallback = tierById.get(raw.default_tier || 'C') || tierById.values().next().value;
    state.tierLookup[kind] = { tierById, codeTier, nameTier, fallback, list: raw };
  }
}

function findCodex(kind, code, name = '') {
  const byCode = state.codexByCode[kind];
  if (code && byCode.has(code)) return byCode.get(code);
  for (const key of [code, name]) {
    const norm = normalize(key);
    if (!norm) continue;
    const hits = state.alias.get(norm) || [];
    const found = hits.find((item) => item.kind === kind);
    if (found) return found;
  }
  return null;
}

function tierFor(kind, code, name = '') {
  const lookup = state.tierLookup[kind];
  if (!lookup) return { id: 'C', label: 'C', score: 40, color: '#6f8299', name: '未上榜' };
  const id = lookup.codeTier.get(code) || lookup.nameTier.get(normalize(name)) || (lookup.fallback && lookup.fallback.id) || 'C';
  return lookup.tierById.get(id) || lookup.fallback;
}

/* ------------------------------------------------------------------ */
/* Equipment                                                           */
/* ------------------------------------------------------------------ */
function itemMatches(item, rule) {
  if (!rule) return false;
  if (rule.category !== undefined && Number(item.category) !== Number(rule.category)) return false;
  if (rule.type !== undefined && Number(item.type) !== Number(rule.type)) return false;
  const code = String(item.code || '').toLowerCase();
  const name = String(item.name || '').toLowerCase();
  for (const key of ['code_contains', 'name_contains']) {
    const value = String(rule[key] || '').toLowerCase();
    if (value && !(key === 'code_contains' ? code : name).includes(value)) return false;
  }
  for (const key of ['code_not_contains', 'name_not_contains']) {
    const value = String(rule[key] || '').toLowerCase();
    if (value && (key === 'code_not_contains' ? code : name).includes(value)) return false;
  }
  for (const value of rule.name_not_contains_any || []) {
    if (name.includes(String(value).toLowerCase())) return false;
  }
  return true;
}

function buildEquipmentIndex() {
  const payload = DATA.equipmentTargets;
  const hits = new Map();
  for (const category of payload.categories || []) {
    for (const target of category.items || []) {
      for (const item of DATA.equipmentItems) {
        if (!itemMatches(item, target.match)) continue;
        if (!hits.has(item.id)) hits.set(item.id, []);
        hits.get(item.id).push([category.id, target.id]);
      }
    }
  }
  state.equipment = { payload, hits };
}

function evaluateEquipment(rows) {
  const payload = state.equipment.payload;
  const hits = state.equipment.hits;
  const categories = (payload.categories || []).map((cat) => ({
    id: cat.id,
    name: cat.name,
    weight: Number(cat.weight || 0),
    targets: (cat.items || []).map((target) => ({
      id: target.id,
      name: target.name,
      target: Number(target.target || 0),
      current: 0,
    })),
  }));
  const byKey = new Map();
  for (const category of categories) {
    for (const target of category.targets) byKey.set(`${category.id}::${target.id}`, target);
  }
  for (const row of rows) {
    const infoId = num(row.info_id ?? row.infoId);
    for (const [categoryId, targetId] of hits.get(infoId) || []) {
      const target = byKey.get(`${categoryId}::${targetId}`);
      if (target) target.current += 1;
    }
  }
  let targetTotal = 0;
  let currentTotal = 0;
  let score = 0;
  let weightSum = 0;
  for (const category of categories) {
    const targetSum = category.targets.reduce((sum, item) => sum + item.target, 0);
    const currentSum = category.targets.reduce((sum, item) => sum + Math.min(item.current, item.target), 0);
    category.targetTotal = targetSum;
    category.currentTotal = currentSum;
    category.completion = targetSum ? (100 * currentSum / targetSum) : 0;
    targetTotal += targetSum;
    currentTotal += currentSum;
    if (targetSum) {
      score += category.weight * category.completion;
      weightSum += category.weight;
    }
  }
  score = weightSum ? score / weightSum : 0;
  return {
    title: payload.title || '装备需求',
    source: payload.source || '',
    categories,
    score,
    targetTotal,
    currentTotal,
    completion: targetTotal ? (100 * currentTotal / targetTotal) : 0,
    allTargets: categories.flatMap((category) => category.targets),
    gaps(limit = 8) {
      return [...this.allTargets]
        .filter((item) => item.current < item.target)
        .sort((a, b) => ((b.target - b.current) / Math.max(1, b.target)) - ((a.target - a.current) / Math.max(1, a.target)))
        .slice(0, limit);
    },
  };
}

/* ------------------------------------------------------------------ */
/* Account aggregation                                                 */
/* ------------------------------------------------------------------ */
function makeUnit(kind, code, name = '') {
  const item = findCodex(kind, code, name);
  const finalCode = item ? item.code : code;
  const finalName = item ? item.name : (name || code);
  return {
    kind,
    code: finalCode,
    name: finalName,
    type: item ? Number(item.type || 0) : 0,
    rank: item ? Number(item.rank || 0) : 0,
    item,
    tier: tierFor(kind, finalCode, finalName),
    level: 0,
    mod: 0,
    favor: 0,
    quality: 0,
    skill_level: 0,
    advance: 0,
    resolution_level: 0,
    team_id: 0,
    count: 1,
    copies: [],
  };
}

function aggregateDolls(rows) {
  const grouped = groupBy(rows.filter((row) => row && row.code), (row) => String(row.code));
  const units = [];
  for (const [code, items] of grouped) {
    const ordered = [...items].sort((a, b) => num(b.level) - num(a.level) || num(b.mod) - num(a.mod));
    const best = ordered[0];
    const unit = makeUnit('doll', code, code);
    unit.level = num(best.level);
    unit.mod = num(best.mod);
    unit.count = items.length;
    unit.favor = Math.max(...items.map((row) => num(row.favor)), 0);
    unit.team_id = Math.max(...items.map((row) => num(row.team_id ?? row.teamId)), 0);
    unit.copies = ordered.map((row) => ({
      uid: num(row.uid),
      level: num(row.level),
      mod: num(row.mod),
      favor: num(row.favor),
      team_id: num(row.team_id ?? row.teamId),
      skin_id: num(row.skin_id ?? row.skinId),
      location: num(row.location),
    }));
    units.push(unit);
  }
  return sortUnits(units);
}

function aggregateFairies(rows) {
  const grouped = groupBy(rows.filter((row) => row && row.code), (row) => String(row.code).replace(/_\d+$/, ''));
  const units = [];
  for (const [base, items] of grouped) {
    const ordered = [...items].sort((a, b) =>
      num(b.quality ?? b.qualityLevel) - num(a.quality ?? a.qualityLevel)
      || num(b.level) - num(a.level)
      || num(b.skill_level ?? b.mainSkillLevel) - num(a.skill_level ?? a.mainSkillLevel));
    const best = ordered[0];
    const unit = makeUnit('fairy', base, base);
    unit.level = num(best.level);
    unit.quality = num(best.quality ?? best.qualityLevel);
    unit.skill_level = num(best.skill_level ?? best.mainSkillLevel);
    unit.mod = num(best.mod);
    unit.count = items.length;
    unit.team_id = Math.max(...items.map((row) => num(row.team_id ?? row.teamId)), 0);
    unit.copies = ordered.map((row) => ({
      id: num(row.id),
      level: num(row.level),
      quality: num(row.quality ?? row.qualityLevel),
      skill_level: num(row.skill_level ?? row.mainSkillLevel),
      mod: num(row.mod),
      team_id: num(row.team_id ?? row.teamId),
      equip_id: num(row.equip_id ?? row.equipId),
    }));
    units.push(unit);
  }
  return sortUnits(units);
}

function aggregateSangvis(rows) {
  const grouped = groupBy(rows.filter((row) => row && row.code), (row) => String(row.code));
  const units = [];
  for (const [code, items] of grouped) {
    const ordered = [...items].sort((a, b) => num(b.level) - num(a.level) || num(b.advance) - num(a.advance));
    const best = ordered[0];
    const unit = makeUnit('sangvis', code, code);
    unit.level = num(best.level);
    unit.advance = num(best.advance);
    unit.resolution_level = num(best.resolution_level ?? best.resolutionLevel);
    unit.count = items.length;
    unit.team_id = num(best.team_id ?? best.teamId);
    unit.copies = ordered.map((row) => ({
      info_id: num(row.info_id ?? row.infoId),
      level: num(row.level),
      advance: num(row.advance),
      resolution_level: num(row.resolution_level ?? row.resolutionLevel),
      team_id: num(row.team_id ?? row.teamId),
    }));
    units.push(unit);
  }
  return sortUnits(units);
}

function sortUnits(units) {
  return units.sort((a, b) =>
    (b.tier?.score || 0) - (a.tier?.score || 0)
    || b.level - a.level
    || a.name.localeCompare(b.name, 'zh-Hans-CN'));
}

function buildAccount(payload) {
  const meta = payload.meta || {};
  const dolls = aggregateDolls(payload.dolls || []);
  const fairies = aggregateFairies(payload.fairies || []);
  const sangvis = aggregateSangvis(payload.sangvis || []);
  return {
    meta,
    dolls,
    fairies,
    sangvis,
    units: { doll: dolls, fairy: fairies, sangvis },
    equipment: evaluateEquipment(payload.equipment || []),
    teams: payload.teams || [],
    squads: payload.squads || [],
    vehicles: payload.vehicles || [],
  };
}

/* ------------------------------------------------------------------ */
/* Evaluation                                                          */
/* ------------------------------------------------------------------ */
function gradeFor(score) {
  if (score >= 90) return 'SS';
  if (score >= 80) return 'S';
  if (score >= 70) return 'A';
  if (score >= 60) return 'B';
  return 'C';
}

function unitRating(kind, units, options) {
  const lookup = state.tierLookup[kind];
  const counts = Object.fromEntries((lookup.list.tiers || []).map((tier) => [tier.id, 0]));
  for (const unit of units) counts[unit.tier.id] = (counts[unit.tier.id] || 0) + 1;
  const ranked = [...units].sort((a, b) => (b.tier?.score || 0) - (a.tier?.score || 0) || b.level - a.level);
  const top = ranked.slice(0, options.topN);
  const depth = top.length ? top.reduce((sum, unit) => sum + (unit.tier?.score || 0), 0) / top.length : 0;
  const breadth = units.length ? Math.min(100, 100 * units.length / options.breadthTarget) : 0;
  const score = units.length ? depth * options.weightDepth + breadth * (1 - options.weightDepth) : 0;
  const summary = options.summary(units, counts);
  return {
    key: kind,
    title: options.title,
    subtitle: options.subtitle,
    score,
    grade: gradeFor(score),
    counts,
    owned: units.length,
    total: (lookup.list.entries || []).length,
    summary,
    topUnits: top,
  };
}

function equipmentRating(account) {
  const report = account.equipment;
  const counts = {
    ok: report.allTargets.filter((item) => item.current >= item.target).length,
    warn: report.allTargets.filter((item) => item.current < item.target && item.current >= item.target * 0.6).length,
    low: report.allTargets.filter((item) => item.current < item.target * 0.6).length,
  };
  return {
    key: 'equipment',
    title: '装备储备',
    subtitle: '目标个数 vs 当前个数',
    score: report.score,
    grade: gradeFor(report.score),
    counts,
    owned: report.currentTotal,
    total: report.targetTotal,
    summary: `${report.currentTotal}/${report.targetTotal} 件目标储备（完成度 ${report.completion.toFixed(0)}%）；${counts.ok} 项达标、${counts.low} 项缺口较大。`,
    report,
  };
}

function evaluateAccount(account) {
  const doll = unitRating('doll', account.dolls, {
    title: '人形强度',
    subtitle: '仓库 / 三体人与常用好手',
    topN: 12,
    breadthTarget: 260,
    weightDepth: 0.7,
    summary: (units, counts) => `已拥有 ${units.length} 个不同人形；SS ${counts.SS || 0} 名、S ${counts.S || 0} 名。`,
  });
  const fairy = unitRating('fairy', account.fairies, {
    title: '妖精强度',
    subtitle: '空降 / T0-T2 战略妖精',
    topN: 6,
    breadthTarget: 41,
    weightDepth: 0.75,
    summary: (units, counts) => `已拥有 ${units.length} 种妖精；SS ${counts.SS || 0} 种、S ${counts.S || 0} 种。`,
  });
  const sangvis = unitRating('sangvis', account.sangvis, {
    title: '融合势力',
    subtitle: '稻草人 / 铁血捕获单位',
    topN: 5,
    breadthTarget: 40,
    weightDepth: 0.75,
    summary: (units, counts) => `已记录 ${units.length} 个融合势力单位；SS ${counts.SS || 0} 个、A ${counts.A || 0} 个。`,
  });
  const equipment = equipmentRating(account);
  const overallScore = doll.score * 0.4 + fairy.score * 0.2 + sangvis.score * 0.2 + equipment.score * 0.2;
  const equipmentGaps = account.equipment.gaps(6);
  const recommendations = [];
  if ((doll.counts.SS || 0) === 0) recommendations.push('人形缺少 SS 级（三体人）：优先补齐 TPS / 索米 / SCAR 等核心。');
  else if ((doll.counts.SS || 0) < 3) recommendations.push(`人形 SS 仅 ${doll.counts.SS} 名，建议继续补强三体人深度。`);
  if ((doll.counts.S || 0) < 8) recommendations.push('S 级常用好手不足 8 名，秃洞编队会吃紧。');
  if ((fairy.counts.SS || 0) === 0) recommendations.push('妖精缺少空降（T0/SS），优先把空降妖精纳入计划。');
  else if ((fairy.counts.S || 0) < 3) recommendations.push('T1 妖精深度偏浅，建议补护盾 / 狙击 / 海滩。');
  if ((sangvis.counts.SS || 0) === 0) recommendations.push('融合势力缺少稻草人（SS），策略位会明显受限。');
  for (const item of equipmentGaps.slice(0, 4)) {
    recommendations.push(`装备缺口：${item.name} ${item.current}/${item.target}（差 ${item.target - item.current}）。`);
  }
  if (!recommendations.length) recommendations.push('四维均无明显短板，继续补图鉴与高难特化解即可。');
  return {
    account,
    doll,
    fairy,
    sangvis,
    equipment,
    overallScore,
    overallGrade: gradeFor(overallScore),
    recommendations: recommendations.slice(0, 6),
    equipmentGaps,
  };
}

function setAccount(payload, sourceLabel = '快照', persist = true) {
  if (!payload || typeof payload !== 'object') throw new Error('快照不是 JSON 对象');
  if (!payload.dolls && !payload.fairies && !payload.sangvis && !payload.equipment) {
    throw new Error('快照缺少 dolls / fairies / sangvis / equipment 字段');
  }
  const account = buildAccount(payload);
  state.account = account;
  state.evaluation = evaluateAccount(account);
  if (persist) {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(payload)); } catch (_) { /* private mode */ }
  }
  updateAccountChip(sourceLabel);
  renderPage();
}

function updateAccountChip(sourceLabel) {
  const chip = $('#accountChip');
  if (!chip) return;
  if (!state.account) {
    chip.textContent = '未载入';
    return;
  }
  const account = state.account;
  const level = account.meta.level ? ` · Lv.${account.meta.level}` : '';
  chip.textContent = `${account.meta.nickname || '未命名指挥官'} · ${account.meta.uid || 'UID?'}${level}`;
  chip.title = `${sourceLabel} · ${account.meta.captured_at || ''}`;
}

/* ------------------------------------------------------------------ */
/* Render helpers                                                      */
/* ------------------------------------------------------------------ */
function pageHead(title, subtitle, extra = '') {
  return `<div class="page-head"><div><h1>${esc(title)}</h1><p>${esc(subtitle)}</p></div><div class="spacer"></div>${extra}</div>`;
}

function tierRowsHTML(kind, rating) {
  const tiers = state.tierLookup[kind].list.tiers || [];
  const max = Math.max(...tiers.map((tier) => rating.counts[tier.id] || 0), 1);
  return tiers.map((tier) => {
    const count = rating.counts[tier.id] || 0;
    return `<div class="tier-row">
      <span class="tier-name">${esc(tier.id)}</span>
      <span class="tier-track"><i style="width:${(100 * count / max).toFixed(1)}%;background:${esc(tier.color || '#6f8299')}"></i></span>
      <span class="tier-count">${count}</span>
    </div>`;
  }).join('');
}

function statusRowsHTML(rating) {
  const rows = [
    ['达标', rating.counts.ok || 0, 'var(--green)'],
    ['接近', rating.counts.warn || 0, 'var(--orange)'],
    ['缺口', rating.counts.low || 0, 'var(--red)'],
  ];
  const max = Math.max(...rows.map((row) => row[1]), 1);
  return rows.map(([label, count, color]) => `<div class="tier-row">
    <span class="tier-name" style="width:32px">${label}</span>
    <span class="tier-track"><i style="width:${(100 * count / max).toFixed(1)}%;background:${color}"></i></span>
    <span class="tier-count">${count}</span>
  </div>`).join('');
}

function statCard(kind, rating) {
  const rows = kind === 'equipment' ? statusRowsHTML(rating) : tierRowsHTML(kind, rating);
  return `<article class="card stat-card">
    <div class="stat-head"><div><div class="stat-title">${esc(rating.title)}</div><div class="stat-sub">${esc(rating.subtitle)}</div></div>${tierBadge(rating.grade)}</div>
    <div class="stat-score">${rating.score.toFixed(0)} <small>/ 100</small></div>
    <div class="stat-bar"><i style="width:${pct(rating.score).toFixed(1)}%"></i></div>
    ${rows}
    <div class="stat-summary">${esc(rating.summary)}</div>
  </article>`;
}

function radarSVG(evaluation) {
  const values = [
    ['人形', evaluation.doll.score],
    ['妖精', evaluation.fairy.score],
    ['融合', evaluation.sangvis.score],
    ['装备', evaluation.equipment.score],
  ];
  const cx = 160, cy = 112, radius = 80;
  const point = (index, ratio) => {
    const angle = -Math.PI / 2 + (2 * Math.PI * index) / values.length;
    return [cx + Math.cos(angle) * radius * ratio, cy + Math.sin(angle) * radius * ratio];
  };
  const grids = [0.25, 0.5, 0.75, 1].map((level) => {
    const points = values.map((_, index) => point(index, level).map((v) => v.toFixed(1)).join(',')).join(' ');
    return `<polygon points="${points}" fill="none" stroke="#d6e4f5" stroke-width="1"/>`;
  }).join('');
  const axes = values.map((_, index) => {
    const [x, y] = point(index, 1);
    return `<line x1="${cx}" y1="${cy}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" stroke="#d6e4f5" stroke-width="1"/>`;
  }).join('');
  const dataPoints = values.map(([, score], index) => point(index, pct(score) / 100).map((v) => v.toFixed(1)).join(',')).join(' ');
  const dots = values.map(([, score], index) => {
    const [x, y] = point(index, pct(score) / 100);
    return `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="3.5" fill="#2474e5"/>`;
  }).join('');
  const labels = values.map(([label, score], index) => {
    const [x, y] = point(index, 1.22);
    return `<text x="${x.toFixed(1)}" y="${(y + 4).toFixed(1)}" text-anchor="middle" font-size="11" fill="#5f7590">${esc(label)} ${score.toFixed(0)}</text>`;
  }).join('');
  return `<svg viewBox="0 0 320 230" role="img" aria-label="四维雷达图">${grids}${axes}
    <polygon points="${dataPoints}" fill="rgba(36,116,229,.10)" stroke="#2474e5" stroke-width="2"/>${dots}${labels}</svg>`;
}

function renderDashboard() {
  const ev = state.evaluation;
  if (!ev) return pageHead('总览', '等待账号数据') + '<div class="card empty">尚未载入快照</div>';
  const account = ev.account;
  const topAvatars = ev.doll.topUnits.slice(0, 7).map((unit) => avatarMarkup(unit.item, unit.name, 'hero-avatar')).join('');
  const tips = ev.recommendations.map((tip) => `<li>${esc(tip)}</li>`).join('');
  const gaps = ev.equipmentGaps.map((item) => {
    const color = item.current >= item.target * 0.6 ? 'var(--orange)' : 'var(--red)';
    return `<div class="gap-row">
      <span class="gap-name">${esc(item.name)}</span>
      <span class="gap-track"><i style="width:${pct(item.current / Math.max(1, item.target) * 100).toFixed(1)}%;background:${color}"></i></span>
      <span class="gap-value">${item.current}/${item.target}</span>
      <span class="gap-left">差 ${item.target - item.current}</span>
    </div>`;
  }).join('') || '<div class="empty" style="padding:20px 0">全部达标</div>';
  return `${pageHead('总览', '四维评分与下一步建议')}
  <section class="hero">
    <div class="hero-card">
      <div class="eyebrow">ACCOUNT OVERVIEW</div>
      <div class="hero-name">${esc(account.meta.nickname || '未命名指挥官')}</div>
      <div class="hero-meta">Lv.${esc(account.meta.level || '—')} · UID ${esc(account.meta.uid || '—')} · ${esc((account.meta.captured_at || '').replace('T', ' ').slice(0, 19))} · ${account.dolls.length} 人形 / ${account.fairies.length} 妖精 / ${account.sangvis.length} 融合势力 / ${account.vehicles.length} 载具</div>
      <div class="hero-score-row"><div class="hero-score">${ev.overallScore.toFixed(0)}</div><div class="hero-grade">${esc(ev.overallGrade)}</div></div>
      <div class="hero-note">评分按人形 40% / 妖精 20% / 融合势力 20% / 装备 20% 加权；点击上方或底部导航查看明细。</div>
      <div class="hero-avatars">${topAvatars}</div>
    </div>
    <div class="card radar-card"><h3>四维雷达</h3><div class="section-sub">人形 / 妖精 / 融合势力 / 装备</div><div class="radar-wrap">${radarSVG(ev)}</div></div>
  </section>
  <section class="stat-grid">${statCard('doll', ev.doll)}${statCard('fairy', ev.fairy)}${statCard('sangvis', ev.sangvis)}${statCard('equipment', ev.equipment)}</section>
  <section class="bottom-grid">
    <div class="card tips-card"><h3 class="section-title">下一步建议</h3><div class="section-sub">按四维评分自动生成，优先补短板</div><ul class="tips-list">${tips}</ul></div>
    <div class="card gaps-card"><h3 class="section-title">装备缺口</h3><div class="section-sub">目标来自「装备需求一图流」</div>${gaps}</div>
  </section>`;
}

function filterBarHTML(key, kind, codexMode) {
  const cfg = state.grid[key];
  const tiers = state.tierLookup[kind].list.tiers || [];
  const chips = [`全部`, ...tiers.map((tier) => tier.id)].map((id) => {
    const active = id === '全部' ? cfg.tiers.size === 0 : cfg.tiers.has(id);
    return `<button class="chip ${active ? 'active' : ''}" type="button" data-action="tier" data-key="${esc(key)}" data-tier="${esc(id)}">${esc(id)}</button>`;
  }).join('');
  const typeSelect = kind === 'doll' ? `<select class="type-select" data-action="type" data-key="${esc(key)}">
    <option value="0"${cfg.type === 0 ? ' selected' : ''}>全部类型</option>
    ${[[1, 'HG 手枪'], [2, 'SMG 冲锋枪'], [3, 'RF 步枪'], [4, 'AR 突击步枪'], [5, 'MG 机枪'], [6, 'SG 霰弹枪']].map(([id, label]) => `<option value="${id}"${cfg.type === id ? ' selected' : ''}>${label}</option>`).join('')}
  </select>` : '';
  return `<div class="filter-bar">
    <input class="search-input" type="search" placeholder="搜索名称 / 代号…" value="${esc(cfg.query)}" data-action="search" data-key="${esc(key)}" autocomplete="off">
    ${chips}
    ${typeSelect}
    <label class="owned-label"><input type="checkbox" data-action="owned" data-key="${esc(key)}" ${cfg.ownedOnly ? 'checked' : ''}>只看已拥有</label>
  </div>`;
}

function unitPageHTML(kind, codexMode = false) {
  const key = codexMode ? `codex_${kind}` : kind;
  const title = codexMode ? '全量图鉴' : (KIND_LABEL[kind] + '仓库');
  const subtitle = codexMode ? '不依赖仓库快照：所有人形 / 妖精 / 融合势力，含未拥有单位。' : (TITLES[kind][1]);
  const kindTabs = codexMode ? `<div class="codex-kinds">
    ${['doll', 'fairy', 'sangvis'].map((k) => `<button class="chip ${state.codexKind === k ? 'active' : ''}" type="button" data-action="codex-kind" data-kind="${k}">${KIND_LABEL[k]}</button>`).join('')}
  </div>` : '';
  return `${pageHead(title, subtitle)}
    ${kindTabs}
    ${filterBarHTML(key, kind, codexMode)}
    <div class="grid-count" id="count-${esc(key)}"></div>
    <div class="unit-grid" id="grid-${esc(key)}"></div>
    <button class="btn ghost more-button" type="button" data-action="more" data-key="${esc(key)}" hidden>加载更多</button>`;
}

function renderUnitPage(kind, codexMode = false) {
  return unitPageHTML(kind, codexMode);
}

function renderEquipmentPage() {
  const ev = state.evaluation;
  if (!ev) return pageHead('装备', '目标个数 vs 当前个数') + '<div class="card empty">尚未载入快照</div>';
  const report = ev.account.equipment;
  const categories = report.categories.map((category) => {
    const color = category.completion >= 100 ? 'var(--green)' : category.completion >= 70 ? 'var(--orange)' : 'var(--red)';
    return `<div class="card equip-cat"><h3>${esc(category.name)}<span class="cat-pct" style="color:${color}">${category.completion.toFixed(0)}%</span></h3><div class="cat-value">${category.currentTotal} / ${category.targetTotal} 目标 · 权重 ${(category.weight * 100).toFixed(0)}%</div><div class="stat-bar"><i style="width:${pct(category.completion).toFixed(1)}%;background:${color}"></i></div></div>`;
  }).join('');
  const sections = report.categories.map((category) => {
    const rows = category.targets.map((item) => {
      const ratio = item.target ? item.current / item.target : 0;
      const color = ratio >= 1 ? 'var(--green)' : ratio >= 0.6 ? 'var(--orange)' : 'var(--red)';
      return `<div class="equip-row"><span class="eq-name">${esc(item.name)}</span><span class="eq-track"><i style="width:${pct(ratio * 100).toFixed(1)}%;background:${color}"></i></span><span class="eq-value" style="color:${color}">${item.current}/${item.target}</span><span class="eq-gap">${item.current >= item.target ? '达标' : `差 ${item.target - item.current}`}</span></div>`;
    }).join('');
    return `<section class="card equip-section"><h3>${esc(category.name)} · ${category.currentTotal}/${category.targetTotal}</h3>${rows}</section>`;
  }).join('');
  return `${pageHead('装备', '目标个数 vs 当前个数')}
    <section class="card equip-hero"><div class="left"><div class="eyebrow">EQUIPMENT RESERVE</div><h1>装备储备</h1><div class="hero-meta">${report.currentTotal}/${report.targetTotal} 件 · 完成度 ${report.completion.toFixed(0)}% · ${report.allTargets.filter((item) => item.current >= item.target).length}/${report.allTargets.length} 项达标</div></div><div><div class="equip-score">${report.score.toFixed(0)}</div><div class="equip-grade">${tierBadge(ev.equipment.grade)}</div></div></section>
    <section class="equip-cats">${categories}</section>${sections}`;
}

/* ------------------------------------------------------------------ */
/* Unit grid                                                           */
/* ------------------------------------------------------------------ */
function gridRows(key, kind, codexMode, cfg) {
  const owned = new Map(state.account.units[kind].map((unit) => [unit.code, unit]));
  const rows = [];
  if (codexMode || !cfg.ownedOnly) {
    for (const item of state.codexByKind[kind]) {
      const unit = owned.get(item.code) || null;
      rows.push({ item, unit });
    }
    const known = new Set(state.codexByKind[kind].map((item) => item.code));
    for (const [code, unit] of owned) {
      if (!known.has(code)) rows.push({ item: unit.item || unit, unit });
    }
  } else {
    for (const unit of state.account.units[kind]) rows.push({ item: unit.item || unit, unit });
  }
  return rows;
}

function unitFilterText(cfg) {
  return cfg.tiers.size ? [...cfg.tiers].sort().join(' + ') : '全部';
}

function renderGrid(key) {
  if (!state.account) return;
  const codexMode = key.startsWith('codex_');
  const kind = codexMode ? key.slice(6) : key;
  const cfg = state.grid[key];
  const grid = document.getElementById(`grid-${key}`);
  const count = document.getElementById(`count-${key}`);
  const more = document.querySelector(`[data-action="more"][data-key="${key}"]`);
  if (!grid) return;
  let rows = gridRows(key, kind, codexMode, cfg);
  const query = cfg.query.trim().toLowerCase();
  rows = rows.filter(({ item, unit }) => {
    if (cfg.ownedOnly && !unit) return false;
    const itemTier = unit ? unit.tier : tierFor(kind, item.code, item.name);
    if (cfg.tiers.size && !cfg.tiers.has(itemTier.id)) return false;
    if (kind === 'doll' && cfg.type && Number(item.type || 0) !== cfg.type) return false;
    if (query && !`${item.name || ''} ${item.code || ''}`.toLowerCase().includes(query)) return false;
    return true;
  });
  rows.sort((a, b) => {
    const ao = a.unit ? 0 : 1;
    const bo = b.unit ? 0 : 1;
    if (ao !== bo) return ao - bo;
    const at = a.unit ? a.unit.tier?.score || 0 : tierFor(kind, a.item.code, a.item.name).score || 0;
    const bt = b.unit ? b.unit.tier?.score || 0 : tierFor(kind, b.item.code, b.item.name).score || 0;
    if (at !== bt) return bt - at;
    const al = a.unit ? a.unit.level || 0 : 0;
    const bl = b.unit ? b.unit.level || 0 : 0;
    if (al !== bl) return bl - al;
    return String(a.item.name || '').localeCompare(String(b.item.name || ''), 'zh-Hans-CN');
  });
  const total = rows.length;
  const shown = rows.slice(0, cfg.limit);
  if (count) count.textContent = `${total} 条 · ${unitFilterText(cfg)} · 显示 ${shown.length}`;
  grid.innerHTML = shown.length ? shown.map(({ item, unit }) => unitCardHTML(kind, key, item, unit)).join('') : '<div class="empty">没有符合条件的单位</div>';
  if (more) {
    more.hidden = total <= shown.length;
    more.textContent = `加载更多（剩余 ${Math.max(0, total - shown.length)}）`;
  }
}

function unitCardHTML(kind, key, item, unit) {
  const owned = Boolean(unit);
  const tier = unit ? unit.tier : tierFor(kind, item.code, item.name);
  let subtitle = '';
  let footer = '未拥有 · 图鉴';
  if (kind === 'doll') {
    subtitle = `${typeLabel(item.type)} · ${item.code}`;
    if (owned) footer = `Lv.${unit.level} · 复制 ${unit.count}`;
  } else if (kind === 'fairy') {
    subtitle = `妖精 · ${item.code}`;
    if (owned) footer = unit.count > 1 ? `共 ${unit.count} 只 · 最高 ${unit.quality}★` : `Lv.${unit.level} · ${unit.quality}★`;
  } else {
    subtitle = `融合势力 · ${item.code}`;
    if (owned) footer = `Lv.${unit.level} · 解析 ${unit.resolution_level}`;
  }
  return `<article class="unit-card ${owned ? '' : 'unowned'}" data-action="unit" data-kind="${kind}" data-key="${key}" data-code="${esc(item.code)}">
    ${avatarMarkup(item, item.name)}
    <div class="unit-name" title="${esc(item.name)}">${esc(item.name)}</div>
    <div class="unit-sub">${esc(subtitle)}</div>
    ${tierBadge(tier.id)}
    <div class="unit-footer">${esc(footer)}</div>
  </article>`;
}

/* ------------------------------------------------------------------ */
/* Details                                                             */
/* ------------------------------------------------------------------ */
function copyRowsHTML(unit, kind) {
  if (!unit || !unit.copies || !unit.copies.length) {
    return `<div class="detail-note">快照中没有逐条复制记录；仅知道共 ${unit ? unit.count : 0} 份。</div>`;
  }
  if (kind === 'fairy') {
    const groups = new Map();
    for (const copy of unit.copies) {
      if (!groups.has(copy.quality)) groups.set(copy.quality, []);
      groups.get(copy.quality).push(copy);
    }
    return [...groups.entries()].sort((a, b) => b[0] - a[0]).map(([quality, copies]) => `
      <div class="quality-group"><div class="quality-title">${quality}★ × ${copies.length}</div>
      ${copies.map((copy) => `<div class="copy-row"><span>Lv.${copy.level}</span><span>技能 ${copy.skill_level}</span>${copy.mod ? `<span>改造 ${copy.mod}</span>` : ''}${copy.equip_id ? `<span>装备 ${copy.equip_id}</span>` : ''}${copy.team_id ? `<span>编队 ${copy.team_id}</span>` : ''}<span class="copy-id">#${copy.id}</span></div>`).join('')}
      </div>`).join('');
  }
  if (kind === 'doll') {
    return unit.copies.map((copy) => `<div class="copy-row"><span>Lv.${copy.level}</span><span>改造 ${copy.mod}</span><span>好感 ${copy.favor}</span>${copy.team_id ? `<span>编队 ${copy.team_id}</span>` : ''}${copy.skin_id ? `<span>皮肤 ${copy.skin_id}</span>` : ''}<span class="copy-id">#${copy.uid}</span></div>`).join('');
  }
  return unit.copies.map((copy) => `<div class="copy-row"><span>Lv.${copy.level}</span><span>扩编 ${copy.advance}</span><span>解析 ${copy.resolution_level}</span>${copy.team_id ? `<span>编队 ${copy.team_id}</span>` : ''}<span class="copy-id">#${copy.info_id}</span></div>`).join('');
}

function openDetail(kind, code) {
  const item = findCodex(kind, code) || { code, name: code, type: 0, rank: 0, avatar: '' };
  const unit = state.account ? state.account.units[kind].find((entry) => entry.code === item.code) : null;
  const tier = unit ? unit.tier : tierFor(kind, item.code, item.name);
  let summary = '';
  let body = '';
  if (unit) {
    if (kind === 'fairy') {
      summary = `<div class="detail-summary"><strong>共 ${unit.count} 只 · 最高配置 Lv.${unit.level}</strong><span>品质分布：${[...new Set(unit.copies.map((copy) => copy.quality))].sort((a, b) => b - a).map((quality) => `${quality}★ × ${unit.copies.filter((copy) => copy.quality === quality).length}`).join(' · ')}</span></div>`;
    } else if (kind === 'doll') {
      summary = `<div class="detail-summary"><strong>共 ${unit.count} 份 · 最高配置 Lv.${unit.level}</strong><span>最高改造 ${unit.mod} · 最高好感 ${unit.favor}</span></div>`;
    } else {
      summary = `<div class="detail-summary"><strong>共 ${unit.count} 个 · 最高 Lv.${unit.level}</strong><span>扩编 ${unit.advance} · 解析 ${unit.resolution_level}</span></div>`;
    }
    body = copyRowsHTML(unit, kind);
  } else {
    summary = '<div class="detail-summary"><strong>图鉴单位</strong><span>当前账号尚未拥有。</span></div>';
    body = '<div class="detail-note">导入包含该单位的快照后，可查看逐条复制记录。</div>';
  }
  const modalBody = $('#modalBody');
  modalBody.innerHTML = `<div class="detail-head">
    ${avatarMarkup(item, item.name, 'detail-avatar')}
    <div><h2 class="detail-name" id="modalTitle">${esc(item.name)}</h2><div class="detail-code">${esc(item.code)}</div><div class="detail-tier-line">${tierBadge(tier.id)}<span>${esc(state.tierLookup[kind].list.title || '强度榜')} · ${esc(tier.name || '')}</span></div></div>
  </div>${summary}${body}<div class="detail-note">数据来源：当前载入的账号快照；逐条记录保留等级 / 品质 / 技能 / 编队等原始字段。</div>`;
  $('#modal').hidden = false;
  document.body.classList.add('modal-open');
}

function closeModal() {
  $('#modal').hidden = true;
  document.body.classList.remove('modal-open');
}

/* ------------------------------------------------------------------ */
/* Navigation / events                                                 */
/* ------------------------------------------------------------------ */
function syncTabs() {
  for (const button of $$('[data-tab]')) {
    button.classList.toggle('active', button.dataset.tab === state.tab);
  }
}

function renderPage() {
  const main = $('#main');
  if (!main || !state.evaluation) return;
  if (state.tab === 'dashboard') main.innerHTML = renderDashboard();
  else if (UNIT_TABS.has(state.tab)) main.innerHTML = renderUnitPage(state.tab, false);
  else if (state.tab === 'equipment') main.innerHTML = renderEquipmentPage();
  else if (state.tab === 'codex') main.innerHTML = renderUnitPage(state.codexKind, true);
  syncTabs();
  if (UNIT_TABS.has(state.tab)) renderGrid(state.tab);
  if (state.tab === 'codex') renderGrid(`codex_${state.codexKind}`);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function showTab(tab) {
  if (!TITLES[tab] && tab !== 'codex') return;
  state.tab = tab;
  renderPage();
}

function onTierClick(button) {
  const key = button.dataset.key;
  const tier = button.dataset.tier;
  const cfg = state.grid[key];
  if (!cfg) return;
  if (tier === '全部') cfg.tiers.clear();
  else if (cfg.tiers.has(tier)) cfg.tiers.delete(tier);
  else cfg.tiers.add(tier);
  cfg.limit = 120;
  syncChips(key);
  renderGrid(key);
}

function syncChips(key) {
  const cfg = state.grid[key];
  if (!cfg) return;
  for (const button of $$('[data-action="tier"]')) {
    if (button.dataset.key !== key) continue;
    const tier = button.dataset.tier;
    const active = tier === '全部' ? cfg.tiers.size === 0 : cfg.tiers.has(tier);
    button.classList.toggle('active', active);
  }
}

function onGridEvent(event) {
  const actionNode = event.target.closest('[data-action]');
  if (!actionNode) return;
  const action = actionNode.dataset.action;
  if (action === 'unit') {
    openDetail(actionNode.dataset.kind, actionNode.dataset.code);
  } else if (action === 'tier') {
    onTierClick(actionNode);
  } else if (action === 'more') {
    const key = actionNode.dataset.key;
    state.grid[key].limit += 120;
    renderGrid(key);
  } else if (action === 'codex-kind') {
    state.codexKind = actionNode.dataset.kind;
    renderPage();
  } else if (action === 'close-modal') {
    closeModal();
  }
}

function onGridChange(event) {
  const node = event.target.closest('[data-action]');
  if (!node) return;
  const action = node.dataset.action;
  if (action === 'owned') {
    state.grid[node.dataset.key].ownedOnly = node.checked;
    state.grid[node.dataset.key].limit = 120;
    renderGrid(node.dataset.key);
  } else if (action === 'type') {
    state.grid[node.dataset.key].type = Number(node.value || 0);
    state.grid[node.dataset.key].limit = 120;
    renderGrid(node.dataset.key);
  }
}

function onGridInput(event) {
  const node = event.target.closest('[data-action="search"]');
  if (!node) return;
  state.grid[node.dataset.key].query = node.value;
  state.grid[node.dataset.key].limit = 120;
  renderGrid(node.dataset.key);
}

async function onFile(event) {
  const file = event.target.files && event.target.files[0];
  if (!file) return;
  try {
    const text = await file.text();
    const payload = JSON.parse(text);
    setAccount(payload, `导入：${file.name}`);
    toast('快照已导入');
  } catch (error) {
    console.error(error);
    toast(`快照导入失败：${error.message}`);
  } finally {
    event.target.value = '';
  }
}

function applyExample() {
  try { localStorage.removeItem(STORAGE_KEY); } catch (_) { /* ignore */ }
  setAccount(DATA.sample, '内置示例');
  toast('已恢复内置示例');
}

function registerSW() {
  if ('serviceWorker' in navigator && location.protocol.startsWith('http')) {
    navigator.serviceWorker.register('sw.js').catch((error) => console.warn('SW registration failed', error));
  }
}

function loadInitialAccount() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const payload = JSON.parse(raw);
      setAccount(payload, '本地快照', false);
      return;
    }
  } catch (error) {
    console.warn('localStorage snapshot failed', error);
  }
  setAccount(DATA.sample, '内置示例', false);
}

async function init() {
  const main = $('#main');
  try {
    await loadData();
    try { loadInitialAccount(); } catch (error) {
      console.error(error);
      main.innerHTML = `<div class="card empty">数据初始化失败：${esc(error.message)}</div>`;
      return;
    }
    $('#importButton').addEventListener('click', () => $('#fileInput').click());
    $('#fileInput').addEventListener('change', onFile);
    $('#exampleButton').addEventListener('click', applyExample);
    for (const button of $$('[data-tab]')) {
      button.addEventListener('click', () => showTab(button.dataset.tab));
    }
    main.addEventListener('click', onGridEvent);
    main.addEventListener('change', onGridChange);
    main.addEventListener('input', onGridInput);
    $('#modal').addEventListener('click', (event) => {
      if (event.target.closest('[data-action="close-modal"]')) closeModal();
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') closeModal();
    });
    registerSW();
  } catch (error) {
    console.error(error);
    if (main) {
      main.innerHTML = `<div class="card empty">数据加载失败：${esc(error.message)}<br><br>请通过本地 HTTP 服务器打开（不要直接双击 index.html）。</div>`;
    }
  }
}

document.addEventListener('DOMContentLoaded', init);
