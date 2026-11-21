#!/usr/bin/env python3
"""Pronostic Quinte+ du jour (Equidia + synthese de la presse) -> quinte.txt

Format du SMS (lignes courtes pour petit ecran) :
    QUINTE 16/11 15H15
    AUTEUIL
    EQUIDIA
    13 4 9 12
    11 8 1 15
    PRESSE
    4 1 7 12
    3 13 11 8

- Equidia est obligatoire : sans lui, le fichier contient "ERREUR ..." et rien n'est envoye.
- La presse est facultative : si turf-fr.com ne repond pas, le SMS part avec Equidia seul.
- La date (jj/mm) est toujours presente : le raccourci iPhone verifie que le fichier est du jour.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

EQUIDIA_URL = "https://www.equidia.fr/pronostics"
EQUIDIA_QUINTE = "https://www.equidia.fr/Quinte"  # page du quinte du jour (secours)
TURF_BASE = "https://www.turf-fr.com"
TURF_QUINTE = TURF_BASE + "/quinte/presse/"           # page presse du quinte du jour
TURF_DEMAIN = TURF_BASE + "/quinte-demain/presse/"    # page presse du quinte de demain
TURF_LISTE = TURF_BASE + "/courses-pmu/pronostics/presse"  # secours
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)
MOIS = ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet",
        "aout", "septembre", "octobre", "novembre", "decembre"]
SMS_MAX = 160
AVEC_PRESSE = False  # presse mise de cote temporairement : passer a True pour la remettre


# ---------------------------------------------------------------- utilitaires
def fetch(url: str, tries: int = 3) -> str:
    last = None
    for i in range(tries):
        req = urllib.request.Request(
            url, headers={"User-Agent": UA, "Accept-Language": "fr-FR,fr;q=0.9"}
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            # turf-fr renvoie parfois un statut 404 avec une page pourtant complete
            body = e.read().decode("utf-8", "replace")
            if len(body) > 5000:
                return body
            last = e
        except Exception as e:
            last = e
        time.sleep(5 * (i + 1))
    raise RuntimeError(f"{url} : {last}")


def ascii_txt(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c))


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", ascii_txt(s).lower()).strip("-")


def nom_hippodrome(lieu: str) -> str:
    lieu = ascii_txt(clean(lieu)).upper()
    return re.sub(r"^HIPPODROME\s+(DE LA |DES |DU |DE |D')?", "", lieu)


# ------------------------------------------------------------------- Equidia
def parse_equidia(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    blocs = []
    for b in soup.select("div.quinte-prono"):
        lien = b.select_one("a.quinte-prono--course")
        m = re.search(r"/courses/(\d{4}-\d{2}-\d{2})/R(\d+)/C(\d+)", lien.get("href", "") if lien else "")
        if not m:
            continue
        partants = []
        for p in b.select(".quinte-prono--analysis--list--partant"):
            num = p.select_one(".quinte-prono--analysis--list--partant--card span")
            if num and clean(num.get_text()).isdigit():
                partants.append(clean(num.get_text()))
        heure = b.select_one(".quinte-prono--header--date--hours--value")
        lieu = b.select_one(".quinte-prono--course--description--lieu")
        prix = b.select_one(".quinte-prono--course--description--prix")
        blocs.append({
            "date": date.fromisoformat(m.group(1)),
            "reunion": int(m.group(2)),
            "course": int(m.group(3)),
            "heure": clean(heure.get_text()) if heure else "",
            "lieu": nom_hippodrome(lieu.get_text()) if lieu else "",
            "prix": clean(prix.get_text()) if prix else "",
            "partants": partants,
        })
    return blocs


def parse_equidia_quinte(html: str) -> dict | None:
    """Page equidia.fr/Quinte : la course est donnee par l'URL canonique, le prono par le bloc
    "Pronostic Quinte d'Equidia" (quelle que soit sa mise en forme)."""
    soup = BeautifulSoup(html, "html.parser")
    can = soup.find("link", rel="canonical")
    m = re.search(r"/courses/(\d{4}-\d{2}-\d{2})/R(\d+)/C(\d+)", can.get("href", "") if can else "")
    if not m:
        return None
    chemin = m.group(0)
    titre = next((h for h in soup.find_all(["h2", "h3"])
                  if re.search(r"Pronostic Quint.*d.Equidia", h.get_text())), None)
    partants: list[str] = []
    bloc = titre
    for _ in range(10):
        if bloc is None:
            break
        cartes = bloc.select('[class*="partant--card"] span')
        if len(cartes) >= 5:
            partants = [clean(x.get_text()) for x in cartes if clean(x.get_text()).isdigit()]
            break
        bloc = bloc.parent
    heure = ""
    for c in soup.select(".course-container"):
        a = c if c.name == "a" else (c.find_parent("a") or c.find("a"))
        if a and a.get("href", "").rstrip("/") == chemin:
            h = c.select_one(".heure-course")
            heure = clean(h.get_text()) if h else ""
            break
    lieu = prix = ""
    h1 = soup.find("h1")
    mh = re.match(r"^R\d+\s+(.*?)\s+C\d+\s*(.*)$", clean(h1.get_text()) if h1 else "")
    if mh:
        lieu, prix = ascii_txt(mh.group(1)).upper(), mh.group(2)
    return {
        "date": date.fromisoformat(m.group(1)), "reunion": int(m.group(2)), "course": int(m.group(3)),
        "heure": heure, "lieu": lieu, "prix": prix, "partants": partants,
    }


def equidia_du_jour(jour: date, get=fetch) -> dict | None:
    # 1) page des pronostics (bloc "quinte-prono" avec lien de course)
    try:
        q = next((b for b in parse_equidia(get(EQUIDIA_URL)) if b["date"] == jour), None)
        if q and len(q["partants"]) >= 5:
            return q
    except Exception:
        pass
    # 2) page du quinte du jour
    pages_vues = []
    try:
        html = get(EQUIDIA_QUINTE)
        pages_vues.append(html)
        q = parse_equidia_quinte(html)
        if q and q["date"] == jour and len(q["partants"]) >= 5:
            return q
    except Exception:
        pass
    # 3) page de la course elle-meme (le prono de demain y est publie des la veille)
    try:
        pages_vues.append(get(EQUIDIA_URL))
    except Exception:
        pass
    vus = set()
    for html in pages_vues:
        for chemin in re.findall(rf"/courses/{jour:%Y-%m-%d}/R\d+/C\d+", html):
            if chemin in vus:
                continue
            vus.add(chemin)
            try:
                q = parse_equidia_quinte(get("https://www.equidia.fr" + chemin))
            except Exception:
                continue
            if q and q["date"] == jour and len(q["partants"]) >= 5:
                return q
    return None


# -------------------------------------------------------- Presse (turf-fr.com)
def liens_presse(html: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for a in soup.find_all("a", href=True):
        if re.search(r"/pronostics/presse/r\d+-[a-z0-9-]+-\d+/?$", a["href"]):
            out.append((urljoin(TURF_BASE, a["href"]), clean(a.get_text())))
    return out


def trouver_page_course(liens: list[tuple[str, str]], q: dict) -> list[str]:
    """Liens candidats vers la page presse du quinte, du plus sur au moins sur."""
    r, c = q["reunion"], q["course"]
    heure = q["heure"]  # ex. "15:15"
    s = re.sub(r"^prix-", "", slug(q["prix"]))[:20]
    forts, faibles = [], []
    for url, texte in liens:
        if f"/r{r}-" not in url:
            continue
        # 1) lien de la barre laterale : texte "C6 15:15:00"
        if re.match(rf"^C{c}\b", texte) and heure and heure in texte:
            forts.append(url)
        # 2) slug du nom de la course
        elif s and s in url:
            faibles.append(url)
    vus, res = set(), []
    for u in forts + faibles:
        if u not in vus:
            vus.add(u)
            res.append(u)
    return res


def parse_presse(html: str, jour: date) -> list[list[str]] | None:
    """Renvoie la liste des pronostics (8 numeros) par journal, ou None si ce n'est pas la bonne date."""
    texte = re.sub(r"\s+", " ", ascii_txt(BeautifulSoup(html, "html.parser").get_text(" ")).lower())
    motif = rf"\b{jour.day}(er)? {MOIS[jour.month - 1]} {jour.year}\b"  # "1er decembre 2026" ou "15 novembre 2026"
    if not re.search(motif, texte):
        return None
    soup = BeautifulSoup(html, "html.parser")
    for table in soup.find_all("table"):
        lignes = table.find_all("tr")
        entete = " ".join(clean(x.get_text()).lower() for x in lignes[:2])
        if "nom du media" not in ascii_txt(entete):
            continue
        pronos = []
        for tr in lignes:
            cells = [clean(td.get_text()) for td in tr.find_all(["td", "th"])]
            if len(cells) >= 9 and not cells[0].isdigit():
                nums = [x for x in cells[1:9] if x.isdigit()]
                if len(nums) >= 5:
                    pronos.append(nums)
        if pronos:
            return pronos
    return []


