// Sonde iniettate nella pagina analizzata: riconoscimento componenti, stato del focus,
// elementi interattivi "per uso" (gestore click) e snapshot di stato per i test da tastiera.
(() => {
  if (window.__a11y) return;

  const NATIVE = 'a[href],area[href],button,input:not([type=hidden]),select,textarea,summary,iframe,[contenteditable=""],[contenteditable=true]';
  const WIDGET_ROLES = new Set(['button', 'link', 'checkbox', 'radio', 'switch', 'tab', 'menuitem',
    'menuitemcheckbox', 'menuitemradio', 'option', 'combobox', 'slider', 'spinbutton', 'textbox', 'searchbox', 'treeitem']);

  const cssPath = (el) => {
    if (!(el instanceof Element)) return '';
    const parts = [];
    while (el && el.nodeType === 1 && el !== document.documentElement) {
      if (el.id && /^[A-Za-z][\w-]*$/.test(el.id) && document.querySelectorAll('#' + el.id).length === 1) {
        parts.unshift('#' + el.id);
        break;
      }
      let part = el.tagName.toLowerCase();
      const parent = el.parentElement;
      if (parent) {
        const same = [...parent.children].filter(c => c.tagName === el.tagName);
        if (same.length > 1) part += `:nth-of-type(${same.indexOf(el) + 1})`;
      }
      parts.unshift(part);
      el = parent;
    }
    return parts.join(' > ');
  };

  const visible = (el) => {
    if (!el || !el.getClientRects || !el.getClientRects().length) return false;
    const s = getComputedStyle(el);
    if (s.visibility === 'hidden' || s.display === 'none' || parseFloat(s.opacity) === 0) return false;
    const r = el.getBoundingClientRect();
    return r.width > 1 && r.height > 1;
  };

  const text = (s, n = 50) => (s || '').replace(/\s+/g, ' ').trim().slice(0, n);

  const accName = (el) => {
    const lb = el.getAttribute('aria-labelledby');
    if (lb) {
      const t = lb.split(/\s+/).map(id => document.getElementById(id)).filter(Boolean).map(e => e.textContent).join(' ');
      if (text(t)) return text(t);
    }
    return text(el.getAttribute('aria-label')) || text(el.getAttribute('alt')) || text(el.getAttribute('title'))
      || text(el.innerText) || text(el.getAttribute('placeholder')) || text(el.getAttribute('value'));
  };

  const isNative = (el) => el.matches(NATIVE);
  const hasWidgetRole = (el) => WIDGET_ROLES.has((el.getAttribute('role') || '').trim());

  // Interattivo "per uso": nativo, con ruolo di widget, con gestore click rilevato via CDP
  // (data-a11y-click) o, in mancanza, con cursore a manina non ereditato da un elemento interattivo.
  const interactive = (el) => {
    if (isNative(el) || hasWidgetRole(el) || el.hasAttribute('data-a11y-click')) return true;
    if (getComputedStyle(el).cursor !== 'pointer') return false;
    const p = el.parentElement;
    return !(p && getComputedStyle(p).cursor === 'pointer') && !el.closest(NATIVE);
  };

  const focusable = (el) => el.tabIndex >= 0 && !el.disabled;

  // ---- Riconoscimento componenti ------------------------------------------------
  const TYPE_RULES = [
    ['Modale / Dialog', 'dialog,[role=dialog],[role=alertdialog],[aria-modal=true]'],
    ['Breadcrumb / Paginazione', 'nav[aria-label*=breadcrumb i],[class*=breadcrumb i],nav[aria-label*=pagin i],[class*=pagination i]'],
    ['Navbar / Navigazione', 'nav,[role=navigation]'],
    ['Tab', '[role=tablist]'],
    ['Accordion', 'details,[class*=accordion i],[class*=expansion-panel i]'],
    ['Carosello / Slider', '[aria-roledescription=carousel i],[class*=carousel i],[class*=swiper i],[class*=slick i],[class*=owl-carousel i],[class*=slider i]:not(input),[class*=scroller i],[class*=gallery i]'],
    ['Menu / Dropdown', '[role=menu],[role=menubar],[role=listbox],[class*=dropdown i]'],
    ['Tabella', 'table,[role=grid],[role=table]'],
    ['Video / Audio', 'video,audio,iframe[src*=youtube],iframe[src*=vimeo]'],
    ['Form / Campo di input', 'form,[role=search],[role=form]'],
    ['Notifica / Messaggio di stato', '[role=alert],[role=status],[aria-live]:not([aria-live=off]),[class*=toast i],[class*=snackbar i]'],
    ['Tooltip / Contenuto su hover-focus', '[role=tooltip]'],
    ['Navbar / Navigazione', 'header,footer,[role=banner],[role=contentinfo]'],
  ];
  const CONSENT = /cookie|consent|gdpr|iubenda|cmp|fc-consent|onetrust|didomi/i;

  // Nomi normalizzati dei componenti trovati nel codice: un elemento appartiene al primo antenato
  // custom element (app-foo → foo) o, in mancanza, alla prima classe/id con lo stesso nome.
  const norm = (s) => (s || '').toLowerCase().replace(/[^a-z0-9]/g, '');
  let sources = new Set();
  const setSources = (names) => { sources = new Set(names.map(norm)); };
  const tagSrc = (e) => {
    const t = e.tagName.toLowerCase();
    if (!t.includes('-')) return '';
    return [norm(t), norm(t.slice(t.indexOf('-') + 1))].find(n => sources.has(n)) || '';
  };
  const tokSrc = (e) => [e.id, ...(typeof e.className === 'string' ? e.className.split(/\s+/) : [])]
    .map(norm).find(n => n && sources.has(n)) || '';
  const src = (el) => {
    if (!sources.size || !el) return '';
    const chain = [];
    for (let e = el; e && e.nodeType === 1; e = e.parentElement) chain.push(e);
    for (const e of chain) { const n = tagSrc(e); if (n) return n; }
    for (const e of chain) { const n = tokSrc(e); if (n) return n; }
    return '';
  };

  const roots = [];
  const rootIndex = new Map();
  const groups = new Map();
  const addRoot = (el, type, name) => {
    if (rootIndex.has(el)) return rootIndex.get(el);
    roots.push({ el, type, name: text(name, 60), location: cssPath(el) });
    rootIndex.set(el, roots.length - 1);
    return roots.length - 1;
  };

  const components = () => {
    roots.length = 0;
    rootIndex.clear();
    groups.clear();
    addRoot(document.documentElement, 'Struttura pagina / Intestazioni', 'Struttura della pagina');
    const used = new Set();
    for (const [type, sel] of TYPE_RULES) {
      for (const el of document.querySelectorAll(sel)) {
        if (used.has(el) || !visible(el) && type !== 'Modale / Dialog') continue;
        // solo il contenitore più esterno (es. .scroller ma non .scroller-item)
        if (el.parentElement && el.parentElement.closest(sel)) continue;
        // i contenitori header/footer contano solo se contengono link
        if (/^(HEADER|FOOTER)$/.test(el.tagName) || /banner|contentinfo/.test(el.getAttribute('role') || '')) {
          if (!el.querySelector('a[href]')) continue;
        }
        used.add(el);
        let t = type;
        const sig = (el.id || '') + ' ' + (typeof el.className === 'string' ? el.className : '');
        if (CONSENT.test(sig)) t = 'Modale / Dialog';
        const head = el.querySelector('h1,h2,h3,h4,legend,caption,summary');
        const label = el.getAttribute('aria-label') || (head && head.innerText) || el.id
          || (typeof el.className === 'string' ? el.className.split(/\s+/)[0] : '') || el.tagName.toLowerCase();
        addRoot(el, t, CONSENT.test(sig) ? 'Banner cookie/consenso' : label);
      }
    }
    return list();
  };

  const ORPHAN_TYPE = (el) => {
    const role = el.getAttribute('role') || '';
    if (el.matches('img,svg,[role=img],picture,canvas') || role === 'img') return 'Immagine / Icona';
    if (el.matches('a[href]') || role === 'link') return 'Link';
    if (el.matches('input,select,textarea') || /textbox|combobox|checkbox|radio|switch/.test(role)) return 'Form / Campo di input';
    if (interactive(el)) return 'Bottone';
    return 'Testo / Contenuto';
  };

  // Componente proprietario di un elemento: il riconosciuto più interno che lo contiene,
  // altrimenti un gruppo per tipologia nella sezione (landmark) più vicina.
  const ownIdx = (el) => {
    if (!el || el.nodeType !== 1) return 0;
    let best = 0;
    for (let i = 1; i < roots.length; i++) {
      if (!roots[i].group && roots[i].el.contains(el) && (best === 0 || roots[best].el.contains(roots[i].el))) best = i;
    }
    if (best) return best;
    const type = ORPHAN_TYPE(el);
    if (type === 'Testo / Contenuto' && el === document.documentElement) return 0;
    const box = el.closest('main,section,aside,article,[role=region],[role=main]') || document.body;
    const key = cssPath(box) + '|' + type;
    if (!groups.has(key)) {
      const h = box.querySelector('h1,h2,h3');
      const where = box === document.body ? 'pagina' : (box.getAttribute('aria-label') || (h && text(h.innerText, 40)) || box.tagName.toLowerCase());
      roots.push({ el: box, type, group: true, name: `${type.split(' /')[0]} in «${where}»`, location: cssPath(box) });
      groups.set(key, roots.length - 1);
    }
    return groups.get(key);
  };

  const own = (el) => {
    const { type, name, location } = roots[ownIdx(el)];
    return { type, name, location, src: src(el) };
  };

  const query = (target) => {
    try {
      return Array.isArray(target) ? document.querySelector(target[0]) : document.querySelector(target);
    } catch (e) {
      return null;
    }
  };

  // ---- Focus -----------------------------------------------------------------
  const focusInfo = () => {
    const el = document.activeElement;
    if (!el || el === document.body || el === document.documentElement) return { body: true };
    const r = el.getBoundingClientRect();
    const vis = visible(el);
    const inView = r.bottom > 0 && r.right > 0 && r.top < innerHeight && r.left < innerWidth;
    let obscured = false;
    if (vis && inView) {
      const cx = Math.min(Math.max(r.left + r.width / 2, 0), innerWidth - 1);
      const cy = Math.min(Math.max(r.top + r.height / 2, 0), innerHeight - 1);
      const top = document.elementFromPoint(cx, cy);
      obscured = !!top && top !== el && !el.contains(top) && !top.contains(el);
    }
    return {
      body: false, sel: cssPath(el), owner: own(el), tag: el.tagName.toLowerCase(), name: accName(el),
      visible: vis, inView, obscured: obscured ? cssPath(document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2)) : '',
      rect: { x: r.left, y: r.top, w: r.width, h: r.height }, frame: el.tagName === 'IFRAME',
    };
  };

  // Elementi interattivi visibili mai raggiunti dal Tab.
  const unreached = (visited) => {
    const seen = new Set(visited);
    const out = [];
    const all = document.querySelectorAll('body *');
    for (const el of all) {
      if (out.length >= 40) break;
      if (!visible(el) || !interactive(el) || el.disabled || el.closest('[inert]')) continue;
      if (el.matches('iframe')) continue;
      const sel = cssPath(el);
      if (seen.has(sel)) continue;
      // contenuto di un elemento già raggiunto (es. icona dentro un link)
      if ([...seen].some(s => { const v = query(s); return v && v.contains(el); })) continue;
      // un elemento che contiene un elemento raggiunto è solo un contenitore cliccabile
      if ([...seen].some(s => { const v = query(s); return v && el.contains(v); })) continue;
      out.push({ sel, owner: own(el), name: accName(el), tag: el.tagName.toLowerCase(),
        focusable: focusable(el), byListener: el.hasAttribute('data-a11y-click') });
    }
    return out;
  };

  // Candidati a cui CDP chiede i gestori di evento: elementi non nativi con cursore a manina.
  const clickCandidates = () => [...document.querySelectorAll('body *')]
    .filter(el => !isNative(el) && !hasWidgetRole(el) && visible(el) && getComputedStyle(el).cursor === 'pointer'
      && !(el.parentElement && getComputedStyle(el.parentElement).cursor === 'pointer'))
    .slice(0, 150);

  // ---- Toggle / disclosure ---------------------------------------------------------
  const TOGGLE_RE = /toggle|burger|hamburger|menu-btn|menu-button|navbar-toggler|dropdown-toggle|collaps/i;
  const toggles = () => [...document.querySelectorAll('body *')].filter(el => {
    if (!visible(el)) return false;
    if (el.matches('a[href]') && !/^(#|javascript:)/.test(el.getAttribute('href') || '')) return false;
    if (el.matches('[type=submit],input,select,textarea')) return false;
    const sig = (el.id || '') + ' ' + (typeof el.className === 'string' ? el.className : '');
    return el.hasAttribute('aria-expanded') || el.hasAttribute('aria-haspopup') || (interactive(el) && TOGGLE_RE.test(sig));
  }).slice(0, 15).map(el => ({ sel: cssPath(el), owner: own(el), name: accName(el), focusable: focusable(el),
    expanded: el.getAttribute('aria-expanded') }));

  const state = (sel) => {
    const el = query(sel);
    const vis = [...document.querySelectorAll('a[href],button,input,select,textarea,[role=menuitem],li')].filter(visible).length;
    return { vis, expanded: el ? el.getAttribute('aria-expanded') : null, url: location.href };
  };

  // ---- Caroselli -------------------------------------------------------------------
  const motion = () => roots.map((r, i) => {
    if (r.type !== 'Carosello / Slider') return null;
    const sig = [...r.el.querySelectorAll('*')].slice(0, 300)
      .map(e => (typeof e.className === 'string' ? e.className : '') + getComputedStyle(e).transform).join('|');
    const pause = [...r.el.querySelectorAll('button,[role=button],a')].some(b => /paus|stop|ferma|arresta/i.test(accName(b)));
    return { i, sig, pause };
  }).filter(Boolean);

  // ---- Contrasto misurato sui pixel (per i casi che axe non sa decidere) -----------
  const lum = (rgb) => {
    const [r, g, b] = rgb.map(c => (c /= 255) <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  };
  const ratio = (a, b) => {
    const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p);
    return (x + 0.05) / (y + 0.05);
  };

  const textInfo = (sel) => {
    const el = query(sel);
    if (!el || !visible(el)) return null;
    el.scrollIntoView({ block: 'center', behavior: 'instant' });
    const s = getComputedStyle(el);
    const c = s.color.match(/[\d.]+/g).map(Number);
    const px = parseFloat(s.fontSize);
    const bold = parseInt(s.fontWeight, 10) >= 700;
    const r = el.getBoundingClientRect();
    return { fg: c.slice(0, 3), large: px >= 24 || (px >= 18.66 && bold), owner: own(el),
      text: text(el.innerText, 40), rect: { x: r.left, y: r.top, w: r.width, h: r.height } };
  };

  const hideText = (sel, on) => {
    if (!document.getElementById('__a11y-hide')) {
      const st = document.createElement('style');
      st.id = '__a11y-hide';
      st.textContent = '.__a11y-hide,.__a11y-hide *{color:transparent!important;-webkit-text-fill-color:transparent!important;text-shadow:none!important;caret-color:transparent!important}';
      document.head.appendChild(st);
    }
    const el = query(sel);
    if (el) el.classList.toggle('__a11y-hide', on);
  };

  // Sfondo reale sotto il testo (screenshot col testo nascosto) confrontato col colore del testo.
  const bgContrast = async (b64, fg) => {
    const img = new Image();
    img.src = 'data:image/png;base64,' + b64;
    await img.decode();
    const cv = document.createElement('canvas');
    cv.width = img.width;
    cv.height = img.height;
    const ctx = cv.getContext('2d');
    ctx.drawImage(img, 0, 0);
    const d = ctx.getImageData(0, 0, cv.width, cv.height).data;
    const step = Math.max(1, Math.floor(d.length / 4 / 6000)) * 4;
    const rs = [];
    for (let i = 0; i < d.length; i += step) rs.push(ratio(fg, [d[i], d[i + 1], d[i + 2]]));
    rs.sort((a, b) => a - b);
    const at = (q) => Math.round(rs[Math.floor(q * (rs.length - 1))] * 100) / 100;
    return { min: at(0), p10: at(0.1), median: at(0.5) };
  };

  const list = () => roots.map(({ el, type, name, location }) => ({ type, name, location, src: src(el) }));

  // ---- Mappa per lo screenshot: riquadri in coordinate di pagina -------------------
  const box = (el) => {
    let r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) {  // custom element inline: unione dei figli
      const rs = [...el.children].map(c => c.getBoundingClientRect()).filter(c => c.width > 1 && c.height > 1);
      if (!rs.length) return null;
      const x = Math.min(...rs.map(c => c.left)), y = Math.min(...rs.map(c => c.top));
      r = { left: x, top: y, width: Math.max(...rs.map(c => c.right)) - x, height: Math.max(...rs.map(c => c.bottom)) - y };
    }
    return { x: Math.round(r.left + scrollX), y: Math.round(r.top + scrollY), w: Math.round(r.width), h: Math.round(r.height) };
  };

  // Componenti riconosciuti e, per ogni componente del codice, gli elementi più esterni che lo rendono.
  const boxes = () => {
    const out = { w: document.documentElement.scrollWidth, h: document.documentElement.scrollHeight, roots: [], sources: {} };
    for (const r of roots) {
      if (r.el === document.documentElement || r.el === document.body || !r.el.isConnected) continue;
      const rect = box(r.el);
      if (rect) out.roots.push({ type: r.type, name: r.name, location: r.location, rect });
    }
    if (!sources.size) return out;
    for (const el of document.querySelectorAll('body *')) {
      const n = tagSrc(el) || tokSrc(el);
      if (!n || getComputedStyle(el).display === 'none') continue;
      let outer = true;
      for (let p = el.parentElement; p && outer; p = p.parentElement) if ((tagSrc(p) || tokSrc(p)) === n) outer = false;
      const rect = outer && box(el);
      if (rect && (out.sources[n] = out.sources[n] || []).length < 20) out.sources[n].push({ rect, sel: cssPath(el) });
    }
    return out;
  };

  window.__a11y = { setSources, components, own, query, focusInfo, unreached, clickCandidates, toggles, state, motion,
    cssPath, visible, accName, list, textInfo, hideText, bgContrast, boxes };
})();
