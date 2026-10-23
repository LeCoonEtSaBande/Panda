"""Bloc 3 : les types de compo (bloc 2) donnent-ils des biais de victoire, à partir de la draft seule ?

1. Force des champions (une fois par tas d'apprentissage) : régression logistique sur la draft,
   un coefficient par champion à son poste (+1 côté bleu, -1 côté rouge), régularisée. C'est la
   référence : « Viego est fort » n'est pas un biais de compo.
   Pour les parties d'apprentissage, la force est estimée en validation croisée (5 plis) : une partie
   n'est jamais prédite par un modèle qui l'a vue.
2. Biais de compo, en plus de la force des champions (une ligne par partie, vue du côté bleu,
   chaque variable vaut +1 si le bleu est dans la situation, -1 si c'est le rouge) :
   - type de compo (effet propre de chaque type) ;
   - compo X contre compo Y ;
   - groupe du jungler contre type de compo adverse ;
   - groupe du jungler avec type de compo alliée ;
   - capacités (CC, front, part magique) : écart entre équipes et croisements (notre CC contre leur front...).
   Régression logistique régularisée (lambda), apprise sur A.
3. Score = ce que les biais font gagner en prédiction sur B, des parties que le modèle n'a pas vues :
   baisse de la perte logarithmique moyenne (en millièmes), sur la PIRE des deux moitiés de B. 0 = rien de plus que la force des
   champions ; plus c'est haut, plus les biais sont réels et utiles.
   On donne aussi la liste des biais, chacun avec son taux de victoire sur A et sur B.
"""

import math
from dataclasses import dataclass

import numpy as np

MIN_PARTIES_CHAMPION = 30
PLIS = 5
# Régularisation de la force des champions : choisie par validation croisée sur le tas d'apprentissage
# (sur les données du 23/10, 300 est le meilleur : moins, le modèle croit au bruit des champions rares).
LAMBDAS_FORCE = (30.0, 100.0, 300.0, 1000.0, 3000.0)


def sigmoide(x):
    return 1 / (1 + np.exp(-np.clip(x, -30, 30)))


def logistique(X, y, decalage=None, lam=1.0, constante=False, iterations=25):
    """Régression logistique régularisée (ridge), par Newton. Renvoie (coefficients, constante)."""
    n, p = X.shape
    if constante:
        X = np.column_stack([np.ones(n), X])
    decalage = np.zeros(n) if decalage is None else decalage
    beta = np.zeros(X.shape[1])
    penalite = np.full(X.shape[1], lam)
    if constante:
        penalite[0] = 1e-6
    for _ in range(iterations):
        mu = sigmoide(decalage + X @ beta)
        gradient = X.T @ (y - mu) - penalite * beta
        poids = mu * (1 - mu)
        hessienne = (X * poids[:, None]).T @ X + np.diag(penalite)
        pas = np.linalg.solve(hessienne, gradient)
        beta += pas
        if np.max(np.abs(pas)) < 1e-6:
            break
    if constante:
        return beta[1:], beta[0]
    return beta, 0.0


def benjamini_hochberg(p):
    """q-valeurs : p-valeurs corrigées pour le nombre de tests (taux de fausses découvertes)."""
    ordre = sorted(range(len(p)), key=lambda i: p[i])
    q = [1.0] * len(p)
    minimum = 1.0
    for rang in range(len(ordre), 0, -1):
        i = ordre[rang - 1]
        minimum = min(minimum, p[i] * len(p) / rang)
        q[i] = minimum
    return q


def plis(n, graine=0):
    """Numéro de pli (0 à PLIS-1) de chaque partie, au hasard mais toujours le même."""
    pli = np.arange(n) % PLIS
    np.random.default_rng(graine).shuffle(pli)
    return pli


def perte_log(y, p):
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


# --- 1. Force des champions -----------------------------------------------------------------

