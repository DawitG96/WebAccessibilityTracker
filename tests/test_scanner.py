# -*- coding: utf-8 -*-
"""Verifica dell'analisi statica su mini-progetti Angular, React e Vue e dell'import nel database.

Eseguire con: python tests/test_scanner.py
"""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scanner.static import scan_project  # noqa: E402

ANGULAR = {
    "package.json": '{"dependencies": {"@angular/core": "17"}}',
    "src/index.html": '<html><head><meta name="viewport" content="width=device-width, user-scalable=no"></head>'
                      '<body><app-root></app-root></body></html>',
    "src/app/app.component.ts": "@Component({selector: 'app-root', templateUrl: './app.component.html'})\n"
                                "export class AppComponent {}",
    "src/app/app.component.html": "<app-header></app-header><router-outlet></router-outlet>",
    "src/app/header/header.component.ts": "@Component({selector: 'app-header', template: `<nav>"
                                          "<button (click)=\"t()\"><i class=\"fa fa-bars\"></i></button></nav>`})\n"
                                          "export class HeaderComponent {}",
    "src/app/app.routes.ts": "import { HomeComponent } from './home/home.component';\n"
                             "export const routes: Routes = [\n"
                             "  { path: '', component: HomeComponent },\n"
                             "  { path: 'area', children: [\n"
                             "     { path: 'profilo', loadComponent: () => import('./profile/profile.component')"
                             ".then(m => m.ProfileComponent) } ] } ];",
    "src/app/home/home.component.ts": "@Component({selector: 'app-home', templateUrl: './home.component.html', "
                                      "styleUrls: ['./home.component.scss']})\nexport class HomeComponent {}",
    "src/app/home/home.component.html": '<img src="a.jpg">\n<div class="card" (click)="open()">Apri</div>\n'
                                        '<app-gallery></app-gallery>',
    "src/app/home/home.component.scss": "button:focus { outline: none; }",
    "src/app/gallery/gallery.component.ts": "@Component({selector: 'app-gallery', template: `<input placeholder=\"Cerca\">`})\n"
                                            "export class GalleryComponent {}",
    "src/app/profile/profile.component.ts": "@Component({selector: 'app-profile', template: `<label for=\"n\">Nome</label>"
                                            "<input id=\"n\"><a (click)=\"x()\">vai</a>`})\nexport class ProfileComponent {}",
}

REACT = {
    "package.json": '{"dependencies": {"react": "18", "react-router-dom": "6"}}',
    "src/App.jsx": "import { Routes, Route } from 'react-router-dom';\nimport Home from './pages/Home';\n"
                   "import Nav from './components/Nav';\n"
                   "export default function App() { return (<><Nav /><Routes>"
                   "<Route path=\"/\" element={<Home />} /></Routes></>); }",
    "src/components/Nav.jsx": "export default function Nav() { return <nav><a href=\"/\">Home</a></nav>; }",
    "src/pages/Home.jsx": "import Card from '../components/Card';\n"
                          "export default function Home() { return <main><Card /><img src=\"x.png\" alt=\"\" /></main>; }",
    "src/components/Card.jsx": "export default function Card() { return <span onClick={() => go()} tabIndex={0}>Card</span>; }",
}

VUE = {
    "package.json": '{"dependencies": {"vue": "3", "vue-router": "4"}}',
    "src/App.vue": "<template><router-view /></template>",
    "src/router/index.js": "import { createRouter } from 'vue-router';\nimport Home from '../views/Home.vue';\n"
                           "const routes = [{ path: '/', component: Home },"
                           " { path: '/info', component: () => import('../views/Info.vue') }];",
    "src/views/Home.vue": "<template>\n  <div>\n    <video src=\"v.mp4\" autoplay></video>\n    <MyModal />\n  </div>\n</template>\n"
                          "<script setup>import MyModal from '../components/MyModal.vue'</script>",
    "src/components/MyModal.vue": "<template><div role=\"dialog\"><button @click=\"close\" aria-label=\"Chiudi\">x</button>"
                                  "<div tabindex=\"3\">a</div></div></template>",
    "src/views/Info.vue": "<template><iframe src=\"https://example.com\"></iframe></template>",
}


