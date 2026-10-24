"""Bloc 2 : le type de chaque compo, à partir du catalogue à l'instant T (bloc 1).

Pour une équipe, chaque groupe du catalogue reçoit un score :
    score[g] = somme sur les 5 postes de  poids_poste × (1 si le champion est du groupe g
               + poids_secondaire si g est son groupe secondaire)
La part d'un groupe = score[g] / somme des poids des postes.
- Type de la compo = le groupe de plus forte part, si cette part atteint le « seuil » ; sinon « Mixte ».
- Le jungler garde toujours son propre groupe (poids de la jungle au moins 0,5, et le bloc 3 regarde
  le groupe du jungler à part).
- Capacités de l'équipe : moyenne pondérée par poste du CC, du front et de la part magique.

Paramètres variables (recuit) : poids de chaque poste, poids du secondaire, seuil.
Avec les poids à 1, le secondaire à 0,5 et le seuil à 0,3, c'est l'équivalent de la règle actuelle
(regle.py : 2 points en principal, 1 en secondaire, style de compo à partir de 3 points).
"""

from dataclasses import dataclass

POSTES = ("top", "jgl", "mid", "adc", "sup")
CAPACITES = ("cc", "front", "magique")


@dataclass
class Compos:
    noms: list            # noms des types de compo (groupes du catalogue + « Mixte »)
    type_b: object        # type de la compo bleue, par partie (indice dans noms)
    type_r: object
    jgl_b: object         # groupe du jungler bleu (-1 si champion inconnu)
    jgl_r: object
    cap_b: object         # capacités de l'équipe bleue (parties × 3)
    cap_r: object
    noms_groupes: list    # noms des groupes du catalogue (pour le jungler)


class Index:
    """Champions des parties sous forme de tableaux (calculé une fois, réutilisé à chaque itération)."""

    def __init__(self, table):
        import numpy as np

        self.champions = sorted({c for cote in "br" for p in POSTES for c in table[f"{cote}_{p}"]})
        indice = {c: i for i, c in enumerate(self.champions)}
        self.equipes = {cote: np.column_stack([table[f"{cote}_{p}"].map(indice).to_numpy() for p in POSTES])
                        for cote in "br"}
        self.y = table["bleu_gagne"].to_numpy(dtype=float)
        self.n = len(table)


def construire(cat, index, params):
    import numpy as np

    k = cat.k
    groupe = np.array([cat.groupe.get(c, -1) for c in index.champions])
    secondaire = np.array([cat.secondaire.get(c, -1) for c in index.champions])
    cap = np.array([cat.capacites.get(c, (0.0, 0.0, 0.5)) for c in index.champions])
    poids = np.array([params["roles"][p] for p in POSTES])
    somme = poids.sum()
    sortie = {}
    for cote in "br":
        e = index.equipes[cote]
        score = np.zeros((index.n, k))
        for r in range(5):
            g = groupe[e[:, r]]
            ok = g >= 0
            score[np.where(ok)[0], g[ok]] += poids[r]
            s = secondaire[e[:, r]]
            ok = s >= 0
            score[np.where(ok)[0], s[ok]] += poids[r] * params["poids_secondaire"]
        part = score / somme
        meilleur = part.argmax(axis=1)
        typ = np.where(part.max(axis=1) >= params["seuil"], meilleur, k)
        capacites = (cap[e] * poids[None, :, None]).sum(axis=1) / somme
        sortie[cote] = (typ, groupe[e[:, 1]], capacites)
    return Compos(noms=list(cat.noms) + ["Mixte"], type_b=sortie["b"][0], type_r=sortie["r"][0],
                  jgl_b=sortie["b"][1], jgl_r=sortie["r"][1], cap_b=sortie["b"][2], cap_r=sortie["r"][2],
                  noms_groupes=list(cat.noms))
