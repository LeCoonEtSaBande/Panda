"""Les contres par lane : quel champion gagne sa lane contre quel autre, à 15 minutes.

Mesure, pour chaque partie avec timeline, ce qui se passe sur chaque lane avant 15 minutes :
- écart d'or à 15 min entre les deux joueurs de la lane (mesure principale : elle contient les kills,
  les sbires et les plaques) ;
- écart d'XP à 15 min ;
- solde de kills : kills + assistances - morts des joueurs de la lane, avant 15 min ;
- plaques de la lane prises avant 15 min ;
- première tour extérieure de la lane tombée avant 15 min (+1 si c'est celle de l'adversaire).
Lanes : top, jungle (jungler contre jungler), mid, bot. La bot se joue à deux : l'or du duo (ADC + support)
est mesuré ensemble, et le modèle sépare ADC contre ADC et support contre support.

Le modèle, lane par lane, sur l'écart d'or :
1. force de lane de chaque champion (régression ridge : un coefficient par champion à ce poste) ;
2. effet propre de chaque paire A contre B : ce qui reste quand on retire les deux forces de lane,
   rétréci vers 0 selon le nombre de parties (une paire vue 5 fois garde un effet presque nul ; une paire
   vue 200 fois garde presque toute sa moyenne). Le rétrécissement est estimé sur les données.
Résultat pour A contre B = force de A - force de B + effet propre de la paire.
« Contre identifié » : effet propre d'au moins 150 or, à plus de deux marges d'erreur de 0, et au moins
20 parties. Sinon, le résultat de la paire repose sur les deux forces de lane seulement.
On traduit aussi l'or en victoires (régression logistique de la victoire sur l'écart d'or de la lane).

Chaque lancement relit toutes les parties avec timeline, compte celles qu'il ne connaissait pas encore,
et signale les contres apparus ou disparus depuis le passage précédent.

    python3 analyse/contres/contres.py        (PANDA_DONNEES : dossier des données, par défaut analyse/donnees)
"""

import csv
import gzip
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent))

import lecture  # noqa: E402

RESULTATS = ICI / "resultats"
POSTES = ("top", "jgl", "mid", "adc", "sup")
LANES = {"top": ("top",), "jgl": ("jgl",), "mid": ("mid",), "bot": ("adc", "sup")}
NOM_LANE = {"top": "Top", "jgl": "Jungle", "mid": "Mid", "bot": "Bot", "adc": "ADC", "sup": "Support"}
OBJET_LANE = {"top": "TOP_LANE", "mid": "MID_LANE", "bot": "BOT_LANE"}
MINUTE = 15
T_MAX = MINUTE * 60_000
MIN_PARTIES_CONTRE = 20
MIN_OR_CONTRE = 150
MIN_PARTIES_LISTE = 10
POOL = ("Fiddlesticks", "Ivern", "Dr. Mundo", "Kayn bleu", "Kayn rouge", "Viego", "Maokai", "Skarner")


def dossier_donnees():
    return Path(os.environ.get("PANDA_DONNEES") or lecture.DONNEES)