def write(root, files):
    for rel, text in files.items():
        p = Path(root) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")


def codes(pages, page_name):
    page = next(p for p in pages if p["name"] == page_name)
    return {c["name"]: sorted({f["code"] for f in c["findings"]}) for c in page["components"]}


def run(files):
    with tempfile.TemporaryDirectory() as d:
        write(d, files)
        return scan_project(d, log=lambda *_: None)


def test_angular():
    pages = run(ANGULAR)
    names = [p["name"] for p in pages]
    assert names == ["index.html (codice)", "Layout comune (codice)", "/ (codice)", "/area/profilo (codice)"], names
    assert codes(pages, "index.html (codice)") == {"index": ["1.4.4", "3.1.1"]}
    assert codes(pages, "Layout comune (codice)") == {"root": [], "header": ["4.1.2"]}
    home = codes(pages, "/ (codice)")
    assert home["home"] == ["1.1.1", "2.1.1", "2.4.7", "4.1.2"], home
    assert home["gallery"] == ["1.3.1", "3.3.2"], home
    assert codes(pages, "/area/profilo (codice)") == {"profile": ["2.1.1"]}


def test_react():
    pages = run(REACT)
    assert codes(pages, "Layout comune (codice)") == {"App": [], "Nav": []}
    # Card ha tabIndex ma nessun gestore tastiera né ruolo; l'img con alt="" è decorativa e va bene
    assert codes(pages, "/ (codice)") == {"Home": [], "Card": ["2.1.1", "4.1.2"]}


def test_vue():
    pages = run(VUE)
    home = codes(pages, "/ (codice)")
    assert home == {"Home": ["1.2.2", "1.4.2"], "MyModal": ["2.4.3"]}, home
    assert codes(pages, "/info (codice)") == {"Info": ["4.1.2"]}
    assert next(c for p in pages for c in p["components"] if c["name"] == "MyModal")["type"] == "Modale / Dialog"


def test_import():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
        os.environ["DB_PATH"] = os.path.join(d, "t.db")
        import database
        database.DB_PATH = os.environ["DB_PATH"]
        from scanner.store import import_results
        database.init_db()
        db = database.get_db()
        pl = db.execute("INSERT INTO platforms (name, slug) VALUES ('p', 'p')").lastrowid
        pr = db.execute("INSERT INTO projects (name, slug, platform_id) VALUES ('x', 'x', ?)", (pl,)).lastrowid
        pages = run(ANGULAR)
        first = import_results(db, pr, pages, "codice")
        again = import_results(db, pr, pages, "codice")
        assert first["pagine"] == 4 and first["componenti"] == 6 and first["anomalie"] > 0, first
        assert again["pagine"] == 0 and again["componenti"] == 0, again
        n = db.execute("SELECT COUNT(*) FROM evaluations WHERE status = 'non_conforme'").fetchone()[0]
        assert n == first["anomalie"], n
        db.close()