class Force:
    """Force de chaque champion à son poste, apprise sur un ensemble de parties."""

    def __init__(self, index, lignes):
        self.index = index
        eb, er = index.equipes["b"][lignes], index.equipes["r"][lignes]
        nb = len(index.champions)
        compte = np.zeros((5, nb))
        for r in range(5):
            np.add.at(compte[r], eb[:, r], 1)
            np.add.at(compte[r], er[:, r], 1)
        self.colonne = -np.ones((5, nb), dtype=int)
        k = 0
        for r in range(5):
            for c in np.where(compte[r] >= MIN_PARTIES_CHAMPION)[0]:
                self.colonne[r, c] = k
                k += 1
        self.p = k

    def matrice(self, lignes):
        X = np.zeros((len(lignes), self.p))
        eb, er = self.index.equipes["b"][lignes], self.index.equipes["r"][lignes]
        rangs = np.arange(len(lignes))
        for r in range(5):
            cb, cr = self.colonne[r, eb[:, r]], self.colonne[r, er[:, r]]
            ok = cb >= 0
            np.add.at(X, (rangs[ok], cb[ok]), 1.0)
            ok = cr >= 0
            np.add.at(X, (rangs[ok], cr[ok]), -1.0)
        return X

    def apprendre(self, lignes, lam):
        beta, c = logistique(self.matrice(lignes), self.index.y[lignes], lam=lam, constante=True)
        return beta, c

    def decalages(self, apprentissage, autres, pli=None):
        """Décalage (logit de la force) : en validation croisée sur `apprentissage`, et appris sur tout
        `apprentissage` pour chaque tableau de `autres`. La régularisation est choisie par la
        validation croisée sur `apprentissage` seulement."""
        apprentissage = np.asarray(apprentissage)
        if pli is None:
            pli = plis(len(apprentissage))
        y = self.index.y[apprentissage]
        meilleur = None
        for lam in LAMBDAS_FORCE:
            dec = np.zeros(len(apprentissage))
            for f in range(PLIS):
                beta, c = self.apprendre(apprentissage[pli != f], lam)
                dec[pli == f] = self.matrice(apprentissage[pli == f]) @ beta + c
            perte = perte_log(y, sigmoide(dec))
            if meilleur is None or perte < meilleur[0]:
                meilleur = (perte, lam, dec)
        _, self.lam, dec_app = meilleur
        beta, c = self.apprendre(apprentissage, self.lam)
        return dec_app, [self.matrice(np.asarray(a)) @ beta + c for a in autres]


# --- 2. Variables de biais ------------------------------------------------------------------

@dataclass
class Variable:
    genre: str
    nom: str
    a: int = -1
    b: int = -1


def caracteristiques(compos, lignes):
    """Matrice des variables de biais (antisymétriques : échanger bleu et rouge change le signe)."""
    tb, tr = compos.type_b[lignes], compos.type_r[lignes]
    jb, jr = compos.jgl_b[lignes], compos.jgl_r[lignes]
    cb, cr = compos.cap_b[lignes], compos.cap_r[lignes]
    K, G = len(compos.noms), len(compos.noms_groupes)
    colonnes, variables = [], []
    for x in range(K - 1):  # le dernier type (« Mixte ») sert de référence
        colonnes.append((tb == x).astype(float) - (tr == x))
        variables.append(Variable("type", f"Compo {compos.noms[x]}", x))
    for x in range(K):
        for y in range(x + 1, K):
            colonnes.append(((tb == x) & (tr == y)).astype(float) - ((tb == y) & (tr == x)))
            variables.append(Variable("duel", f"Compo {compos.noms[x]} contre compo {compos.noms[y]}", x, y))
    for j in range(G):
        for y in range(K):
            colonnes.append(((jb == j) & (tr == y)).astype(float) - ((jr == j) & (tb == y)))
            variables.append(Variable("jungler_adverse", f"Jungler {compos.noms_groupes[j]} contre compo {compos.noms[y]}", j, y))
            colonnes.append(((jb == j) & (tb == y)).astype(float) - ((jr == j) & (tr == y)))
            variables.append(Variable("jungler_allie", f"Jungler {compos.noms_groupes[j]} avec compo alliée {compos.noms[y]}", j, y))
    noms_cap = ("CC", "front", "magique")
    for a in range(3):
        colonnes.append(cb[:, a] - cr[:, a])
        variables.append(Variable("capacite", f"Plus de {noms_cap[a]} que l'adversaire", a))
    for a in range(3):
        for b in range(3):
            if a != b:
                colonnes.append(cb[:, a] * cr[:, b] - cr[:, a] * cb[:, b])
                variables.append(Variable("capacite_croisee", f"Notre {noms_cap[a]} contre leur {noms_cap[b]}", a, b))
    return np.column_stack(colonnes), variables


# --- 3. Score et liste des biais ------------------------------------------------------------

@dataclass
class Evaluation:
    score: float              # gain de perte log sur B, en millièmes
    score_a: float            # même chose sur A (pour voir l'écart A/B)
    biais: list               # dictionnaires, triés par force sur A
    nb_variables: int


