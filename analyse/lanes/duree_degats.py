"""Mix de dégâts des équipes et compos early / late.

1. Profils des champions, à chaque poste :
   - dégâts : part physique, magique et brute, et dégâts moyens par partie (pour pondérer l'équipe : un
     support pèse moins qu'un ADC). Source : Lolalytics (page de chaque champion, profils.csv) quand elle est
     là, sinon nos parties (joueurs) ;
   - early / late : de combien le taux de victoire du champion monte (late) ou baisse (early) quand la partie
     dure 10 minutes de plus, par rapport à son propre taux moyen. Source : Lolalytics (victoires par tranche
     de durée), sinon nos parties.
2. Vérification sur nos parties (Émeraude-Diamant, découpage n° 2, A et B séparément), à force de champions égale :
   - early / late : l'écart de « pente » entre les deux équipes ; on mesure le coefficient sur A et sur B ;
     un effet qui tient a le même signe des deux côtés. Le coefficient de A + B sert à l'assistant ;
   - mix de dégâts : les équipes presque toutes physiques ou toutes magiques gagnent-elles moins ?
Écrit resultats/duree_degats.json (pour l'assistant) et resultats/duree_degats.md.

    python3 analyse/lanes/duree_degats.py [--lolalytics <dossier du patch>]
"""

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent))
sys.path.insert(0, str(ICI.parent / "contres"))
sys.path.insert(0, str(ICI.parent / "base"))

import lecture  # noqa: E402
import contres  # noqa: E402
import commun  # noqa: E402
import bloc2_compos as bloc2  # noqa: E402
import bloc3_biais as bloc3  # noqa: E402
from dynamique import RESULTATS  # noqa: E402

POSTES = ("top", "jgl", "mid", "adc", "sup")
# Tranches de durée de Lolalytics : centre de chaque tranche, en minutes (1 = moins de 15 min … 7 = plus de 40 min).
CENTRES = (13.0, 17.5, 22.5, 27.5, 32.5, 37.5, 43.0)
K_TRANCHE = 300          # rétrécissement d'une tranche vers le taux moyen du champion (en parties)
MIN_PARTIES = 300        # parties minimum d'un champion à un poste pour garder son profil Lolalytics
# Tranches de part magique de l'équipe testées (la référence est 30-70 %).
MIX = (("magique < 20 %", 0.0, 0.2), ("magique 20-30 %", 0.2, 0.3), ("magique > 70 %", 0.7, 1.01))
TRANCHES_DUREE = ((0, 20), (20, 25), (25, 30), (30, 35), (35, 40), (40, 999))


def points(b):
    return 100 * (1 / (1 + math.exp(-b)) - 0.5)


def T(minutes):
    """Durée centrée sur 30 min, en dizaines de minutes, bornée à 15-45 min."""
    return (min(max(minutes, 15.0), 45.0) - 30.0) / 10.0


def nom_lola(c):
    return "Kayn" if c in ("Kayn rouge", "Kayn bleu") else c


def pente(t, v):
    """Pente (fraction de victoire par 10 min) des tranches t/v d'un champion, par rapport à son taux moyen."""
    n = sum(t)
    if n <= 0:
        return None
    w = sum(v) / n
    xs = [T(c) for c in CENTRES]
    es = [((vb + K_TRANCHE * w) / (tb + K_TRANCHE) - w) for tb, vb in zip(t, v)]
    mx = sum(tb * x for tb, x in zip(t, xs)) / n
    sxx = sum(tb * (x - mx) ** 2 for tb, x in zip(t, xs))
    return sum(tb * (x - mx) * e for tb, x, e in zip(t, xs, es)) / sxx if sxx else None


