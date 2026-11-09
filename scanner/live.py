# -*- coding: utf-8 -*-
"""Analisi dinamica di un sito (deployato o in localhost) con un browser reale.

Per ogni pagina: riconoscimento dei componenti, regole WCAG di axe-core (incluso il
contrasto), giro completo con il Tab (focus visibile, nascosto, coperto, trappole),
elementi cliccabili non raggiungibili da tastiera, toggle attivabili solo col mouse,
reflow a 320px e caroselli in movimento senza pausa.
"""
import base64
import json
import re
import time
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from scanner.store import match_route

HERE = Path(__file__).parent
AXE = (HERE / "vendor" / "axe.min.js").read_text(encoding="utf-8")
AXE_IT = json.loads((HERE / "vendor" / "axe-it.json").read_text(encoding="utf-8"))
PROBES = (HERE / "probes.js").read_text(encoding="utf-8")

AXE_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]
DESKTOP = {"width": 1280, "height": 900}
# Link da non seguire nel crawl: logout (chiuderebbe la sessione) e file non HTML.
SKIP_URL = re.compile(r"log-?out|sign-?out|esci|disconnett|\.(pdf|zip|jpe?g|png|gif|svg|webp|docx?|xlsx?|mp4|mp3)$", re.I)


def wcag_codes(tags):
    return [f"{m[1]}.{m[2]}.{m[3]}" for t in tags if (m := re.fullmatch(r"wcag(\d)(\d)(\d+)", t))]


class PageResult:
    """Componenti di una pagina con rilevazioni e verifiche superate.

    Chiave componente = (tipologia, posizione, nome, componente del codice a cui appartiene).
    """

    def __init__(self, url, title, route=None):
        self.url, self.title, self.route = url, title, route
        self.components, self.passes = {}, {}

    def touch(self, owner):
        key = (owner["type"], owner["location"], owner["name"], owner.get("src", ""))
        self.passes.setdefault(key, set())
        return self.components.setdefault(key, [])

    def add(self, owner, codes, note):
        bucket = self.touch(owner)
        for code in ([codes] if isinstance(codes, str) else codes):
            bucket.append({"code": code, "note": note})

    def passed(self, owner, codes):
        self.touch(owner)
        self.passes[(owner["type"], owner["location"], owner["name"], owner.get("src", ""))].update(codes)

    def as_dict(self):
        path = urlparse(self.url).path or "/"
        return {
            "name": self.route or ("Home" if path == "/" else path),
            "url": self.url,
            "route": self.route,
            "notes": f"Titolo: {self.title}",
            "components": [{"type": t, "location": loc, "name": n, "src": src, "findings": f,
                            "passed": sorted(self.passes[(t, loc, n, src)])}
                           for (t, loc, n, src), f in self.components.items()],
        }


def _inject(page):
    page.evaluate(AXE)
    page.evaluate(PROBES)
    page.evaluate("(n) => __a11y.setSources(n)", getattr(page, "a11y_sources", []))
    _mark_click_listeners(page)
    for comp in page.evaluate("__a11y.components()"):
        yield comp


def _mark_click_listeners(page):
    """Marca con data-a11y-click gli elementi non nativi che hanno un proprio gestore click (via CDP)."""
    cdp = page.context.new_cdp_session(page)
    try:
        arr = cdp.send("Runtime.evaluate", {"expression": "window.__a11y.clickCandidates()"})["result"]["objectId"]
        for prop in cdp.send("Runtime.getProperties", {"objectId": arr, "ownProperties": True})["result"]:
            if not prop["name"].isdigit():
                continue
            oid = prop["value"]["objectId"]
            listeners = cdp.send("DOMDebugger.getEventListeners", {"objectId": oid})["listeners"]
            if any(lst["type"] in ("click", "mousedown", "mouseup", "pointerdown", "pointerup") for lst in listeners):
                cdp.send("Runtime.callFunctionOn", {
                    "objectId": oid, "functionDeclaration": "function(){this.setAttribute('data-a11y-click','1')}"})
    finally:
        cdp.detach()