def evaluer(compos, index, lignes_a, lignes_b, dec_a, dec_b, lam, min_parties=50, avec_biais=False):
    Xa, variables = caracteristiques(compos, lignes_a)
    Xb, _ = caracteristiques(compos, lignes_b)
    garder = (Xa != 0).sum(axis=0) >= min_parties
    Xa, Xb = Xa[:, garder], Xb[:, garder]
    variables = [v for v, g in zip(variables, garder) if g]
    ya, yb = index.y[lignes_a], index.y[lignes_b]
    beta, _ = logistique(Xa, ya, dec_a, lam=lam)
    # Score : le pire des deux moitiés de B (parties paires et impaires). Un réglage qui ne doit son
    # score qu'à un coup de chance sur une moitié est ainsi freiné.
    gains = []
    for moitie in (0, 1):
        m = np.arange(len(yb)) % 2 == moitie
        gains.append(perte_log(yb[m], sigmoide(dec_b[m])) - perte_log(yb[m], sigmoide(dec_b[m] + Xb[m] @ beta)))
    gain_b = min(gains)
    gain_a = perte_log(ya, sigmoide(dec_a)) - perte_log(ya, sigmoide(dec_a + Xa @ beta))
    biais = []
    if avec_biais:
        biais = liste_biais(variables, beta, Xa, Xb, ya, yb, dec_a, dec_b)
    return Evaluation(score=1000 * gain_b, score_a=1000 * gain_a, biais=biais, nb_variables=len(variables))


def evaluer_rotation(compos, index, lignes, pli, dec, lam, min_parties=300, avec_biais=False, lignes_a=None, lignes_b=None):
    """Score en rotation sur les parties de recherche (A + B) : 5 fois, on apprend les biais sur 4/5
    des parties et on note sur le 1/5 restant. Score = gain moyen sur les 5 cinquièmes, en millièmes.
    Toutes les parties servent ainsi à noter, ce qui rend le score bien moins sensible à la chance
    qu'avec un seul tas B fixe. `dec` : force des champions en validation croisée sur les mêmes plis."""
    X, variables = caracteristiques(compos, lignes)
    garder = (X != 0).sum(axis=0) >= min_parties
    X = X[:, garder]
    variables = [v for v, g in zip(variables, garder) if g]
    y = index.y[lignes]
    gains = []
    for f in range(PLIS):
        app, note = pli != f, pli == f
        beta, _ = logistique(X[app], y[app], dec[app], lam=lam)
        gains.append(perte_log(y[note], sigmoide(dec[note])) - perte_log(y[note], sigmoide(dec[note] + X[note] @ beta)))
    beta, _ = logistique(X, y, dec, lam=lam)
    gain_interne = perte_log(y, sigmoide(dec)) - perte_log(y, sigmoide(dec + X @ beta))
    biais = []
    if avec_biais:
        a = np.isin(lignes, lignes_a) if lignes_a is not None else np.ones(len(lignes), bool)
        b = np.isin(lignes, lignes_b) if lignes_b is not None else np.ones(len(lignes), bool)
        biais = liste_biais(variables, beta, X[a], X[b], y[a], y[b], dec[a], dec[b])
    return Evaluation(score=1000 * float(np.mean(gains)), score_a=1000 * gain_interne, biais=biais,
                      nb_variables=len(variables))


def taux_ajuste(x, y, dec):
    """Taux de victoire de la situation, ramené à des champions de force égale : 50 % + écart moyen
    entre résultat et prédiction par la force seule, vu du côté qui est dans la situation."""
    ok = x != 0
    if not ok.any():
        return float("nan"), 0, float("nan")
    signe = np.sign(x[ok])
    residu = signe * (y[ok] - sigmoide(dec[ok]))
    n = int(ok.sum())
    erreur = float(residu.std(ddof=1) / math.sqrt(n)) if n > 1 else float("nan")
    return 0.5 + float(residu.mean()), n, erreur


def liste_biais(variables, beta, Xa, Xb, ya, yb, dec_a, dec_b):
    biais = []
    for i, v in enumerate(variables):
        if v.genre.startswith("capacite"):
            ta, na, _ = float("nan"), int((Xa[:, i] != 0).sum()), None
            tb, nb, eb = float("nan"), int((Xb[:, i] != 0).sum()), float("nan")
        else:
            ta, na, _ = taux_ajuste(Xa[:, i], ya, dec_a)
            tb, nb, eb = taux_ajuste(Xb[:, i], yb, dec_b)
        biais.append({
            "genre": v.genre, "nom": v.nom, "coefficient": float(beta[i]),
            "taux_modele": float(sigmoide(np.array([beta[i]]))[0]),
            "taux_A": ta, "parties_A": na, "taux_B": tb, "parties_B": nb, "erreur_B": eb,
        })
    biais.sort(key=lambda b: -abs(b["coefficient"]))
    return biais


def phrase(b):
    """Le biais en une phrase simple."""
    if b["genre"].startswith("capacite"):
        sens = "favorable" if b["coefficient"] > 0 else "défavorable"
        return f"{b['nom']} : {sens} (environ {100 * b['taux_modele']:.1f} % pour un écart d'un cran)"
    tb = "" if b["taux_B"] != b["taux_B"] else f" ; sur B : {100 * b['taux_B']:.1f} % ({b['parties_B']} parties)"
    return (f"{b['nom']} : {100 * b['taux_A']:.1f} % sur A ({b['parties_A']} parties){tb}, "
            f"contre 50 % à force de champions égale")
