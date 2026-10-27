"""Diagnostic : où Lolalytics charge-t-il la synergie (onglet « Synergy », chargé au clic) ?

Lit une page champion, les scripts qu'elle charge, et cherche les adresses d'API (« mega », « ep= ») et les
mentions de synergie ; essaie quelques adresses candidates. Écrit lolalytics/diagnostic_synergie.md.
Une dizaine de requêtes au plus, une toutes les 3 secondes.

    python3 lolalytics/diagnostic_synergie.py
"""

import re
import time
import urllib.error
import urllib.request
from pathlib import Path

ICI = Path(__file__).resolve().parent
ENTETES = {"User-Agent": "Mozilla/5.0 (compatible; panda-draft/1.0; projet personnel, une fois par patch)",
           "Accept": "text/html,application/xhtml+xml,application/json,*/*", "Accept-Language": "en-US,en;q=0.9"}
PAGE = "https://lolalytics.com/lol/gwen/build/?lane=top&tier=platinum_plus"
lignes = ["# Diagnostic synergie Lolalytics", ""]


def get(url):
    time.sleep(3)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=ENTETES), timeout=30) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:  # noqa: BLE001
        return str(e), ""


def extraits(texte, motif, largeur=160, maxi=12):
    sortie = []
    for m in re.finditer(motif, texte):
        sortie.append(texte[max(0, m.start() - largeur): m.end() + largeur].replace("\n", " "))
        if len(sortie) >= maxi:
            break
    return sortie


statut, html = get(PAGE)
lignes += [f"Page {PAGE} : {statut}, {len(html)} caractères", ""]
for motif in (r"https?://[a-z0-9]+\.lolalytics\.com[^\"' ]*", r"ep=[a-z0-9_-]+", r"[Ss]ynerg", r"\"team"):
    ex = extraits(html, motif)
    lignes += [f"## Dans la page : {motif} ({len(ex)})", ""] + [f"- `{e}`" for e in ex] + [""]
scripts = sorted(set(re.findall(r"(/build/q-[A-Za-z0-9_-]+\.js)", html)))[:60]
lignes += [f"## Scripts : {len(scripts)}", ""]
trouves = 0
for s in scripts:
    if trouves >= 6:
        break
    st, js = get("https://lolalytics.com" + s)
    ex = extraits(js, r"ep=|mega|[Ss]ynerg", 200, 6)
    if ex:
        trouves += 1
        lignes += [f"### {s} ({st})", ""] + [f"- `{e}`" for e in ex] + [""]
for url in ("https://a1.lolalytics.com/mega/?ep=build-team&p=d&v=1&patch=30&c=gwen&lane=top&tier=platinum_plus&queue=420&region=all",
            "https://ax.lolalytics.com/mega/?ep=build-team&p=d&v=1&patch=30&c=gwen&lane=top&tier=platinum_plus&queue=420&region=all"):
    st, txt = get(url)
    lignes += [f"## Essai {url} : {st}", "", f"`{txt[:400]}`", ""]
(ICI / "diagnostic_synergie.md").write_text("\n".join(lignes) + "\n", encoding="utf-8")
print("\n".join(lignes))