def test_live_merge():
    from scanner.store import match_route
    assert match_route("/news/42", ["/news", "/news/:id", "/**"]) == "/news/:id"
    assert match_route("/", ["/", "/**"]) == "/" and match_route("/x/y", ["/news"]) is None
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
        import database
        database.DB_PATH = os.path.join(d, "t.db")
        from scanner.store import code_sources, import_results, shot_path
        database.init_db()
        db = database.get_db()
        pl = db.execute("INSERT INTO platforms (name, slug) VALUES ('p', 'p')").lastrowid
        pr = db.execute("INSERT INTO projects (name, slug, platform_id) VALUES ('x', 'x', ?)", (pl,)).lastrowid
        import_results(db, pr, run(ANGULAR), "codice")
        routes, sources = code_sources(db, pr)
        assert set(routes) == {"/", "/area/profilo"} and "header" in sources, (routes, sources)
        live = [{"name": "/", "url": "http://x/", "route": "/", "components": [
            # header (layout) con lo stesso criterio del codice: conferma
            {"type": "Navbar / Navigazione", "name": "Menu principale", "location": "nav", "src": "header",
             "findings": [{"code": "4.1.2", "note": "bottone senza nome"}], "passed": []},
            # home: axe ha verificato 1.1.1 senza violazioni, la rilevazione del codice resta non conforme con una nota
            {"type": "Testo / Contenuto", "name": "Testo in «pagina»", "location": "main", "src": "home",
             "findings": [], "passed": ["1.1.1"]},
            {"type": "Link", "name": "Link in «pagina»", "location": "body", "src": "",
             "findings": [{"code": "2.4.4", "note": "link vago"}], "passed": [], "rect": {"x": 0, "y": 0, "w": 9, "h": 9}}],
            "shot": {"w": 100, "h": 50, "image": b"jpg", "sources": {
                "header": [{"rect": {"x": 0, "y": 0, "w": 100, "h": 10}, "sel": "app-header"}]}}}]
        stats = import_results(db, pr, live, "live")
        assert stats["pagine"] == 0 and stats["componenti"] == 1 and stats["collegati"] == 2, stats
        assert stats["confermate"] == 1 and stats["non_riscontrate"] == 1, stats
        assert db.execute("SELECT url FROM pages WHERE route = '/'").fetchone()[0] == "http://x/"
        # mappa dello screenshot: riquadro del componente live e del componente del codice (dal layout)
        page_id, shot = db.execute("SELECT id, shot FROM pages WHERE route = '/'").fetchone()
        header_id = db.execute("SELECT id FROM components WHERE source = 'header'").fetchone()[0]
        boxes = json.loads(shot)["boxes"]
        assert os.path.exists(shot_path(page_id)) and len(boxes) == 2 and boxes[1]["id"] == header_id, boxes
        assert db.execute("SELECT name FROM components WHERE source = 'header'").fetchone()[0] == "header — Menu principale"
        st = {r[0]: r[1] for r in db.execute("""SELECT c.source || ' ' || cr.code, e.status FROM evaluations e
              JOIN components c ON c.id = e.component_id JOIN criteria cr ON cr.id = e.criterion_id""")}
        assert st["home 1.1.1"] == "non_conforme" and st["header 4.1.2"] == "non_conforme", st
        # nelle note ogni pagina compare sempre, anche oltre il limite di occorrenze
        from scanner.store import _note
        many = _note([f"/p{i}: x" for i in range(20)] + [f"/p0: y{i}" for i in range(5)])
        assert all(f"/p{i}: x" in many for i in range(20)) and "altre 5" in many, many
        # analisi mirata di una pagina: le righe delle altre pagine nel blocco live restano
        from scanner.store import _kept
        assert _kept("[Analisi automatica live, x]\n• /a: uno\n• /b: due", "live", {"/b"}) == ["/a: uno"]
        # live senza codice e codice importato dopo: la pagina live viene adottata dalla rotta
        pr2 = db.execute("INSERT INTO projects (name, slug, platform_id) VALUES ('y', 'y', ?)", (pl,)).lastrowid
        import_results(db, pr2, [{"name": "/area/profilo", "url": "http://x/area/profilo", "components": []}], "live")
        assert import_results(db, pr2, run(ANGULAR), "codice")["pagine"] == 3
        assert db.execute("SELECT route FROM pages WHERE project_id = ? AND url = 'http://x/area/profilo'",
                          (pr2,)).fetchone()[0] == "/area/profilo"
        db.close()



