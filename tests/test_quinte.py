"""Tests hors ligne : python tests/test_quinte.py"""
import os
import sys
from datetime import date

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(ICI))
import quinte  # noqa: E402
quinte.AVEC_PRESSE = True  # les tests couvrent aussi la presse

PAGES = {
    quinte.EQUIDIA_URL: "equidia.html",
    quinte.TURF_QUINTE: "turf_course.html",
    quinte.TURF_LISTE: "turf_liste.html",
    quinte.TURF_BASE + "/courses-pmu/pronostics/presse/r1-prix-bernard-secly-390466": "turf_r1c1.html",
    quinte.TURF_BASE + "/courses-pmu/pronostics/presse/r1-prix-la-haye-jousselin-390471": "turf_course.html",
}


def faux_get(url, pannes=()):
    if url in pannes or url not in PAGES:
        raise RuntimeError(f"404 {url}")
    return open(os.path.join(ICI, PAGES[url]), encoding="utf-8").read()


def test_complet():
    txt, ok = quinte.construire(date(2026, 11, 15), get=faux_get, log=lambda *_: None)
    assert ok, txt
    lignes = txt.splitlines()
    assert lignes[0] == "QUINTE 15/11 15H15", lignes
    assert lignes[1] == "AUTEUIL"
    assert lignes[2:5] == ["EQUIDIA", "13 4 9 12", "11 8 1 15"]
    assert lignes[5] == "PRESSE"
    assert len((lignes[6] + " " + lignes[7]).split()) == 8
    assert len(txt) <= 160
    print(txt, f"\n({len(txt)} caracteres)\n")


def test_presse_secours():
    # page /quinte/presse/ en panne : on passe par la barre laterale
    get = lambda u: faux_get(u, pannes={quinte.TURF_QUINTE})
    txt, ok = quinte.construire(date(2026, 11, 15), get=get, log=lambda *_: None)
    assert ok and "PRESSE" in txt, txt


def test_presse_en_panne():
    get = lambda u: faux_get(u, pannes={quinte.TURF_QUINTE, quinte.TURF_LISTE})
    txt, ok = quinte.construire(date(2026, 11, 15), get=get, log=lambda *_: None)
    assert ok and "EQUIDIA" in txt and "PRESSE" not in txt, txt


def test_equidia_secours_page_quinte():
    # cas reel du 17/11 : /pronostics n'a que "demain", le prono du jour est sur /Quinte
    pages = dict(PAGES)
    pages[quinte.EQUIDIA_URL] = "equidia_demain_seul.html"
    pages[quinte.EQUIDIA_QUINTE] = "equidia_quinte.html"
    get = lambda u: open(os.path.join(ICI, pages[u]), encoding="utf-8").read() if u in pages else (_ for _ in ()).throw(RuntimeError(u))
    txt, ok = quinte.construire(date(2026, 11, 17), get=get, log=lambda *_: None)
    assert ok, txt
    assert txt.splitlines()[:5] == ["QUINTE 17/11 13H57", "CHANTILLY", "EQUIDIA", "5 4 8 7", "14"], txt
    print(txt, "\n")


def test_equidia_page_course_veille():
    # cas reel du 21/11 a 14h : /pronostics et /Quinte n'ont que le jour J,
    # mais la page de la course du lendemain contient deja le prono
    pages = dict(PAGES)
    pages[quinte.EQUIDIA_URL] = "equidia_demain_seul.html"  # contient un lien /courses/2026-11-18/R1/C1
    pages[quinte.EQUIDIA_QUINTE] = "equidia_quinte.html"     # quinte du 17
    html = open(os.path.join(ICI, "equidia_quinte.html"), encoding="utf-8").read().replace("2026-11-17/R1/C4", "2026-11-18/R1/C1").replace("C4 PRIX", "C1 PRIX")
    get = lambda u: html if u.endswith("/courses/2026-11-18/R1/C1") else open(os.path.join(ICI, pages[u]), encoding="utf-8").read()
    txt, ok = quinte.construire(date(2026, 11, 18), get=get, log=lambda *_: None)
    assert ok and txt.startswith("QUINTE 18/11"), txt


def test_mauvais_jour():
    txt, ok = quinte.construire(date(2026, 11, 16), get=faux_get, log=lambda *_: None)
    assert not ok and txt.startswith("ERREUR 16/11"), txt


def test_date_presse_verifiee():
    html = open(os.path.join(ICI, "turf_course.html"), encoding="utf-8").read()
    assert quinte.parse_presse(html, date(2026, 11, 22)) is None


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            f()
            print("OK", name)
