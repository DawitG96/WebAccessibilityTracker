# -*- coding: utf-8 -*-
"""Analisi statica del sorgente di un progetto frontend (Angular, React/Next, Vue/Nuxt, Svelte, HTML).

Ricava le rotte, segue l'albero dei componenti caricati da ciascuna rotta e applica regole
di accessibilità ai template. È un'analisi euristica: ciò che dipende dal rendering
(contrasto, focus, ordine reale) va verificato con l'analisi live.
"""
import json
import os
import re
from pathlib import Path

IGNORE_DIRS = {"node_modules", ".git", "dist", "build", ".next", ".nuxt", ".output", ".angular", "coverage",
               ".svelte-kit", "out", "vendor", "e2e", "__tests__", ".storybook"}
SRC_EXT = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".vue", ".svelte", ".html")
STYLE_EXT = (".css", ".scss", ".sass", ".less")
RESOLVE_EXT = ("", ".ts", ".tsx", ".js", ".jsx", ".vue", ".svelte", "/index.ts", "/index.tsx", "/index.js", "/index.jsx")

# Tag con attributi, comprese le espressioni JSX tra graffe (fino a tre livelli di annidamento).
_BRACES = r"\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\}"
_VALUE = rf"(?:\"[^\"]*\"|'[^']*'|{_BRACES}|[^\s>\"']+)"
TAG = re.compile(rf"<([A-Za-z][\w.:-]*)((?:\s+[^\s=>/\"'{{}}]+(?:\s*=\s*{_VALUE})?|\s*{_BRACES})*)\s*/?>", re.S)
ATTR = re.compile(rf"([^\s=>/\"'{{}}]+)(?:\s*=\s*({_VALUE}))?")
IMPORT = re.compile(r"import\s+(?:type\s+)?(?:(\w+)\s*,?\s*)?(?:\{([^}]*)\})?\s*(?:\*\s+as\s+\w+\s*)?from\s*['\"]([^'\"]+)['\"]")

NON_INTERACTIVE = {"div", "span", "li", "p", "img", "i", "svg", "td", "tr", "section", "article", "h1", "h2", "h3",
                   "h4", "h5", "h6", "ul", "label", "strong", "em", "small", "figure", "header", "footer"}
TYPE_HINTS = [
    ("Modale / Dialog", r"modal|dialog|popup|lightbox|cookie|consent|overlay"),
    ("Breadcrumb / Paginazione", r"breadcrumb|paginat|pager"),
    ("Navbar / Navigazione", r"nav|header|footer|sidebar|sidenav|topbar|menu-bar|toolbar"),
    ("Carosello / Slider", r"carousel|slider|swiper|slick|scroller|gallery|slideshow"),
    ("Tab", r"tabs?\b|tabset|tab-?group"),
    ("Accordion", r"accordion|collaps|expansion|faq"),
    ("Menu / Dropdown", r"dropdown|menu|select|combobox|autocomplete"),
    ("Tabella", r"table|grid|datatable|list-view"),
    ("Form / Campo di input", r"form|input|field|login|signin|signup|register|search|newsletter|contact"),
    ("Notifica / Messaggio di stato", r"toast|alert|snackbar|notif|banner|message"),
    ("Tooltip / Contenuto su hover-focus", r"tooltip|popover"),
    ("Video / Audio", r"video|audio|player|media"),
    ("Immagine / Icona", r"image|img|icon|avatar|logo|picture"),
    ("Bottone", r"button|btn"),
    ("Link", r"\blink"),
]


# ---------------------------------------------------------------- file e moduli
def _walk(root, exts):
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in IGNORE_DIRS and not x.startswith(".")]
        for f in files:
            if f.endswith(exts) and not re.search(r"\.(spec|test|stories)\.", f):
                yield Path(d) / f


