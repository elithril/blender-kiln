// Kiln Studio's words and numbers. Every string the page shows goes through t(): the
// English text is the key, so the page reads the same without a dictionary, and each
// other language maps it. Numbers, sizes and lengths are formatted for the language.
// Note text and Claude's replies are the user's and Claude's own words: never translated.

const DICTS = { en: {} };
const CHECKS = { en: {} };   // checks.py MESSAGES, per language
let lang = 'en';
let units = 'm';

export const LANGS = { en: 'English', fr: 'Français' };
// A language's words: static/i18n/<code>.json, { "ui": {English: …}, "checks": {code: …} }.
export async function loadLanguage(code) {
  if (code === 'en' || DICTS[code]) return;
  const r = await fetch(`/static/i18n/${code}.json`);
  if (!r.ok) throw new Error(`${code}: ${r.status}`);
  const d = await r.json();
  DICTS[code] = d.ui || {};
  CHECKS[code] = d.checks || {};
}
export function setCheckMessages(en) { CHECKS.en = en || {}; }
// A marker for words the page translates later: the extractor (test_studio.py) finds them.
export const N_ = (s) => s;
export const getLang = () => lang;
export function setLang(code) { lang = DICTS[code] ? code : 'en'; document.documentElement.lang = lang; }
export function setUnits(u) { units = u === 'cm' ? 'cm' : 'm'; }
export const getUnits = () => units;
const locale = () => (lang === 'fr' ? 'fr-FR' : 'en-US');

// t('{n} open', { n: 3 }): {name} placeholders, values inserted as given.
export function t(en, params) {
  const s = (DICTS[lang] && DICTS[lang][en]) || en;
  return params ? s.replace(/\{(\w+)\}/g, (m, k) => (k in params ? String(params[k]) : m)) : s;
}
// tp(n, '{n} note', '{n} notes'): the form for n, in the language's plural rule.
const plural = {};
export function tp(n, one, other, params = {}) {
  const pr = (plural[lang] ||= new Intl.PluralRules(locale()));
  return t(pr.select(n) === 'one' ? one : other, { n: fmtN(n), ...params });
}

// Fill [data-i18n] text and [data-i18n-attr] attributes from their English originals.
export function applyI18n(root = document) {
  for (const el of root.querySelectorAll('[data-i18n]')) {
    if (el.dataset.en == null) el.dataset.en = el.textContent;
    el.textContent = t(el.dataset.en);
  }
  for (const el of root.querySelectorAll('[data-i18n-attr]')) {
    for (const a of el.dataset.i18nAttr.split(',')) {
      const k = `en${a.replace(/(^|-)(\w)/g, (_, __, c) => c.toUpperCase())}`;
      if (el.dataset[k] == null) el.dataset[k] = el.getAttribute(a) || '';
      el.setAttribute(a, t(el.dataset[k]));
    }
  }
}

// ── numbers ──────────────────────────────────────────────────────────────────

const nf = {};
const num = (opts = {}) => (nf[lang + JSON.stringify(opts)] ||= new Intl.NumberFormat(locale(), opts));
export const fmtN = (n) => (n == null ? '–' : num().format(n));
export const fmtD = (n, d) => num({ minimumFractionDigits: d, maximumFractionDigits: d }).format(n);
// 1500 → 1.5K (as checks.kfmt), with the language's decimal mark.
export const fmtK = (n) => (n >= 1e6 ? `${num({ maximumFractionDigits: 2 }).format(n / 1e6)}M`
  : n >= 1000 ? `${num({ maximumFractionDigits: 1 }).format(n / 1000)}K` : `${num().format(n)}`);
export const fmtB = (b) => (b == null ? '–' : b >= 1e6 ? `${fmtD(b / 1e6, 2)} ${t('MB')}` : `${fmtD(b / 1e3, 1)} ${t('kB')}`);
// A length in metres: m, cm or mm by size, or always cm when the user chose cm.
export function fmtLen(m) {
  if (m == null || Number.isNaN(m)) return '–';
  const a = Math.abs(m);
  if (units === 'cm' && a >= 0.001) return `${fmtD(m * 100, a >= 10 ? 0 : 1)} cm`;
  if (a >= 1) return `${fmtD(m, 2)} m`;
  if (a >= 0.01) return `${fmtD(m * 100, 1)} cm`;
  return `${fmtD(m * 1000, 1)} mm`;
}
// 0.12 → "12%" (fr: "12 %"); signed adds + or −.
export function fmtPct(frac, signed = false) {
  const v = num({ maximumFractionDigits: 0 }).format(Math.abs(frac) * 100);
  const s = frac < 0 ? '−' : signed && frac > 0 ? '+' : '';
  return lang === 'fr' ? `${s}${v}\u202f%` : `${s}${v}%`;
}

export function ago(iso) {
  if (!iso) return '';
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 45) return t('just now');
  if (s < 3600) return t('{n} min ago', { n: Math.round(s / 60) });
  if (s < 86400) return t('{n} h ago', { n: Math.round(s / 3600) });
  if (s < 86400 * 14) return t('{n} d ago', { n: Math.round(s / 86400) });
  return new Date(iso).toLocaleDateString(locale());
}
// A check finding ([[code, params], …], checks.py) in the language: the same codes,
// the same placeholders, numbers and lengths formatted here.
export function renderMsg(msg) {
  if (!Array.isArray(msg) || !msg.length) return null;
  return msg.map(([code, params]) => one(code, params || {})).join(' ');
}
function one(code, params) {
  let tm = (CHECKS[lang] && CHECKS[lang][code]) || CHECKS.en[code];
  if (tm == null) return code;
  if (Array.isArray(tm)) {
    const pr = (plural[lang] ||= new Intl.PluralRules(locale()));
    tm = pr.select(params.n ?? 2) === 'one' ? tm[0] : tm[1];
  }
  return tm.replace(/\{(\w+)(?::(\w+))?\}/g, (m, k, f) => (k in params ? fmtParam(params[k], f) : m));
}
function fmtParam(v, f) {
  if (Array.isArray(v) && v.length === 2 && typeof v[0] === 'string' && v[1] && typeof v[1] === 'object' && !Array.isArray(v[1])) return one(v[0], v[1]);
  switch (f) {
    case 'n': return fmtN(v);
    case 'k': return fmtK(v);
    case 'px': return `${fmtN(v)}${lang === 'fr' ? '\u202fpx' : 'px'}`;
    case 'd2': return fmtD(v, 2);
    case 'm2': return units === 'cm' ? fmtLen(v) : `${fmtD(v, 2)} m`;
    case 'm3': return units === 'cm' ? fmtLen(v) : `${fmtD(v, 3)} m`;
    case 'sm3': return `${v > 0 ? '+' : v < 0 ? '−' : '±'}${units === 'cm' ? fmtLen(Math.abs(v)) : `${fmtD(Math.abs(v), 3)} m`}`;
    case 'mm1': return `${fmtD(v * 1000, 1)} mm`;
    case 'm0': return `${fmtD(v, 0)} m`;
    case 'pct': return fmtPct(v);
    case 'spct': return fmtPct(v, true);
    case 'w': return t(v);
    case 'or': return v.map((x) => t(x)).join(t(' or '));
    default: return String(v);
  }
}

export const stamp = (iso) => new Date(iso).toLocaleString(locale(), { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
