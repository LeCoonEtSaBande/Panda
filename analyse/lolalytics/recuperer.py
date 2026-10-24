"""Récupère, une fois par patch, la tier list et les contres de Lolalytics (Platine et plus, tous serveurs).

Pages lues (une toutes les 3 secondes, environ 250 par patch) :
- la tier list de chaque poste : taux de victoire, parties, pick, ban de chaque champion ;
- la page « build » de chaque champion à chaque poste où il est assez joué : elle contient son taux de
  victoire contre chaque adversaire, à chaque poste adverse (lane contre lane, mais aussi jungler contre
  jungler, etc.), avec le nombre de parties et deux écarts :
  * delta_1 = taux de victoire du matchup - (100 - taux de victoire moyen de l'adversaire) ;
  * delta_2 = la même chose, corrigée aussi du taux moyen du champion lui-même : c'est l'effet propre du
    matchup, le « contre » (positif = le champion gagne ce matchup plus que prévu).
Les données sont lues dans l'état sérialisé de la page (bloc « qwik/json »), pas dans le texte affiché.

Écrit dans analyse/lolalytics/<patch>/ : champions.csv, matchups.csv et resume.md. Ne garde pas les pages.
Kayn : Lolalytics ne sépare pas ses deux formes (une seule ligne « Kayn »).

    python3 analyse/lolalytics/recuperer.py [--max-pages 400] [--pause 3]
"""

import argparse
import csv
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ICI = Path(__file__).resolve().parent
BASE = "https://lolalytics.com/lol"
TIER = "platinum_plus"
POSTES = {"top": "top", "jungle": "jgl", "middle": "mid", "bottom": "adc", "support": "sup"}
ENTETES = {"User-Agent": "Mozilla/5.0 (compatible; panda-draft/1.0; projet personnel, une fois par patch)",
           "Accept": "text/html,application/xhtml+xml", "Accept-Language": "en-US,en;q=0.9"}
CHIFFRES = "0123456789abcdefghijklmnopqrstuvwxyz"
MIN_PARTIES_PAGE = 300          # on ne lit la page d'un champion à un poste qu'à partir de ce nombre de parties
POOL = ("Fiddlesticks", "Ivern", "Dr. Mundo", "Kayn", "Viego", "Maokai", "Skarner")


# --- Lecture de l'état sérialisé (Qwik) ---------------------------------------------------------

class Etat:
    """Les objets sérialisés d'une page. Dans un objet ou une liste, chaque valeur est l'indice
    (en base 36) d'un autre objet de la liste."""

    def __init__(self, html):
        m = re.search(r'<script type="qwik/json">([\s\S]*?)</script>', html)
        if not m:
            raise ValueError("pas de bloc qwik/json : la page a changé")
        self.objs = json.loads(m.group(1))["objs"]

    def val(self, ref):
        if isinstance(ref, str) and ref and all(c in CHIFFRES for c in ref):
            i = int(ref, 36)
            if i < len(self.objs):
                return self.objs[i]
        return ref

    def plein(self, ref, profondeur=4):
        """La valeur entièrement résolue (dictionnaires et listes compris)."""
        v = self.val(ref)
        if profondeur == 0:
            return v
        if isinstance(v, dict):
            return {k: self.plein(x, profondeur - 1) for k, x in v.items()}
        if isinstance(v, list):
            return [self.plein(x, profondeur - 1) for x in v]
        return v

    def dicts(self):
        return [o for o in self.objs if isinstance(o, dict)]


def lire_tierlist(html):
    """{identifiant du champion: ligne} et le patch."""
    e = Etat(html)
    patch = None
    for o in e.dicts():
        if "patch" in o and "champPath" in o:
            patch = e.val(o["patch"])
    for o in e.dicts():
        if len(o) < 50:
            continue
        lignes = {k: e.plein(v, 1) for k, v in o.items()}
        if all(isinstance(l, dict) and {"wr", "games", "pr"} <= set(l) for l in lignes.values()):
            return {int(k): l for k, l in lignes.items()}, patch
    raise ValueError("tier list introuvable dans la page")


def lire_build(html):
    """(parties du champion à ce poste, taux moyen du palier, {poste adverse: [ [id, wr, d1, d2, pr, n], ...]})."""
    e = Etat(html)
    for o in e.dicts():
        if "enemy" in o and "n" in o:
            ennemis = e.plein(o["enemy"], 3)
            if isinstance(ennemis, dict):
                return e.val(o["n"]), e.val(o.get("avgWr")), ennemis
    raise ValueError("matchups introuvables dans la page")


# --- Téléchargement ------------------------------------------------------------------------------

class Client:
    def __init__(self, pause):
        self.pause, self.dernier, self.pages = pause, 0.0, 0

    def get(self, url):
        attente = self.pause - (time.monotonic() - self.dernier)
        if attente > 0:
            time.sleep(attente)
        for essai in range(3):
            self.dernier = time.monotonic()
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=ENTETES), timeout=30) as r:
                    self.pages += 1
                    return r.read().decode("utf-8", errors="replace")
            except urllib.error.HTTPError as err:
                if err.code in (403, 429):
                    raise SystemExit(f"Lolalytics refuse l'accès ({err.code}) : arrêt, sans insister.")
                if err.code == 404:
                    return None
                time.sleep(10 * (essai + 1))
            except (urllib.error.URLError, TimeoutError, OSError):
                time.sleep(10 * (essai + 1))
        return None