def _goto(page, url):
    page.goto(url, wait_until="load", timeout=45000)
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except PlaywrightError:
        pass  # analytics e annunci tengono la rete sempre attiva
    try:  # le SPA caricano i dati dopo il load: si aspetta che spariscano gli indicatori di caricamento
        page.wait_for_function("""() => ![...document.querySelectorAll('[aria-busy=true],[class*=spinner],[class*=loading]')]
            .some(e => e.getClientRects().length)""", timeout=8000)
    except PlaywrightError:
        pass
    page.wait_for_timeout(1000)


def _axe(page, res):
    violations = page.evaluate("""async ([locale, tags]) => {
        axe.configure({ locale });
        const r = await axe.run(document, { runOnly: { type: 'tag', values: tags },
                                            resultTypes: ['violations', 'incomplete', 'passes'], iframes: false });
        const pack = (v) => ({ id: v.id, help: v.help, tags: v.tags, impact: v.impact,
          nodes: v.nodes.slice(0, 60).map(n => ({ owner: __a11y.own(__a11y.query(n.target)),
            target: n.target.join(' '), summary: (n.failureSummary || '').split('\\n').slice(1, 3).join(' ').trim() })) });
        // verifiche superate: servono solo sui componenti collegati al codice
        const passes = r.passes.map(v => ({ tags: v.tags, owners: v.nodes.slice(0, 200)
          .map(n => __a11y.own(__a11y.query(n.target))).filter(o => o.src) })).filter(v => v.owners.length);
        return { violations: r.violations.map(pack), passes,
                 contrast: r.incomplete.filter(v => v.id === 'color-contrast').map(pack) };
    }""", [AXE_IT, AXE_TAGS])
    contrast = [n["target"] for v in violations["contrast"] for n in v["nodes"]]
    for v in violations["violations"]:
        codes = wcag_codes(v["tags"])
        for n in v["nodes"]:
            note = f"[axe:{v['id']}, {v['impact']}] {v['help']}. {n['summary']} — {n['target']}"
            res.add(n["owner"], codes, note.strip())
    for v in violations["passes"]:
        for owner in v["owners"]:
            res.passed(owner, wcag_codes(v["tags"]))
    return contrast


def _measured_contrast(page, res, targets):
    """Contrasto dei testi su immagini/gradienti/sovrapposizioni: sfondo letto dai pixel reali."""
    for sel in targets[:40]:
        try:
            info = page.evaluate("(s) => __a11y.textInfo(s)", sel)
            if not info or not info["text"]:
                continue
            page.wait_for_timeout(50)
            r = page.evaluate("(s) => __a11y.textInfo(s)", sel)["rect"]
            clip = {"x": max(r["x"], 0), "y": max(r["y"], 0), "width": min(r["w"], DESKTOP["width"] - max(r["x"], 0)),
                    "height": min(r["h"], page.viewport_size["height"] - max(r["y"], 0))}
            if clip["width"] < 2 or clip["height"] < 2:
                continue
            page.evaluate("(s) => __a11y.hideText(s, true)", sel)
            png = page.screenshot(clip=clip, animations="disabled")
            page.evaluate("(s) => __a11y.hideText(s, false)", sel)
            m = page.evaluate("([b, fg]) => __a11y.bgContrast(b, fg)", [base64.b64encode(png).decode(), info["fg"]])
        except PlaywrightError:
            continue
        need = 3.0 if info["large"] else 4.5
        what = f"«{info['text']}» ({sel})"
        if m["median"] < need:
            res.add(info["owner"], "1.4.3", f"Contrasto misurato sullo sfondo reale {m['median']}:1, "
                                            f"richiesto {need}:1 (minimo {m['min']}:1): {what}.")
        elif m["p10"] < need:
            res.add(info["owner"], "1.4.3", f"Contrasto insufficiente su parte dello sfondo: scende a {m['p10']}:1 "
                                            f"sul 10% dell'area (richiesto {need}:1, mediana {m['median']}:1): {what}.")


def _screenshot_focus(page, info):
    r = info["rect"]
    pad = 6
    x, y = max(r["x"] - pad, 0), max(r["y"] - pad, 0)
    w = min(r["x"] + r["w"] + pad, DESKTOP["width"]) - x
    h = min(r["y"] + r["h"] + pad, page.viewport_size["height"]) - y
    if w < 2 or h < 2:
        return None
    clip = {"x": x, "y": y, "width": w, "height": h}
    focused = page.screenshot(clip=clip, animations="disabled")
    page.evaluate("document.activeElement && document.activeElement.blur()")
    blurred = page.screenshot(clip=clip, animations="disabled")
    page.evaluate("(s) => { const e = __a11y.query(s); e && e.focus({ preventScroll: true }); }", info["sel"])
    return focused != blurred