def synthese(pronos: list[list[str]], n: int = 8) -> list[str]:
    """1re place = 8 pts ... 8e place = 1 pt. Egalite : le plus cite d'abord."""
    pts: dict[str, int] = {}
    cites: dict[str, int] = {}
    for p in pronos:
        for i, num in enumerate(p[:8]):
            pts[num] = pts.get(num, 0) + (8 - i)
            cites[num] = cites.get(num, 0) + 1
    return sorted(pts, key=lambda k: (-pts[k], -cites[k], int(k)))[:n]


def presse_du_jour(q: dict, get=fetch) -> list[str]:
    # 1) pages dediees au quinte du jour / de demain (date verifiee dans parse_presse)
    for url in (TURF_QUINTE, TURF_DEMAIN):
        try:
            pronos = parse_presse(get(url), q["date"])
            if pronos:
                return synthese(pronos)
        except Exception:
            pass
    # 2) secours : retrouver la course via la barre laterale des pages presse
    a_visiter = [TURF_LISTE]
    vus: set[str] = set()
    tous_liens: list[tuple[str, str]] = []
    while a_visiter and len(vus) < 4:
        url = a_visiter.pop(0)
        if url in vus:
            continue
        vus.add(url)
        html = get(url)
        liens = liens_presse(html)
        tous_liens += liens
        for cand in trouver_page_course(tous_liens, q):
            if cand in vus:
                continue
            vus.add(cand)
            pronos = parse_presse(get(cand), q["date"])
            if pronos:
                return synthese(pronos)
        # sinon, on suit le lien "Aujourd'hui" (R1 du jour) pour avoir la barre laterale complete
        for u, t in liens:
            if t.lower().startswith("aujourd") and u not in vus:
                a_visiter.append(u)
    raise RuntimeError("page presse du quinte introuvable")