def _read(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def detect_framework(root):
    pkg = Path(root) / "package.json"
    deps = {}
    if pkg.exists():
        try:
            data = json.loads(_read(pkg))
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        except ValueError:
            pass
    for name, fw in (("@angular/core", "angular"), ("next", "next"), ("nuxt", "nuxt"), ("@sveltejs/kit", "sveltekit"),
                     ("svelte", "svelte"), ("vue", "vue"), ("react", "react")):
        if name in deps:
            return fw
    return "html"


class Project:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.files = list(_walk(self.root, SRC_EXT))
        self.text = {f: _read(f) for f in self.files}
        src = self.root / "src"
        self.alias_base = src if src.is_dir() else self.root

    def rel(self, path):
        return Path(path).relative_to(self.root).as_posix()

    def resolve(self, from_file, spec):
        if spec.startswith("."):
            base = (Path(from_file).parent / spec)
        elif spec[:2] in ("@/", "~/") or spec.startswith("src/"):
            base = self.alias_base / spec.split("/", 1)[1] if not spec.startswith("src/") else self.root / spec
        else:
            return None  # pacchetto esterno
        for ext in RESOLVE_EXT:
            p = Path(os.path.normpath(str(base) + ext))
            if p in self.text:
                return p
        return None

    def imports(self, path):
        """Nome importato → file del progetto."""
        out = {}
        for default, named, spec in IMPORT.findall(self.text.get(path, "")):
            target = self.resolve(path, spec)
            if not target:
                continue
            if default:
                out[default] = target
            for n in filter(None, (x.strip() for x in named.split(","))):
                out[n.split(" as ")[-1].strip()] = target
        return out


# ---------------------------------------------------------------- markup per framework
def markup_of(proj, path):
    """(markup, riga iniziale, file del template) di un componente."""
    text = proj.text.get(path, "")
    sp = str(path)
    if sp.endswith(".vue"):
        m = re.search(r"<template[^>]*>(.*)</template>", text, re.S)
        return (m.group(1), text[:m.start(1)].count("\n") + 1, path) if m else ("", 1, path)
    if sp.endswith(".ts") and "@Component" in text:
        m = re.search(r"templateUrl\s*:\s*['\"]([^'\"]+)['\"]", text)
        if m:
            tpl = Path(os.path.normpath(Path(path).parent / m.group(1)))
            return proj.text.get(tpl) or _read(tpl), 1, tpl
        m = re.search(r"template\s*:\s*`(.*?)`", text, re.S)
        return (m.group(1), text[:m.start(1)].count("\n") + 1, path) if m else ("", 1, path)
    if sp.endswith((".ts", ".js", ".mjs")):
        return "", 1, path
    return text, 1, path


def styles_of(proj, path):
    text = proj.text.get(path, "")
    out = []
    sp = str(path)
    if sp.endswith((".vue", ".svelte", ".html")):
        out += re.findall(r"<style[^>]*>(.*?)</style>", text, re.S)
    if sp.endswith(".ts"):
        for spec in re.findall(r"styleUrls?\s*:\s*\[?\s*((?:['\"][^'\"]+['\"]\s*,?\s*)+)", text):
            for s in re.findall(r"['\"]([^'\"]+)['\"]", spec):
                out.append(_read(Path(path).parent / s))
        out += re.findall(r"styles\s*:\s*\[?\s*`(.*?)`", text, re.S)
    return "\n".join(out)


# ---------------------------------------------------------------- rotte e albero componenti
def _bracket_depth(text, pos):
    return text.count("[", 0, pos) - text.count("]", 0, pos) + text.count("{", 0, pos) - text.count("}", 0, pos)


def _object_routes(proj, path, resolve_comp):
    """Rotte dichiarate come oggetti { path: '...', component|element|loadComponent: ... } con annidamento children."""
    text = proj.text[path]
    matches = list(re.finditer(r"\bpath\s*:\s*['\"`]([^'\"`]*)['\"`]", text))
    out, stack = [], []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        window = text[m.end():end]
        depth = _bracket_depth(text, m.start())
        while stack and stack[-1][0] >= depth:
            stack.pop()
        full = "/".join(x for x in [stack[-1][1] if stack else ""] + [m.group(1)] if x)
        stack.append((depth, full))
        comp = resolve_comp(path, window)
        if comp:
            out.append(("/" + full.strip("/"), comp))
    return out


def _comp_from_window(proj, classes):
    def resolve(path, window):
        imports = proj.imports(path)
        m = re.search(r"(?:loadComponent|component)\s*:\s*\(\s*\)\s*=>\s*import\(\s*['\"]([^'\"]+)['\"]\s*\)"
                      r"(?:\s*\.then\(\s*\(?\s*\w+\s*\)?\s*=>\s*\w+\.(\w+)\s*\))?", window)
        if m:
            if m.group(2) and m.group(2) in classes:
                return classes[m.group(2)]
            return proj.resolve(path, m.group(1))
        m = re.search(r"(?:component|Component)\s*:\s*(\w+)|element\s*:\s*<\s*(\w+)", window)
        if m:
            name = m.group(1) or m.group(2)
            return classes.get(name) or imports.get(name)
        m = re.search(r"lazy\s*\(\s*\(\s*\)\s*=>\s*import\(\s*['\"]([^'\"]+)['\"]", window)
        return proj.resolve(path, m.group(1)) if m else None
    return resolve


def _angular(proj):
    classes, selectors = {}, {}
    for f, t in proj.text.items():
        if str(f).endswith(".ts") and "@Component" in t:
            sel = re.search(r"selector\s*:\s*['\"]([\w-]+)['\"]", t)
            for cls in re.findall(r"export\s+class\s+(\w+)", t):
                classes[cls] = f
            if sel:
                selectors[sel.group(1)] = f
    routes = []
    for f, t in proj.text.items():
        if str(f).endswith(".ts") and re.search(r"Routes\b|RouterModule|provideRouter", t):
            routes += _object_routes(proj, f, _comp_from_window(proj, classes))

    def children(path):
        markup = markup_of(proj, path)[0]
        return [selectors[s] for s in dict.fromkeys(re.findall(r"<([a-z][\w-]*-[\w-]*)", markup)) if s in selectors]
    root = selectors.get("app-root")
    return routes, children, [root] if root else []


def _jsx_children(proj):
    def children(path):
        imports = proj.imports(path)
        return [imports[n] for n in dict.fromkeys(re.findall(r"<([A-Z]\w*)", proj.text.get(path, ""))) if n in imports]
    return children


def _react(proj):
    routes = []
    for f, t in proj.text.items():
        if not str(f).endswith((".tsx", ".jsx", ".js", ".ts")) or "react-router" not in t and "Route" not in t:
            continue
        imports = proj.imports(f)
        for m in re.finditer(r"<Route\b", t):
            tag = TAG.match(t, m.start())
            if not tag:
                continue
            attrs = dict(_attrs(tag.group(2)))
            path = _plain(attrs.get("path", ""))
            comp = re.search(r"<\s*(\w+)", attrs.get("element", "")) or re.search(r"(\w+)", attrs.get("component", ""))
            if comp and comp.group(1) in imports:
                routes.append(("/" + path.strip("/"), imports[comp.group(1)]))
        if "createBrowserRouter" in t or "createHashRouter" in t or "useRoutes" in t:
            routes += _object_routes(proj, f, _comp_from_window(proj, {}))
    app = [f for f in proj.text if re.search(r"(^|/)src/(App|main|index)\.(t|j)sx$", proj.rel(f))]
    return routes, _jsx_children(proj), app[:1]


def _file_routes(proj, dirs, page_re, layout_re):
    routes, layouts = [], []
    for f in proj.text:
        rel = proj.rel(f)
        for d in dirs:
            if not rel.startswith(d + "/"):
                continue
            sub = rel[len(d) + 1:]
            if re.search(layout_re, sub):
                layouts.append(f)
            elif re.search(page_re, sub) and not sub.startswith("api/"):
                path = re.sub(page_re, "", sub)
                path = re.sub(r"\([^)]*\)/?", "", path)  # gruppi di rotte (Next app router)
                routes.append(("/" + path.strip("/"), f))
    return routes, layouts


def _next(proj):
    r1, l1 = _file_routes(proj, ["pages", "src/pages"], r"(/?index)?\.(t|j)sx?$", r"^_(app|document)\.")
    r2, l2 = _file_routes(proj, ["app", "src/app"], r"/?page\.(t|j)sx?$", r"(^|/)layout\.(t|j)sx?$")
    return r1 + r2, _jsx_children(proj), (l1 + l2)[:2]


def _vue_children(proj):
    def children(path):
        out = [v for v in proj.imports(path).values() if str(v).endswith((".vue", ".svelte"))]
        markup = markup_of(proj, path)[0]
        by_stem = proj.__dict__.setdefault("_vue_stems", {Path(f).stem: f for f in proj.text if str(f).endswith(".vue")})
        for tag in re.findall(r"<([A-Z]\w*|[a-z]+-[\w-]+)", markup):
            pascal = "".join(p.capitalize() for p in tag.split("-")) if "-" in tag else tag
            if pascal in by_stem:
                out.append(by_stem[pascal])
        return list(dict.fromkeys(out))
    return children


def _vue(proj):
    routes = []
    for f, t in proj.text.items():
        if str(f).endswith((".ts", ".js")) and ("createRouter" in t or "VueRouter" in t or "routes" in t):
            routes += _object_routes(proj, f, _comp_from_window(proj, {}))
    app = [f for f in proj.text if re.search(r"(^|/)src/App\.vue$", proj.rel(f))]
    return routes, _vue_children(proj), app


def _nuxt(proj):
    routes, _ = _file_routes(proj, ["pages", "app/pages"], r"(/?index)?\.vue$", r"^$")
    layouts = [f for f in proj.text if re.search(r"(^|/)(app|layouts/default)\.vue$", proj.rel(f))]
    return routes, _vue_children(proj), layouts[:2]


def _sveltekit(proj):
    routes, layouts = _file_routes(proj, ["src/routes"], r"/?\+page\.svelte$", r"(^|/)\+layout\.svelte$")
    return routes, _vue_children(proj), layouts[:1]


def _html(proj):
    pages = [f for f in proj.text if str(f).endswith(".html")]
    return [("/" + proj.rel(f), f) for f in pages], (lambda p: []), []


FRAMEWORKS = {"angular": _angular, "react": _react, "next": _next, "vue": _vue, "nuxt": _nuxt,
              "svelte": _vue, "sveltekit": _sveltekit, "html": _html}


def tree(start, children, stop=(), limit=200):
    seen, queue = [], [start]
    while queue and len(seen) < limit:
        f = queue.pop(0)
        if f in seen or f in stop:
            continue
        seen.append(f)
        queue += children(f)
    return seen


# ---------------------------------------------------------------- regole
def _attrs(raw):
    return [(n, v or "") for n, v in ATTR.findall(raw or "")]


def _plain(v):
    return v.strip().strip("{}").strip().strip("\"'`")


def _norm(name):
    """(click), @click, v-on:click, on:click, onClick → click; [attr.aria-label], :alt → aria-label, alt."""
    n = name.lower()
    n = re.sub(r"^(\[attr\.|\[|\(|v-on:|v-bind:|@|:|on:)", "", n).rstrip(")]")
    return n


def _has(attrs, *names):
    keys = {_norm(n) for n, _ in attrs}
    return any(x in keys for x in names)


def _value(attrs, name):
    for n, v in attrs:
        if _norm(n) == name:
            return _plain(v)
    return None


def _events(attrs, prefix):
    out = set()
    for n, _ in attrs:
        low = n.lower()
        if low.startswith("on") and not low.startswith("on:") and len(low) > 2:
            out.add(low[2:])
        elif low.startswith(("(", "@", "v-on:", "on:")):
            out.add(_norm(n).split(".")[0])
    return {e for e in out if e.startswith(prefix)}


def _inner(markup, end, tag):
    close = markup.find(f"</{tag}", end)
    return markup[end:close] if close != -1 else ""


def _has_text(inner):
    if re.search(r"\{\{|\{[^}]*\}|<(img|svg)\b[^>]*(alt|aria-label|title)=|<title>|aria-label", inner):
        return True
    return bool(re.sub(r"<[^>]+>|&nbsp;|\s", "", inner))


def check_markup(markup, start_line=1, full_text=None):
    """Regole sui template: restituisce [(riga, codice WCAG, nota)]."""
    out = []
    labels_for = set(re.findall(r"(?:\bfor|htmlFor|\[for\]|\[attr\.for\])\s*=\s*[\"'{]+([\w-]+)", markup))
    for m in TAG.finditer(markup):
        tag, attrs = m.group(1), _attrs(m.group(2))
        low = tag.lower()
        line = start_line + markup.count("\n", 0, m.start())
        snippet = re.sub(r"\s+", " ", m.group(0))[:90]
        clicks = _events(attrs, "click")
        keys = _events(attrs, "key")
        role = _value(attrs, "role")
        tabindex = _value(attrs, "tabindex")
        named = _has(attrs, "aria-label", "aria-labelledby", "title")

        if low == "img" or tag == "Image":
            if not _has(attrs, "alt") and role not in ("presentation", "none") and _value(attrs, "aria-hidden") != "true":
                out.append((line, "1.1.1", f"Immagine senza attributo alt: {snippet}"))
        if low in NON_INTERACTIVE and clicks:
            problems = []
            if not role:
                out.append((line, "4.1.2", f"<{low}> con gestore click senza ruolo (usare <button>): {snippet}"))
            if tabindex is None:
                problems.append("non è focalizzabile (manca tabindex)")
            if not keys:
                problems.append("non risponde a Invio/Spazio (nessun gestore tastiera)")
            if problems:
                out.append((line, "2.1.1", f"<{low}> cliccabile che " + " e ".join(problems) + f": {snippet}"))
        if low == "a":
            href = _value(attrs, "href")
            router = _has(attrs, "routerlink", "to", "nuxt-link")
            if href is None and not router and clicks:
                out.append((line, "2.1.1", f"<a> senza href usato come bottone: non è raggiungibile con Tab: {snippet}"))
            elif href in ("#", "") or (href or "").startswith("javascript:"):
                if clicks:
                    out.append((line, "4.1.2", f"<a href=\"{href}\"> usato come bottone (usare <button>): {snippet}"))
            if (href is not None or router) and not named and not _has_text(_inner(markup, m.end(), tag)):
                out.append((line, "2.4.4", f"Link senza testo né aria-label: {snippet}"))
        if low == "button" and not named and not _has_text(_inner(markup, m.end(), tag)):
            out.append((line, "4.1.2", f"Bottone senza nome accessibile (solo icona?): {snippet}"))
        if low in ("input", "select", "textarea"):
            typ = (_value(attrs, "type") or "text").lower()
            if typ not in ("hidden", "submit", "button", "reset", "image") and not named:
                ident = _value(attrs, "id")
                before = markup[:m.start()]
                wrapped = before.count("<label") > before.count("</label") or \
                    before.count("<mat-form-field") > before.count("</mat-form-field")
                if not wrapped and not (ident and ident in labels_for):
                    extra = " (il placeholder non sostituisce l'etichetta)" if _has(attrs, "placeholder") else ""
                    out.append((line, "3.3.2", f"Campo senza etichetta associata{extra}: {snippet}"))
                    out.append((line, "1.3.1", f"Campo senza etichetta associata programmaticamente: {snippet}"))
        if tabindex and tabindex.isdigit() and int(tabindex) > 0:
            out.append((line, "2.4.3", f"tabindex positivo ({tabindex}) altera l'ordine del focus: {snippet}"))
        if _value(attrs, "aria-hidden") == "true" and (low in ("button", "input", "select", "textarea")
                                                       or (low == "a" and _has(attrs, "href"))
                                                       or (tabindex and tabindex.lstrip("-").isdigit() and int(tabindex) >= 0)):
            out.append((line, "4.1.2", f"Elemento focalizzabile con aria-hidden=\"true\": {snippet}"))
        if low == "iframe" and not _has(attrs, "title", "aria-label"):
            out.append((line, "4.1.2", f"iframe senza title: {snippet}"))
        if low in ("video", "audio"):
            if _has(attrs, "autoplay") and not _has(attrs, "muted"):
                out.append((line, "1.4.2", f"Audio/video in riproduzione automatica con sonoro: {snippet}"))
            if low == "video" and "<track" not in _inner(markup, m.end(), tag):
                out.append((line, "1.2.2", f"Video senza traccia di sottotitoli (<track>): {snippet}"))
        hover = _events(attrs, "mouseenter") | _events(attrs, "mouseover")
        if hover and not (_events(attrs, "focus") or _events(attrs, "focusin")):
            out.append((line, "1.4.13", f"Contenuto mostrato al passaggio del mouse senza equivalente al focus: {snippet}"))
        if low == "html" and not _has(attrs, "lang"):
            out.append((line, "3.1.1", "Elemento <html> senza attributo lang."))
        if low == "meta" and _value(attrs, "name") == "viewport":
            content = (_value(attrs, "content") or "").replace(" ", "")
            if "user-scalable=no" in content or re.search(r"maximum-scale=1(\.0)?(,|$)", content):
                out.append((line, "1.4.4", f"Il viewport impedisce lo zoom: {snippet}"))
    return out


def check_styles(css):
    """outline rimosso senza uno stile :focus-visible/:focus alternativo nello stesso file."""
    out = []
    removed = [sel.strip() for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css)
               if re.search(r"outline\s*:\s*(none|0)\b", body)]
    replaced = re.search(r":focus(-visible)?[^{]*\{[^}]*(outline\s*:(?!\s*(none|0)\b)|box-shadow|border)", css)
    if removed and not replaced:
        out.append((0, "2.4.7", "outline rimosso senza indicatore di focus alternativo nei selettori: "
                                + ", ".join(dict.fromkeys(s.split("\n")[-1] for s in removed))[:200]))
    return out


