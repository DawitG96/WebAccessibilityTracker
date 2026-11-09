# -*- coding: utf-8 -*-
"""Verifica dell'analisi statica su mini-progetti Angular, React e Vue e dell'import nel database.

Eseguire con: python tests/test_scanner.py
"""
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
    assert codes(pages, "Layout comune (codice)") == {"app": [], "header": ["4.1.2"]}
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


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