def _settled_focus(page):
    """Stato del focus a scroll concluso (molti siti usano scroll-behavior: smooth)."""
    f = page.evaluate("__a11y.focusInfo()")
    for _ in range(12):
        page.wait_for_timeout(60)
        g = page.evaluate("__a11y.focusInfo()")
        if g.get("rect") == f.get("rect"):
            return g
        f = g
    return f


def _keyboard_walk(page, res, max_stops=250):
    """Simula la navigazione con Tab; restituisce (selettori raggiunti, giro completato)."""
    page.mouse.move(0, 0)
    page.evaluate("() => { document.activeElement && document.activeElement.blur(); window.scrollTo(0, 0); }")
    start_url = page.url
    visited, seen = [], set()
    prev, same = None, 0
    for _ in range(max_stops):
        page.keyboard.press("Tab")
        f = _settled_focus(page)
        if page.url != start_url:
            res.add(page.evaluate("__a11y.own(document.documentElement)"), "3.2.1",
                    f"Spostare il focus con Tab ha cambiato pagina ({start_url} → {page.url}).")
            _goto(page, start_url)
            list(_inject(page))
            return visited, False
        if f["body"]:
            if visited:
                return visited, True
            continue
        if f["sel"] == prev:
            same += 1
            # dentro un iframe il focus resta sull'iframe mentre si muove al suo interno
            if same >= (40 if f["frame"] else 3):
                res.add(f["owner"], "2.1.2", f"Trappola da tastiera: Tab non sposta più il focus da «{f['name']}» ({f['sel']}).")
                return visited, False
            continue
        same, prev = 0, f["sel"]
        if f["sel"] in seen:
            return visited, True
        seen.add(f["sel"])
        visited.append(f["sel"])
        label = f"«{f['name'] or f['tag']}» ({f['sel']})"
        if f["frame"]:
            continue
        if not f["visible"]:
            res.add(f["owner"], "2.4.7", f"Il focus da tastiera finisce su un elemento non visibile: {label}.")
        elif f["obscured"]:
            res.add(f["owner"], "2.4.11", f"Elemento con focus coperto da {f['obscured']}: {label}.")
        elif f["inView"]:
            shown = _screenshot_focus(page, f)
            if shown is False:
                res.add(f["owner"], "2.4.7", f"Nessun indicatore di focus visibile: {label} appare identico con e senza focus.")
            elif shown and f["owner"].get("src"):
                res.passed(f["owner"], ["2.4.7"])
    return visited, False


def _unreached(page, res, visited):
    for u in page.evaluate("(v) => __a11y.unreached(v)", visited):
        if u["focusable"]:
            continue
        how = "gestore click rilevato" if u["byListener"] else "cursore a manina, da confermare"
        res.add(u["owner"], "2.1.1",
                f"Elemento cliccabile «{u['name'] or u['tag']}» non raggiungibile con Tab ({how}): {u['sel']}.")
    for f in page.evaluate("""() => [...document.querySelectorAll('[data-a11y-click]')]
        .filter(e => !e.getAttribute('role') && __a11y.visible(e))
        .map(e => ({ owner: __a11y.own(e), sel: __a11y.cssPath(e), name: __a11y.accName(e), tag: e.tagName.toLowerCase() }))"""):
        res.add(f["owner"], "4.1.2",
                f"<{f['tag']}> «{f['name']}» ha un gestore click ma nessun ruolo: non è annunciato come controllo ({f['sel']}).")


def _changed(a, b):
    return a["vis"] != b["vis"] or a["expanded"] != b["expanded"]