def guess_type(name, markup):
    low = name.lower()
    for t, rx in TYPE_HINTS:
        if re.search(rx, low):
            return t
    for t, rx in (("Form / Campo di input", r"<(form|input|select|textarea)\b"), ("Navbar / Navigazione", r"<nav\b"),
                  ("Tabella", r"<table\b"), ("Modale / Dialog", r"role=\"dialog\"|<dialog\b"),
                  ("Video / Audio", r"<(video|audio)\b")):
        if re.search(rx, markup):
            return t
    return "Altro / Generico"


def analyze_component(proj, path):
    markup, start, source = markup_of(proj, path)
    rel, tpl = proj.rel(path), proj.rel(source)
    findings = [(f"{tpl}:{ln}", c, n) for ln, c, n in check_markup(markup, start)]
    findings += [(rel, c, n) for _, c, n in check_styles(styles_of(proj, path))]
    name = re.sub(r"\.(component|page|view)$", "", Path(path).stem)
    if name in ("page", "+page") or (name == "index" and not rel.endswith(".html")):
        name = Path(path).parent.name or name
    # Angular: il nome viene dal selettore (app-foo → foo), lo stesso tag che l'analisi live trova nel DOM
    sel = re.search(r"selector\s*:\s*['\"]([a-z][\w]*-([\w-]+))['\"]", proj.text.get(path, ""))
    if sel:
        name = sel.group(2)
    return {"type": guess_type(name, markup), "name": name, "location": rel,
            "findings": [{"code": c, "note": f"{where} — {n}"} for where, c, n in findings]}


