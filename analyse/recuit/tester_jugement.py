"""Le jugement sur B d'un recuit n° 2 est-il meilleur que le hasard ?

On garde le meilleur réglage du recuit, FIXE, et on refait n fois : victoires de A et B tirées au sort
selon la seule force des champions (aucun biais de compo), apprentissage sur A, jugement sur B.
On compare le vrai jugement à ces n jugements « au hasard ».

    python3 analyse/recuit/tester_jugement.py recuit2_teamfight_20261024_0045.json 40
"""
import json, sys
import numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import recuit_pistes as rp  # ajoute aussi base/ au chemin
import commun, bloc2_compos as bloc2, bloc3_biais as bloc3
fichier, n_sim = sys.argv[1], int(sys.argv[2])
R = rp.RESULTATS
recuit = json.load(open(R / fichier)); piste = recuit["piste"]
params = recuit["palmares"][0]["parametres"]
regle = commun.lire_decoupage()
table = commun.drafts(regle); table = table[table["tas"].isin(["A", "B"])].reset_index(drop=True)
cat = rp.lire_catalogue()
m = rp.Machine(table, piste, cat)
reel = m.juger(params).score
print(piste, "jugement réel", round(reel, 3), "lambda", m.lam, "lambda force", m.lambda_force, flush=True)
# Victoires tirées au sort selon la seule force des champions (apprise sur A + B), réglage FIXE.
index = bloc2.Index(table); tout = np.arange(len(table))
f = bloc3.Force(index, tout); beta, c = f.apprendre(tout, m.lambda_force)
proba = bloc3.sigmoide(f.matrice(tout) @ beta + c)
bloc3.LAMBDAS_FORCE = (m.lambda_force,); rp.LAMBDAS = (m.lam,)
sims = []
for s in range(n_sim):
    t = table.copy(); t["bleu_gagne"] = (np.random.default_rng(5000 + s).random(len(t)) < proba).astype(int)
    ms = rp.Machine(t, piste, cat)
    sims.append(ms.juger(params).score)
sims = np.array(sims)
print(piste, "hasard : moyenne %.3f, écart-type %.3f, max %.3f ; part >= réel : %d / %d" % (sims.mean(), sims.std(ddof=1), sims.max(), (sims >= reel).sum(), n_sim))
sortie = R / fichier.replace(".json", "_test_jugement.json")
sortie.write_text(json.dumps({"recuit": fichier, "piste": piste, "jugement_reel": reel, "jugements_hasard": sims.tolist(),
    "part_hasard_au_moins_aussi_bon": float((sims >= reel).mean())}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