def _toggles(page, res, where):
    start_url = page.url
    for t in page.evaluate("__a11y.toggles()"):
        sel, label = t["sel"], f"«{t['name'] or 'senza nome'}» ({t['sel']})"
        try:
            s0 = page.evaluate("(s) => __a11y.state(s)", sel)
            by_kb = False
            if t["focusable"]:
                for key in ("Enter", " "):
                    page.evaluate("(s) => __a11y.query(s).focus()", sel)
                    page.keyboard.press(key)
                    page.wait_for_timeout(400)
                    s1 = page.evaluate("(s) => __a11y.state(s)", sel)
                    if s1["url"] != start_url:
                        raise _Navigated
                    if _changed(s0, s1):
                        by_kb = True
                        break
            if by_kb:
                after = s1
                page.keyboard.press(key)
            else:
                page.click(sel, timeout=2000)
                page.wait_for_timeout(400)
                after = page.evaluate("(s) => __a11y.state(s)", sel)
                if after["url"] != start_url:
                    raise _Navigated
                if not _changed(s0, after):
                    continue
                res.add(t["owner"], "2.1.1",
                        f"Il controllo {label} si attiva con il click ma non con Invio/Spazio ({where})."
                        if t["focusable"] else
                        f"Il controllo {label} si attiva solo con il mouse: non è focalizzabile ({where}).")
                page.click(sel, timeout=2000)
            page.wait_for_timeout(300)
            if after["vis"] != s0["vis"] and after["expanded"] == s0["expanded"]:
                res.add(t["owner"], "4.1.2",
                        f"Il controllo {label} apre/chiude contenuti ma non espone aria-expanded ({where})."
                        if s0["expanded"] is None else
                        f"Il controllo {label} apre/chiude contenuti ma aria-expanded resta «{s0['expanded']}» ({where}).")
        except _Navigated:
            _goto(page, start_url)
            list(_inject(page))
        except PlaywrightError:
            continue


class _Navigated(Exception):
    pass