PATTERN_PAGE = """<!doctype html><html lang="it"><head><title>Prova</title><style>
  a { color: #000; } a:focus { outline: none; box-shadow: 0 0 0 4px rgba(13, 110, 253, .25); }
  button:focus, [tabindex]:focus { outline: 3px solid #000; } #dlg { display: none; } #dlg.open { display: block; }
</style></head><body><main><h1>Prova</h1>
  <a href="#x">Link con focus debole</a>
  <div role="button" tabindex="0" id="fake" onclick="box.hidden = !box.hidden">Solo click</div>
  <div id="box" hidden><a href="#y">dentro</a></div>
  <button aria-haspopup="dialog" onclick="dlg.classList.add('open')">Apri dialog</button>
  <div id="dlg" role="dialog" aria-modal="true"><p>Testo</p><button onclick="dlg.classList.remove('open')">Chiudi</button></div>
  <form onsubmit="return false"><label>Nome <input name="n"></label><button>Invia</button></form>
  <div role="tablist" aria-label="Schede"><button role="tab" aria-selected="true">A</button>
    <button role="tab" aria-selected="false" tabindex="-1">B</button></div>
</main></body></html>"""


def test_live_patterns():
    """Regole note su una pagina locale: focus poco contrastato, widget solo col mouse, dialog, tab senza frecce."""
    from scanner.live import scan_site
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "p.html"
        f.write_text(PATTERN_PAGE, encoding="utf-8")
        pages = scan_site(f.as_uri(), urls=[f.as_uri()], max_pages=1, log=lambda *_: None)
    notes = [(x["code"], x["note"]) for c in pages[0]["components"] for x in c["findings"]]
    def has(code, text):
        return any(c == code and text in n for c, n in notes)
    assert has("1.4.11", "Link con focus debole"), notes
    assert has("2.1.1", "[button] Il controllo «Solo click»"), notes
    assert has("4.1.2", "[Dialog] Il dialog") and has("2.4.3", "focus resta fuori dal dialog"), notes
    assert has("2.4.3", "il focus non torna"), notes
    assert has("2.1.1", "[Tab] In «Schede»"), notes
    # bottone non attivato dall'analisi: verifica manuale esplicita, non silenzio
    manual = [x for c in pages[0]["components"] for x in c["findings"] if x.get("manual")]
    assert any("Bottone di invio «Invia»" in x["note"] for x in manual), manual
    assert {"Link", "Tab"} <= set(pages[0]["shot"]["pattern"]), pages[0]["shot"]["pattern"]
    # link e bottoni sono istanze riusate: un componente per firma, con le occorrenze per contenitore
    link = next(c for c in pages[0]["components"] if c["location"] == "riuso:Link:a")
    assert link["name"] == "Link «a»" and any("1.4.11" == f["code"] for f in link["findings"]), link
    assert pages[0]["riuso"]["riuso:Link:a"]["where"], pages[0]["riuso"]
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
        import database
        database.DB_PATH = os.path.join(d, "t.db")
        from scanner.store import import_results
        database.init_db()
        db = database.get_db()
        pl = db.execute("INSERT INTO platforms (name, slug) VALUES ('p', 'p')").lastrowid
        pr = db.execute("INSERT INTO projects (name, slug, platform_id) VALUES ('x', 'x', ?)", (pl,)).lastrowid
        import_results(db, pr, pages, "live")
        notes, status = db.execute("""SELECT c.notes, e.status FROM components c JOIN pages p ON p.id = c.page_id
            JOIN evaluations e ON e.component_id = c.id JOIN criteria cr ON cr.id = e.criterion_id
            WHERE p.url = 'riuso:' AND c.name = 'Link «a»' AND cr.code = '1.4.11'""").fetchone()
        assert status == "non_conforme" and "• /" in notes, (status, notes)
        n = db.execute("""SELECT COUNT(*) FROM evaluations e WHERE e.status = 'da_verificare'
                          AND e.note LIKE '%DA VERIFICARE A MANO%Invia%'""").fetchone()[0]
        assert n == 1, n
        db.close()


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