# ---------------------------------------------------------------------- SMS
def par4(nums: list[str]) -> list[str]:
    """4 numeros par ligne : evite les retours a la ligne au hasard sur un petit ecran."""
    return [" ".join(nums[i:i + 4]) for i in range(0, len(nums), 4)]


def message(q: dict, presse: list[str] | None) -> str:
    l1 = f"QUINTE {q['date']:%d/%m}"
    if q["heure"]:
        l1 += " " + q["heure"].replace(":", "H")
    lignes = [l1]
    if q["lieu"]:
        lignes.append(q["lieu"])
    lignes += ["EQUIDIA"] + par4(q["partants"])
    if presse:
        lignes += ["PRESSE"] + par4(presse)
    return "\n".join(lignes)[:SMS_MAX]


def construire(jour: date, get=fetch, log=print) -> tuple[str, bool]:
    try:
        q = equidia_du_jour(jour, get)
    except Exception as e:
        return f"ERREUR {jour:%d/%m} : Equidia {e}"[:SMS_MAX], False
    if not q:
        return f"ERREUR {jour:%d/%m} : pronostic Equidia du jour introuvable", False
    presse = None
    try:
        if AVEC_PRESSE:
            presse = presse_du_jour(q, get)
    except Exception as e:
        log(f"[info] presse indisponible : {e}")
    return message(q, presse), True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="AAAA-MM-JJ (defaut : aujourd'hui a Paris)")
    ap.add_argument("--out", default="quinte.txt")
    a = ap.parse_args()
    maintenant = datetime.now(ZoneInfo("Europe/Paris"))
    if a.date:
        jour = date.fromisoformat(a.date)
    elif maintenant.hour >= 12:
        # l'apres-midi et le soir, on prepare le quinte de DEMAIN (publie la veille par Equidia
        # et la presse) : le fichier est pret bien avant l'envoi du matin, meme si GitHub
        # lance la tache avec plusieurs heures de retard.
        jour = maintenant.date() + timedelta(days=1)
    else:
        jour = maintenant.date()

    texte, ok = construire(jour)
    # Ne jamais remplacer un bon pronostic du meme jour par une erreur
    try:
        ancien = open(a.out, encoding="utf-8").read()
    except OSError:
        ancien = ""
    if not ok and ancien.startswith(f"QUINTE {jour:%d/%m}"):
        print(f"[info] erreur ignoree, pronostic du {jour:%d/%m} deja present")
        texte, ok = ancien.strip(), True
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(texte + "\n")
    print(texte)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"ok={'true' if ok else 'false'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