def scan_project(root, log=print):
    root = Path(root)
    if not root.is_dir():
        raise ValueError(f"Cartella non trovata: {root}")
    fw = detect_framework(root)
    log(f"Framework rilevato: {fw}")
    proj = Project(root)
    routes, children, layout = FRAMEWORKS[fw](proj)
    log(f"{len(proj.files)} file sorgente, {len(routes)} rotte, layout: {[proj.rel(x) for x in layout]}")
    cache = {}

    def comp(path):
        if path not in cache:
            cache[path] = analyze_component(proj, path)
        return cache[path]

    pages = []
    shell = set()
    if layout:
        route_files = {f for _, f in routes}
        files = [f for start in layout for f in tree(start, children, stop=route_files)]
        shell = set(files)
        pages.append({"name": "Layout comune (codice)", "url": "codice:layout",
                      "notes": f"Componenti presenti su tutte le pagine ({fw}).",
                      "components": [comp(f) for f in dict.fromkeys(files)]})
    for path, start in dict.fromkeys(routes):
        files = [f for f in tree(start, children) if f not in shell]
        log(f"  {path}: {len(files)} componenti")
        pages.append({"name": f"{path} (codice)", "url": f"codice:{path}", "route": path,
                      "notes": f"Rotta definita in {proj.rel(start)} ({fw}).",
                      "components": [comp(f) for f in files]})
    # file globali: index.html e fogli di stile non legati a un componente
    for f in [x for x in proj.text if str(x).endswith(".html") and Path(x).name == "index.html"][:1]:
        if fw != "html":
            pages.insert(0, {"name": "index.html (codice)", "url": "codice:index.html", "notes": "Documento host",
                             "components": [{**comp(f), "type": "Struttura pagina / Intestazioni"}]})
    global_css = [f for f in _walk(root, STYLE_EXT) if re.search(r"(^|/)(styles?|global|main|app)\.(s?css|less|sass)$",
                                                                    Path(f).relative_to(proj.root).as_posix())]
    css_findings = [{"code": c, "note": f"{proj.rel(f)} — {n}"} for f in global_css for _, c, n in check_styles(_read(f))]
    if css_findings and pages:
        pages[0]["components"].append({"type": "Struttura pagina / Intestazioni", "name": "Stili globali",
                                       "location": ", ".join(proj.rel(f) for f in global_css),
                                       "findings": css_findings})
    return pages