def noms_des_champions():
    with urllib.request.urlopen("https://ddragon.leagueoflegends.com/api/versions.json", timeout=30) as r:
        version = json.load(r)[0]
    with urllib.request.urlopen(f"https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json", timeout=30) as r:
        donnees = json.load(r)["data"]
    return {int(f["key"]): f["name"] for f in donnees.values()}, {int(f["key"]): f["id"].lower() for f in donnees.values()}


def nombre(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


# --- Programme ------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-pages", type=int, default=400)
    parser.add_argument("--pause", type=float, default=3.0)
    args = parser.parse_args()
    noms, slugs = noms_des_champions()
    client = Client(args.pause)

    champions, patch = [], None
    for poste_l, poste in POSTES.items():
        html = client.get(f"{BASE}/tierlist/?lane={poste_l}&tier={TIER}")
        if html is None:
            print(f"Tier list {poste_l} : page absente.")
            continue
        lignes, patch = lire_tierlist(html)
        for cid, l in lignes.items():
            if (nombre(l.get("games")) or 0) <= 0:
                continue
            champions.append({"champion": noms.get(cid, f"?{cid}"), "id": cid, "poste": poste, "parties": int(nombre(l["games"])),
                              "victoires": nombre(l["wr"]), "pick": nombre(l["pr"]), "ban": nombre(l.get("br")),
                              "part_du_poste": nombre(l.get("pctLane")), "rang": l.get("rank"), "tier": l.get("tier")})
        print(f"Tier list {poste_l} : {sum(c['poste'] == poste for c in champions)} champions (patch {patch}).", flush=True)
    if not champions:
        print("::error::Aucune tier list lue.")
        return 1

    dossier = ICI / (patch or "patch_inconnu")
    dossier.mkdir(parents=True, exist_ok=True)
    a_lire = sorted([c for c in champions if c["parties"] >= MIN_PARTIES_PAGE], key=lambda c: -c["parties"])[: args.max_pages]
    matchups, echecs = [], 0
    for i, c in enumerate(a_lire, 1):
        poste_l = next(k for k, v in POSTES.items() if v == c["poste"])
        html = client.get(f"{BASE}/{slugs.get(c['id'], c['champion'].lower())}/build/?lane={poste_l}&tier={TIER}")
        try:
            if html is None:
                raise ValueError("page absente")
            _, _, ennemis = lire_build(html)
        except ValueError as err:
            echecs += 1
            print(f"::warning::{c['champion']} {c['poste']} : {err}")
            continue
        for poste_adverse, liste in ennemis.items():
            if poste_adverse not in POSTES or not isinstance(liste, list):
                continue
            for e in liste:
                if not isinstance(e, list) or len(e) < 6:
                    continue
                matchups.append({"champion": c["champion"], "poste": c["poste"], "adversaire": noms.get(int(e[0]), f"?{e[0]}"),
                                 "poste_adversaire": POSTES[poste_adverse], "parties": int(e[5]), "victoires": e[1],
                                 "delta_1": e[2], "delta_2": e[3], "pick_adversaire": e[4]})
        if i % 25 == 0:
            print(f"{i} / {len(a_lire)} pages de champion lues ({echecs} échecs).", flush=True)

    with open(dossier / "champions.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(champions[0]), delimiter=";", lineterminator="\n")
        w.writeheader()
        w.writerows(sorted(champions, key=lambda c: (c["poste"], -(c["victoires"] or 0))))
    if matchups:
        with open(dossier / "matchups.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(matchups[0]), delimiter=";", lineterminator="\n")
            w.writeheader()
            w.writerows(matchups)
    ecrire_resume(dossier, patch, champions, matchups, client.pages, echecs)
    print(f"Patch {patch} : {len(champions)} lignes de tier list, {len(matchups)} matchups, {client.pages} pages, {echecs} échecs.")
    return 0


def ecrire_resume(dossier, patch, champions, matchups, pages, echecs):
    jungle = sorted([c for c in champions if c["poste"] == "jgl" and c["parties"] >= 1000], key=lambda c: -(c["victoires"] or 0))
    lignes = [f"# Lolalytics, patch {patch} (Platine et plus, tous serveurs)", "",
              f"- {pages} pages lues, {echecs} échecs. {len(matchups)} matchups.",
              "- Contre (delta 2) : de combien le champion gagne ce matchup plus que prévu d'après les taux moyens des deux champions, en points.", "",
              "## Junglers (1 000 parties ou plus), du plus fort au plus faible", "",
              "| Champion | Victoires | Parties | Pick | Ban |", "|---|---|---|---|---|"]
    lignes += [f"| {'**' + c['champion'] + '**' if c['champion'] in POOL else c['champion']} | {c['victoires']:.2f} % | {c['parties']} | "
               f"{c['pick']:.2f} % | {c['ban'] or 0:.2f} % |" for c in jungle]
    lignes += [""]
    for nom in POOL:
        duels = [m for m in matchups if m["champion"] == nom and m["poste"] == "jgl" and m["poste_adversaire"] == "jgl" and m["parties"] >= 100]
        if not duels:
            continue
        duels.sort(key=lambda m: -m["delta_2"])
        lignes += [f"## {nom} en jungle contre le jungler adverse (100 parties ou plus)", "",
                   "- Meilleurs : " + ", ".join(f"{m['adversaire']} {m['victoires']:.1f} % ({m['delta_2']:+.1f})" for m in duels[:5]),
                   "- Pires : " + ", ".join(f"{m['adversaire']} {m['victoires']:.1f} % ({m['delta_2']:+.1f})" for m in duels[::-1][:5]), ""]
    (dossier / "resume.md").write_text("\n".join(lignes) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