def lire_lolalytics(dossier):
    """{(poste, champion Lolalytics): {"degats": [p, m, b], "tranches": ([t1..t7], [v1..v7])}}."""
    chemin = Path(dossier) / "profils.csv" if dossier else None
    if not chemin or not chemin.exists():
        return {}
    profils = {}
    with open(chemin, encoding="utf-8", newline="") as f:
        for l in csv.DictReader(f, delimiter=";"):
            val = {k: contres.nombre(x) for k, x in l.items() if k not in ("champion", "poste")}
            t = [val.get(f"t{i}") for i in range(1, 8)]
            v = [val.get(f"v{i}") for i in range(1, 8)]
            d = [val.get("physiques"), val.get("magiques"), val.get("bruts")]
            profils[(l["poste"], l["champion"])] = {
                "degats": d if all(x == x and x is not None for x in d) and sum(d) > 0 else None,
                "tranches": (t, v) if all(x == x and x is not None for x in t + v) and sum(t) >= MIN_PARTIES else None}
    return profils


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lolalytics", help="dossier du patch Lolalytics (avec profils.csv)")
    args = parser.parse_args()
    donnees = contres.dossier_donnees()
    table = commun.drafts(commun.lire_decoupage(), donnees)
    table = table[table["tas"].isin(["A", "B"])].reset_index(drop=True)
    duree = {}
    for r in lecture.lire_details("details_parties", donnees):
        if r["duree_s"]:
            duree[r["match"]] = float(r["duree_s"]) / 60
    index = bloc2.Index(table)
    la = np.where(table["tas"] == "A")[0]; lb = np.where(table["tas"] == "B")[0]
    force = bloc3.Force(index, la)
    dec_a, (dec_b,) = force.decalages(la, [lb])
    dec = np.zeros(len(table)); dec[la] = dec_a; dec[lb] = dec_b
    y = index.y.astype(float)
    avec_duree = np.array([m in duree for m in table["match"]])

    # --- Profils de nos parties (dégâts par champion et poste, sur A + B ; pente early/late apprise sur A) ---
    nos_degats = defaultdict(lambda: np.zeros(4))
    matchs = set(table["match"][avec_duree])
    for j in lecture.lire_details("joueurs", donnees, matchs=matchs):
        x = [contres.nombre(j[k]) for k in ("degats_physiques_champions", "degats_magiques_champions", "degats_vrais_champions")]
        if all(v == v for v in x):
            nos_degats[(j["poste"], j["champion"])] += (*x, 1)
            nos_degats[("*", j["champion"])] += (*x, 1)

    cles = {}
    for e in "br":
        for p in POSTES:
            for c in table[f"{e}_{p}"]:
                cles.setdefault((p, c), len(cles))
    sel_a = np.array([i for i in la if avec_duree[i]])
    X = np.zeros((len(sel_a), len(cles)))
    for k, i in enumerate(sel_a):
        t = T(duree[table["match"][i]])
        for p in POSTES:
            X[k, cles[(p, table[f"b_{p}"][i])]] += t
            X[k, cles[(p, table[f"r_{p}"][i])]] -= t
    beta_nos, _ = bloc3.logistique(X, y[sel_a], dec[sel_a], lam=30.0)
    nb = defaultdict(int)
    for i in sel_a:
        for e in "br":
            for p in POSTES:
                nb[(p, table[f"{e}_{p}"][i])] += 1

    # --- Profils retenus : Lolalytics d'abord, sinon nos parties ---
    lola = lire_lolalytics(args.lolalytics)
    degats, late, source = {p: {} for p in POSTES}, {p: {} for p in POSTES}, defaultdict(int)
    for (p, c) in cles:
        lp = lola.get((p, nom_lola(c)))
        if lp and lp["degats"] and c not in ("Kayn rouge", "Kayn bleu"):
            d = lp["degats"]; source["degats Lolalytics"] += 1
        else:
            x = nos_degats.get((p, c))
            if x is None or x[3] < 30:
                x = nos_degats.get(("*", c))
            if x is None or x[3] < 10:
                continue
            d = list(x[:3] / x[3]); source["degats nos parties"] += 1
        total = sum(d)
        degats[p][c] = [round(d[0] / total, 3), round(d[1] / total, 3), round(d[2] / total, 3), round(total)]
    for (p, c) in cles:
        lp = lola.get((p, nom_lola(c)))
        s = pente(*lp["tranches"]) if lp and lp["tranches"] else None
        if s is not None:
            source["late Lolalytics"] += 1
        elif nb[(p, c)] >= 100:
            s = float(beta_nos[cles[(p, c)]]) / 4; source["late nos parties"] += 1
        if s is not None:
            late[p][c] = round(s, 4)

    # --- Vérification early / late : victoire ~ force + b × (écart de pente) × durée ---
    def ecart_pente(i):
        return sum(late[p].get(table[f"b_{p}"][i], 0.0) for p in POSTES) - sum(late[p].get(table[f"r_{p}"][i], 0.0) for p in POSTES)
    S = np.array([ecart_pente(i) if avec_duree[i] else 0.0 for i in range(len(table))])
    TT = np.array([T(duree[m]) if m in duree else 0.0 for m in table["match"]])
    coef = {}
    for nom, lignes in (("A", la), ("B", lb), ("AB", np.concatenate([la, lb]))):
        lignes = np.array([i for i in lignes if avec_duree[i]])
        b, _ = bloc3.logistique((S[lignes] * TT[lignes])[:, None], y[lignes], dec[lignes], lam=1.0)
        coef[nom] = float(b[0])
    # Tableau lisible (B) : l'équipe la plus late, quand l'écart est au-dessus de la médiane.
    lb_d = np.array([i for i in lb if avec_duree[i]])
    med = float(np.median(np.abs(S[lb_d])))
    tranches = []
    for a, z in TRANCHES_DUREE:
        sel = [i for i in lb_d if abs(S[i]) > med and a <= duree[table["match"][i]] < z]
        if not sel:
            continue
        late_b = np.array([S[i] > 0 for i in sel])
        gagne = np.where(late_b, y[sel], 1 - y[sel])
        attendu = 1 / (1 + np.exp(-np.where(late_b, dec[sel], -dec[sel])))
        tranches.append({"de": a, "a": z, "parties": len(sel), "late_gagne": round(100 * float(gagne.mean()), 1),
                         "force_seule": round(100 * float(attendu.mean()), 1)})

    # --- Vérification du mix de dégâts : part magique de chaque équipe ---
    def part_magique(i, e):
        s = np.zeros(3)
        for p in POSTES:
            d = degats[p].get(table[f"{e}_{p}"][i])
            if d:
                s += np.array(d[:3]) * d[3]
        return s[1] / s.sum() if s.sum() else 0.5
    mag = {e: np.array([part_magique(i, e) for i in range(len(table))]) for e in "br"}
    Xm = np.column_stack([((mag["b"] >= a) & (mag["b"] < z)).astype(float) - ((mag["r"] >= a) & (mag["r"] < z)).astype(float)
                          for _, a, z in MIX])
    mix = {}
    for nom, lignes in (("A", la), ("B", lb), ("AB", np.concatenate([la, lb]))):
        b, _ = bloc3.logistique(Xm[lignes], y[lignes], dec[lignes], lam=5.0)
        for (titre, a, z), v in zip(MIX, b):
            mix.setdefault(titre, {"de": a, "a": min(z, 1.0)})[nom] = float(v)
    for titre, a, z in MIX:
        eq = int(sum(((mag[e] >= a) & (mag[e] < z)).sum() for e in "br"))
        m = mix[titre]
        m.update(equipes=eq, points_A=round(points(m["A"]), 1), points_B=round(points(m["B"]), 1),
                 tient=bool(m["A"] * m["B"] > 0 and min(abs(points(m["A"])), abs(points(m["B"]))) >= 1.0))

    # Coefficient retenu pour l'assistant : A + B si les pentes viennent de Lolalytics (indépendantes de nos
    # parties) ; sinon B seul, car les pentes de nos parties ont été apprises sur A (A serait trop optimiste).
    lola_d_abord = source["late Lolalytics"] >= source["late nos parties"]
    coef["retenu"] = max(0.0, coef["AB"] if lola_d_abord else coef["B"]) if coef["A"] > 0 and coef["B"] > 0 else 0.0
    sortie = {"parties": int(avec_duree.sum()), "sources": dict(source),
              "patch_lolalytics": Path(args.lolalytics).name if lola else None,
              "degats": degats, "late": late, "coef_late": coef, "tranches_B": tranches, "mix": mix}
    RESULTATS.mkdir(parents=True, exist_ok=True)
    (RESULTATS / "duree_degats.json").write_text(json.dumps(sortie, ensure_ascii=False) + "\n", encoding="utf-8")

    pts10 = lambda s: 100 * s
    tous = sorted(((s, p, c) for p in POSTES for c, s in late[p].items() if nb[(p, c)] >= 100 or lola.get((p, nom_lola(c)))),
                  key=lambda x: x[0])
    texte = ["# Mix de dégâts et compos early / late", "",
             f"- {sortie['parties']} parties avec durée (A + B, Émeraude-Diamant). Profils : "
             + ", ".join(f"{k} {v}" for k, v in sorted(source.items()))
             + (f" (Lolalytics patch {sortie['patch_lolalytics']}, Platine et plus)." if lola else "."),
             "- Pente early/late d'un champion : points de victoire gagnés (late) ou perdus (early) par 10 minutes de partie "
             "en plus, par rapport à son propre taux moyen.", "",
             "## Early / late : ça tient ?", "",
             f"- Coefficient (victoire selon l'écart de pente × durée, à force égale) : A {coef['A']:.2f}, B {coef['B']:.2f}, "
             f"A + B {coef['AB']:.2f} ; retenu pour l'assistant : {coef['retenu']:.2f}. **{'Confirmé' if coef['A'] > 0 and coef['B'] > 0 else 'Ne tient pas'}** "
             "(même signe sur A et B).",
             f"- Sur B, quand une équipe est nettement plus late que l'autre (écart de pente au-dessus de la médiane, {med:.2f}) :", "",
             "| Durée | Parties | L'équipe late gagne | Force des champions seule |", "|---|---|---|---|"]
    texte += [f"| {t['de']}-{t['a'] if t['a'] < 999 else '…'} min | {t['parties']} | {t['late_gagne']} % | {t['force_seule']} % |"
              for t in tranches]
    texte += ["", "- **Les plus early** : " + ", ".join(f"{c} ({p}) {pts10(s):+.1f}" for s, p, c in tous[:15]),
              "- **Les plus late** : " + ", ".join(f"{c} ({p}) {pts10(s):+.1f}" for s, p, c in reversed(tous[-15:])), "",
              "## Mix de dégâts : part magique de l'équipe", "",
              "Points de victoire par rapport à une équipe à 30-70 % de dégâts magiques, à force de champions égale.", "",
              "| Part magique | Équipes | A | B | Tient |", "|---|---|---|---|---|"]
    texte += [f"| {t} | {m['equipes']} | {m['points_A']:+.1f} | {m['points_B']:+.1f} | {'oui' if m['tient'] else 'non'} |"
              for t, m in mix.items()]
    texte.append("")
    (RESULTATS / "duree_degats.md").write_text("\n".join(texte) + "\n", encoding="utf-8")
    print("\n".join(texte))
    return 0


if __name__ == "__main__":
    sys.exit(main())