def _reflow(page, res):
    page.set_viewport_size({"width": 320, "height": 800})
    page.wait_for_timeout(800)
    sw, cw = page.evaluate("[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
    if sw > cw + 2:
        res.add(page.evaluate("__a11y.own(document.documentElement)"), "1.4.10",
                f"A 320px di larghezza la pagina scorre in orizzontale (contenuto largo {sw}px).")
    _toggles(page, res, "vista mobile 320px")
    page.set_viewport_size(DESKTOP)
    page.wait_for_timeout(300)


def analyze_page(page, log=print, route=None):
    """Analizza la pagina già caricata nel browser."""
    res = PageResult(page.url, page.title(), route)
    for comp in _inject(page):
        res.touch(comp)
    t0, m0 = time.time(), page.evaluate("__a11y.motion()")
    log(f"  axe-core su {page.url}")
    contrast = _axe(page, res)
    if m0:
        page.wait_for_timeout(max(0, int(6000 - (time.time() - t0) * 1000)))
        before = {m["i"]: m for m in m0}
        for m in page.evaluate("__a11y.motion()"):
            b = before.get(m["i"])
            if b and b["sig"] != m["sig"] and not m["pause"]:
                comp = page.evaluate("(i) => __a11y.list()[i]", m["i"])
                res.add(comp, "2.2.2", "Il carosello si muove da solo e non ha un controllo per metterlo in pausa.")
    if contrast:
        log(f"  contrasto misurato su {len(contrast)} testi con sfondo complesso")
        _measured_contrast(page, res, contrast)
        page.evaluate("window.scrollTo(0, 0)")
    log("  navigazione da tastiera")
    visited, complete = _keyboard_walk(page, res)
    if complete:
        _unreached(page, res, visited)
    else:
        log("  giro con Tab non completato: controllo elementi non raggiungibili saltato")
    log("  toggle e reflow")
    _toggles(page, res, "vista desktop")
    _reflow(page, res)
    for comp in page.evaluate("__a11y.list()"):
        res.touch(comp)
    result = res.as_dict()
    try:
        result["shot"] = _shot(page, result)
    except PlaywrightError as e:  # senza screenshot la pagina analizzata resta valida
        log(f"  screenshot non riuscito: {e.message.splitlines()[0]}")
    return result, page.evaluate("[...document.querySelectorAll('a[href]')].map(a => a.href)")


def _shot(page, result, max_h=12000):
    """Screenshot a pagina intera con i riquadri dei componenti (a fine analisi: lazy load già caricati)."""
    page.keyboard.press("Escape")
    page.evaluate("""() => { document.activeElement && document.activeElement.blur();
                             window.scrollTo({ top: 0, left: 0, behavior: 'instant' }); }""")
    page.mouse.move(0, 0)
    page.wait_for_timeout(300)
    shot = page.evaluate("__a11y.boxes()")
    shot["w"], shot["h"] = DESKTOP["width"], min(shot["h"], max_h)
    shot["image"] = page.screenshot(full_page=True, type="jpeg", quality=70, animations="disabled",
                                    clip={"x": 0, "y": 0, "width": shot["w"], "height": shot["h"]})
    rects = {(b["type"], b["location"], b["name"]): b["rect"] for b in shot.pop("roots")}
    for c in result["components"]:
        c["rect"] = rects.get((c["type"], c["location"], c["name"]))
    return shot


SHAPE = """() => { const m = document.querySelector('main,[role=main]') || document.body;
  return [...new Set([...m.querySelectorAll('*')].map(e => e.tagName + '.' +
    (typeof e.className === 'string' ? e.className.trim().split(/\\s+/).sort().join('.') : '')))].sort().join('|'); }"""


def _same_site(url, origin):
    u = urlparse(url)
    return u.scheme in ("http", "https") and u.netloc == origin and not SKIP_URL.search(u.path)


def scan_site(start_url, max_pages=10, storage_state=None, urls=None, headless=True, log=print,
              routes=None, sources=None):
    """Analizza start_url e le pagine dello stesso sito raggiunte dai link (o la lista urls).

    Con le rotte del codice parte anche da quelle senza parametri, analizza una sola URL per
    rotta (/news/1 e /news/2 sono la stessa pagina) e collega gli elementi ai componenti sources.
    Senza codice, salta le pagine con lo stesso percorso padre e la stessa struttura di una già vista.
    """
    origin = urlparse(start_url).netloc
    queue = list(urls or [start_url])
    if routes and not urls:
        queue += [urljoin(start_url, r) for r in routes if ":" not in r and "*" not in r]
    done, done_routes, shapes, pages = set(), set(), {}, []

    def new(u):
        return u not in done and (match_route(urlparse(u).path, routes) or u) not in done_routes
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(viewport=DESKTOP, bypass_csp=True, storage_state=storage_state,
                                      locale="it-IT")
        page = context.new_page()
        page.a11y_sources = sources or []
        while queue and len(pages) < max_pages:
            url = urldefrag(queue.pop(0))[0]
            if not new(url):
                continue
            done.add(url)
            log(f"Pagina {len(pages) + 1}/{max_pages}: {url}")
            try:
                _goto(page, url)
                final = urldefrag(page.url)[0]
                path = urlparse(final).path or "/"
                route = match_route(path, routes)
                key = route or urlparse(final)._replace(query="").geturl()
                if urlparse(final).netloc != origin:
                    log(f"  reindirizzata fuori dal sito ({urlparse(final).netloc}, es. login): saltata")
                    continue
                if final != url and (final in done or key in done_routes):
                    log(f"  reindirizzata a {final}, già analizzata")
                    continue
                parent = path.rstrip("/").rsplit("/", 1)[0]
                if not route and parent:
                    # ponytail: firma = insieme di tag+classi del contenuto principale; due pagine sorelle
                    # con lo stesso template (es. /regione/piemonte e /regione/lombardia) sono una sola pagina
                    shape = (parent, page.evaluate(SHAPE))
                    if shape in shapes:
                        log(f"  stessa struttura di {shapes[shape]}: saltata")
                        done.add(final)
                        continue
                    shapes[shape] = path
                result, links = analyze_page(page, log, route)
            except PlaywrightError as e:
                log(f"  errore: {e.message.splitlines()[0]}")
                continue
            done.add(final)
            done_routes.add(key)
            pages.append(result)
            if not urls:
                queue += [u for u in (urldefrag(x)[0] for x in links) if _same_site(u, origin) and new(u)]
        browser.close()
    return pages


def interactive_login(url, out_path, log=print):
    """Apre un browser visibile: l'utente fa il login e chiude la finestra; la sessione viene salvata."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport=DESKTOP)
        page = context.new_page()
        page.goto(url)
        log("Effettua il login nel browser aperto, poi chiudi la finestra.")
        state = context.storage_state()
        while context.pages:
            try:
                state = context.storage_state()
                context.pages[0].wait_for_timeout(1000)
            except PlaywrightError:
                break
        browser.close()
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(state), encoding="utf-8")
    log(f"Sessione salvata in {out_path}")
    return out_path