def nombre(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return math.nan


# --- 1. Lecture : une ligne par partie et par lane -------------------------------------------

def lire(donnees):
    avec_tl = lecture.matchs_presents("timeline_joueurs", donnees) & lecture.matchs_avec_details(donnees)
    gagnant = {}
    with open(donnees / "parties.csv", encoding="utf-8", newline="") as fichier:
        for l in csv.DictReader(fichier, delimiter=";"):
            if l["match"] in avec_tl:
                gagnant[l["match"]] = l["gagnant"]
    matchs = set(gagnant)
    joueurs = {}                                   # (match, participant) -> (equipe, poste, champion)
    for j in lecture.lire_details("joueurs", donnees, matchs=matchs):
        joueurs[(j["match"], int(j["participant"]))] = (j["equipe"], j["poste"], j["champion"])
    tl = {}
    for t in lecture.lire_details("timeline_joueurs", donnees, matchs=matchs):
        tl[(t["match"], int(t["participant"]))] = (nombre(t[f"or_{MINUTE}"]), nombre(t[f"xp_{MINUTE}"]))
    kda = defaultdict(float)                       # (match, participant) -> kills + assistances - morts avant 15 min
    plaques = defaultdict(int)                     # (match, lane, equipe) -> plaques prises
    tours = {}                                     # (match, lane) -> équipe qui a détruit la première tour extérieure
    for e in lecture.lire_details("evenements", donnees, matchs=matchs):
        t = nombre(e["t_ms"])
        if not t < T_MAX:
            continue
        m = e["match"]
        if e["type"] == "CHAMPION_KILL":
            if e["participant"] not in ("", "0"):
                kda[(m, int(e["participant"]))] += 1
            for a in (e["assistants"] or "").split("|"):
                if a:
                    kda[(m, int(a))] += 1
            if e["victime"]:
                kda[(m, int(e["victime"]))] -= 1
        elif e["type"] == "TURRET_PLATE_DESTROYED":
            plaques[(m, e["detail"], e["equipe"])] += 1
        elif e["type"] == "BUILDING_KILL" and "OUTER_TURRET" in e["detail"]:
            lane = e["detail"].rsplit("/", 1)[-1]
            if (m, lane) not in tours or t < tours[(m, lane)][0]:
                tours[(m, lane)] = (t, e["equipe"])

    par_match = defaultdict(dict)                  # match -> {(equipe, poste): participant}
    for (m, p), (equipe, poste, _) in joueurs.items():
        par_match[m][(equipe, poste)] = p
    lignes = {lane: [] for lane in LANES}
    for m, places in par_match.items():
        if len(places) != 10:
            continue
        for lane, postes in LANES.items():
            ligne = {"match": m, "bleu_gagne": 1.0 if gagnant[m] == "b" else 0.0}
            ok = True
            for cote in "br":
                for poste in postes:
                    p = places.get((cote, poste))
                    if p is None or (m, p) not in tl:
                        ok = False
                        break
                    ligne[f"{cote}_{poste}"] = joueurs[(m, p)][2]
                if not ok:
                    break
            if not ok:
                continue
            for mesure, i in (("or", 0), ("xp", 1)):
                vals = {c: sum(tl[(m, places[(c, poste)])][i] for poste in postes) for c in "br"}
                ligne[mesure] = vals["b"] - vals["r"]
            ligne["kda"] = sum(kda[(m, places[("b", poste)])] - kda[(m, places[("r", poste)])] for poste in postes)
            objet = OBJET_LANE.get(lane)
            ligne["plaques"] = plaques[(m, objet, "b")] - plaques[(m, objet, "r")] if objet else math.nan
            premiere = tours.get((m, objet)) if objet else None
            ligne["tour"] = (1.0 if premiere[1] == "b" else -1.0) if premiere else (0.0 if objet else math.nan)
            if not math.isnan(ligne["or"]):
                lignes[lane].append(ligne)
    return lignes, matchs


# --- 2. Le modèle ---------------------------------------------------------------------------

def ridge(X, y, lam):
    p = X.shape[1]
    pen = np.full(p, lam)
    pen[0] = 1e-6
    return np.linalg.solve(X.T @ X + np.diag(pen), X.T @ y)


def forces_de_lane(lignes, postes):
    """Force de lane (en or) de chaque champion à chaque poste de la lane, plus l'avantage du côté bleu."""
    cles = sorted({(l[f"{c}_{p}"], p) for l in lignes for c in "br" for p in postes})
    col = {k: i + 1 for i, k in enumerate(cles)}
    X = np.zeros((len(lignes), len(cles) + 1))
    X[:, 0] = 1
    for i, l in enumerate(lignes):
        for p in postes:
            X[i, col[(l[f"b_{p}"], p)]] += 1
            X[i, col[(l[f"r_{p}"], p)]] -= 1
    y = np.array([l["or"] for l in lignes])
    pli = np.arange(len(y)) % 5
    np.random.default_rng(0).shuffle(pli)
    meilleur = None
    for lam in (3.0, 10.0, 30.0, 100.0, 300.0):
        err = 0.0
        for f in range(5):
            b = ridge(X[pli != f], y[pli != f], lam)
            err += float(((y[pli == f] - X[pli == f] @ b) ** 2).sum())
        if meilleur is None or err < meilleur[0]:
            meilleur = (err, lam)
    beta = ridge(X, y, meilleur[1])
    residu = y - X @ beta
    forces = {k: float(beta[col[k]]) for k in cles}
    comptes = defaultdict(int)
    for l in lignes:
        for c in "br":
            for p in postes:
                comptes[(l[f"{c}_{p}"], p)] += 1
    return forces, float(beta[0]), residu, comptes, meilleur[1]


def effets_de_paires(lignes, residu, poste):
    """Effet propre de chaque paire (A, B) au même poste, vu de A, rétréci selon le nombre de parties."""
    groupes = defaultdict(list)
    for l, r in zip(lignes, residu):
        a, b = l[f"b_{poste}"], l[f"r_{poste}"]
        if a == b:
            continue
        groupes[(a, b)].append((r, l, +1))
        groupes[(b, a)].append((-r, l, -1))
    sigma2 = float(np.var(residu))
    # Variance des vraies paires (méthode des moments) : dispersion des moyennes moins le bruit attendu.
    moyennes = [(np.mean([x for x, _, _ in v]), len(v)) for v in groupes.values() if len(v) >= 20]
    if len(moyennes) >= 10:
        m = np.array([x for x, _ in moyennes]); n = np.array([k for _, k in moyennes])
        tau2 = max(float(np.average(m ** 2, weights=n) - np.mean(sigma2 / n)), sigma2 / 1000)
    else:
        tau2 = sigma2 / 1000
    k = sigma2 / tau2
    sortie = {}
    for (a, b), v in groupes.items():
        x = np.array([e[0] for e in v])
        n = len(x)

        def moyenne(cle):
            vals = [e[2] * e[1][cle] for e in v if not math.isnan(e[1][cle])]
            return float(np.mean(vals)) if vals else math.nan

        sortie[(a, b)] = {"parties": n, "specifique": float(x.sum() / (n + k)), "erreur": math.sqrt(sigma2 / (n + k)),
                          "or_brut": moyenne("or"), "xp_brut": moyenne("xp"), "kda": moyenne("kda"),
                          "plaques": moyenne("plaques"), "tour": moyenne("tour"),
                          "victoires_brut": float(np.mean([l["bleu_gagne"] if s > 0 else 1 - l["bleu_gagne"] for _, l, s in v]))}
    return sortie, k, tau2, sigma2


def fiabilite(lignes, residu, poste):
    """Accord entre deux moitiés des parties sur l'effet propre des paires (corrélation, paires vues
    au moins 15 fois dans chaque moitié). Proche de 0 : les effets propres sont surtout du bruit."""
    moities = [defaultdict(list), defaultdict(list)]
    for i, (l, r) in enumerate(zip(lignes, residu)):
        a, b = l[f"b_{poste}"], l[f"r_{poste}"]
        if a == b:
            continue
        cle, signe = ((a, b), 1) if a < b else ((b, a), -1)
        moities[int(l["match"]) % 2][cle].append(signe * r)
    communes = [c for c in moities[0] if len(moities[0][c]) >= 15 and len(moities[1].get(c, [])) >= 15]
    if len(communes) < 10:
        return math.nan, len(communes)
    x = [np.mean(moities[0][c]) for c in communes]
    y = [np.mean(moities[1][c]) for c in communes]
    return float(np.corrcoef(x, y)[0, 1]), len(communes)


def pente_victoire(lignes):
    """Victoires en fonction de l'écart d'or de la lane (logistique à une variable, en milliers d'or)."""
    x = np.array([l["or"] for l in lignes]) / 1000
    y = np.array([l["bleu_gagne"] for l in lignes])
    b = np.zeros(2)
    X = np.column_stack([np.ones_like(x), x])
    for _ in range(25):
        mu = 1 / (1 + np.exp(-(X @ b)))
        h = (X * (mu * (1 - mu))[:, None]).T @ X
        b += np.linalg.solve(h, X.T @ (y - mu))
    return float(b[1])


def victoire(or_, pente):
    return 1 / (1 + math.exp(-pente * or_ / 1000))


# --- 3. Sorties -----------------------------------------------------------------------------

def statut(e):
    if e["parties"] < MIN_PARTIES_CONTRE:
        return "pas assez de parties"
    if abs(e["specifique"]) >= MIN_OR_CONTRE and abs(e["specifique"]) >= 2 * e["erreur"]:
        return "contre identifié"
    if abs(e["specifique"]) >= 2 * e["erreur"]:
        return "petit effet propre"
    return "pas d'effet propre"


def analyser(lignes):
    sortie = {}
    for lane, postes in LANES.items():
        l = lignes[lane]
        if len(l) < 500:
            continue
        forces, cote_bleu, residu, comptes, lam = forces_de_lane(l, postes)
        pente = pente_victoire(l)
        for poste in postes:
            paires, k, tau2, sigma2 = effets_de_paires(l, residu, poste)
            r, nb = fiabilite(l, residu, poste)
            for (a, b), e in paires.items():
                e["force_A"] = forces.get((a, poste), 0.0)
                e["force_B"] = forces.get((b, poste), 0.0)
                e["total"] = e["force_A"] - e["force_B"] + e["specifique"]
                e["victoire_estimee"] = victoire(e["total"], pente)
                e["statut"] = statut(e)
            sortie[poste] = {"lane": lane, "parties": len(l), "paires": paires, "k": k, "ecart_type_paires": math.sqrt(tau2),
                             "ecart_type_residu": math.sqrt(sigma2), "fiabilite": r, "paires_fiabilite": nb, "pente": pente,
                             "forces": {c: v for (c, p), v in forces.items() if p == poste},
                             "comptes": {c: n for (c, p), n in comptes.items() if p == poste}, "lambda": lam}
    return sortie


def charger_etat():
    chemin = RESULTATS / "etat.json"
    return json.loads(chemin.read_text(encoding="utf-8")) if chemin.exists() else {"contres": {}, "parties": 0}


def charger_connues():
    chemin = RESULTATS / "parties_connues.txt.gz"
    if not chemin.exists():
        return set()
    with gzip.open(chemin, "rt", encoding="utf-8") as f:
        return {l.strip() for l in f if l.strip()}


def signe(x):
    return f"{'+' if x >= 0 else '−'}{abs(x):.0f}"


def ecrire(sortie, matchs, connues, etat):
    RESULTATS.mkdir(parents=True, exist_ok=True)
    date = datetime.now(timezone.utc).astimezone().strftime("%d/%m/%Y %H:%M")
    nouvelles = len(matchs - connues)
    contres_actuels = {}
    for poste, s in sortie.items():
        with open(RESULTATS / f"contres_{poste}.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter=";", lineterminator="\n")
            w.writerow(["champion", "adversaire", "parties", "resultat_or_15", "victoire_estimee", "force_lane_champion",
                        "force_lane_adversaire", "effet_propre", "marge_erreur", "statut", "or_brut", "xp_brut",
                        "solde_kills", "plaques", "premiere_tour", "victoires_brut"])
            for (a, b), e in sorted(s["paires"].items(), key=lambda kv: (kv[0][0], -kv[1]["total"])):
                if e["parties"] < MIN_PARTIES_LISTE:
                    continue
                w.writerow([a, b, e["parties"], f"{e['total']:.0f}", f"{e['victoire_estimee']:.4f}", f"{e['force_A']:.0f}",
                            f"{e['force_B']:.0f}", f"{e['specifique']:.0f}", f"{e['erreur']:.0f}", e["statut"],
                            f"{e['or_brut']:.0f}", f"{e['xp_brut']:.0f}", f"{e['kda']:.2f}",
                            "" if math.isnan(e["plaques"]) else f"{e['plaques']:.2f}",
                            "" if math.isnan(e["tour"]) else f"{e['tour']:.2f}", f"{e['victoires_brut']:.4f}"])
                if e["statut"] == "contre identifié" and e["specifique"] > 0:
                    contres_actuels[f"{poste}|{a}|{b}"] = round(e["specifique"])
        with open(RESULTATS / f"forces_{poste}.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter=";", lineterminator="\n")
            w.writerow(["champion", "parties", "force_lane_or_15"])
            for c, v in sorted(s["forces"].items(), key=lambda kv: -kv[1]):
                w.writerow([c, s["comptes"].get(c, 0), f"{v:.0f}"])

    anciens = etat.get("contres", {})
    apparus = sorted(set(contres_actuels) - set(anciens))
    disparus = sorted(set(anciens) - set(contres_actuels))
    lignes = [f"# Les contres par lane ({date})", "",
              f"- {len(matchs)} parties avec timeline, dont **{nouvelles} que l'outil ne connaissait pas** au passage précédent.",
              f"- Mesure principale : l'écart d'or à {MINUTE} min entre les deux joueurs de la lane (le duo ADC + support en bot).",
              "- **Résultat** = force de lane du champion − celle de l'adversaire + effet propre de la paire. "
              "**Contre identifié** : un effet propre d'au moins 150 or, à plus de deux marges d'erreur de zéro, sur 20 parties ou plus.",
              "- Victoire estimée : ce que l'écart d'or de la lane donne en victoires, en moyenne.", "",
              "## Fiabilité", "",
              "| Poste | Parties | Paires (≥ 20 parties) | Contres identifiés | Accord entre deux moitiés des parties | 1 000 or à 15 min = |",
              "|---|---|---|---|---|---|"]
    for poste, s in sortie.items():
        nb20 = sum(e["parties"] >= MIN_PARTIES_CONTRE for e in s["paires"].values()) // 2
        nbc = sum(1 for k in contres_actuels if k.startswith(poste + "|"))
        fia = "—" if math.isnan(s["fiabilite"]) else f"{s['fiabilite']:.2f} ({s['paires_fiabilite']} paires)"
        lignes.append(f"| {NOM_LANE[poste]} | {s['parties']} | {nb20} | {nbc} | {fia} | "
                      f"{100 * (victoire(1000, s['pente']) - 0.5):+.1f} points de victoire |")
    lignes += ["", "L'accord entre moitiés mesure si les effets propres des paires se retrouvent d'une moitié des parties "
               "à l'autre (1 = parfaitement, 0 = du bruit).", ""]
    lignes += ["## Changements depuis le passage précédent", ""]
    if not anciens:
        lignes.append("- Premier passage.")
    else:
        lignes += [f"- Nouveau contre : {k.split('|')[1]} contre {k.split('|')[2]} ({NOM_LANE[k.split('|')[0]]}, "
                   f"{signe(contres_actuels[k])} or)" for k in apparus] or ["- Aucun nouveau contre."]
        lignes += [f"- Ne passe plus le seuil : {k.split('|')[1]} contre {k.split('|')[2]} ({NOM_LANE[k.split('|')[0]]})"
                   for k in disparus]
    lignes.append("")
    for poste, s in sortie.items():
        contres = sorted([(k, e) for k, e in s["paires"].items() if e["statut"] == "contre identifié" and e["specifique"] > 0],
                         key=lambda kv: -kv[1]["specifique"])
        lignes += [f"## {NOM_LANE[poste]} : contres identifiés ({len(contres)})", ""]
        if contres:
            lignes += ["| Champion | contre | Parties | Effet propre (or à 15 min) | Résultat total | Victoire estimée |", "|---|---|---|---|---|---|"]
            lignes += [f"| {a} | {b} | {e['parties']} | {signe(e['specifique'])} ± {e['erreur']:.0f} | {signe(e['total'])} | "
                       f"{100 * e['victoire_estimee']:.1f} % |" for (a, b), e in contres[:20]]
        else:
            lignes.append("Aucun pour l'instant.")
        lignes.append("")
    if "jgl" in sortie:
        s = sortie["jgl"]
        lignes += ["## Ton pool en jungle : écart d'or attendu à 15 min contre chaque jungler adverse (20 parties ou plus)", "",
                   "Positif : ton jungler finit en général devant à 15 min. La force de lane est l'écart moyen contre un jungler quelconque.", ""]
        for c in POOL:
            paires = sorted([(b, e) for (a, b), e in s["paires"].items() if a == c and e["parties"] >= MIN_PARTIES_CONTRE],
                            key=lambda kv: -kv[1]["total"])
            if not paires:
                lignes.append(f"- **{c}** : pas encore assez de parties par adversaire.")
                continue
            if len(paires) <= 6:
                duels = ", ".join(f"{b} {signe(e['total'])}" for b, e in paires)
                lignes.append(f"- **{c}** (force de lane {signe(s['forces'].get(c, 0))} or) : {duels}.")
                continue
            fort = ", ".join(f"{b} {signe(e['total'])}" for b, e in paires[:3])
            faible = ", ".join(f"{b} {signe(e['total'])}" for b, e in paires[::-1][:3])
            lignes.append(f"- **{c}** (force de lane {signe(s['forces'].get(c, 0))} or) : meilleurs duels {fort} ; "
                          f"pires duels {faible}.")
        lignes.append("")
    (RESULTATS / "contres.md").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    with gzip.open(RESULTATS / "parties_connues.txt.gz", "wt", encoding="utf-8") as f:
        f.write("\n".join(sorted(matchs)) + "\n")
    (RESULTATS / "etat.json").write_text(json.dumps({"date": date, "parties": len(matchs), "contres": contres_actuels},
                                                    ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return nouvelles, len(contres_actuels)


def main():
    donnees = dossier_donnees()
    lignes, matchs = lire(donnees)
    sortie = analyser(lignes)
    nouvelles, nb = ecrire(sortie, matchs, charger_connues(), charger_etat())
    print(f"Contres : {len(matchs)} parties avec timeline ({nouvelles} nouvelles), {nb} contres identifiés. "
          f"Résumé dans {RESULTATS / 'contres.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
