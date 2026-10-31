"""Surcouche en jeu : une petite fenêtre par-dessus League of Legends, lancée par le lien client.

Ce qu'elle affiche, sur le bord droit de l'écran (déplaçable en tirant son bandeau du haut) :
- le prochain dragon (ou le Dragon ancien après une âme) et le Héraut, avec un bip 1 min 30 avant ;
- pour chaque champion adverse : l'or de ses objets, son Saut éclair et son Sablier de Zhonya s'il en a un.
  Clic gauche sur « F » ou « Z » quand il l'utilise : le compte à rebours démarre ; reclic : remis à zéro.

D'où viennent les informations : l'interface officielle de Riot pendant une partie (« Live Client Data API »,
https://127.0.0.1:2999, sur ton PC seulement). Elle donne le temps de jeu, les objets et sorts de chaque champion
(ce que montre le tableau des scores), et les dragons et Hérauts tués (ce qu'annonce le jeu à tout le monde).
Elle ne dit pas quand un ennemi utilise un sort : c'est le clic. Rien n'est lu dans la mémoire du jeu, rien n'est
envoyé au jeu.

Les recharges tiennent compte de la hâte des invocateurs (Bottes de lucidité ioniennes, Lucidité pourpre, lues dans
ses objets ; Perspicacité cosmique, supposée dès qu'il a l'arbre Inspiration, marquée « ✦ », car le jeu ne donne
pas les petites runes des autres), et on retire une marge de 10 secondes (le temps de cliquer). Les valeurs du patch
viennent de lolalytics/valeurs_jeu.json (branche scraping), téléchargé au lancement et gardé en copie.

Le jeu doit être en « Fenêtré sans bordure » : une fenêtre ne peut pas s'afficher par-dessus le plein écran.
"""

import json
import ssl
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

API_JEU = "https://127.0.0.1:2999/liveclientdata/allgamedata"
URL_VALEURS = "https://raw.githubusercontent.com/LeCoonEtSaBande/panda/scraping/lolalytics/valeurs_jeu.json"
DDRAGON = "https://ddragon.leagueoflegends.com/cdn"
MARGE_S = 10            # retirée des recharges : le temps de voir le sort et de cliquer
ALERTE_AVANT_S = 90     # bip et surlignage 1 min 30 avant un objectif

# Si le fichier du patch est injoignable et qu'il n'y a pas de copie (vérifiées le 31/10/2026).
VALEURS_DEFAUT = {
    "flash_s": 300, "zhonya_s": 120, "zhonya_ids": ["3157"], "hate_invocateur_objets": {"3158": 10, "3171": 20},
    "cosmic_hate_invocateur": 18, "cosmic_hate_objets": 10, "cosmic_id": 8347, "inspiration_id": 8300,
    "dragon_premier_s": 300, "dragon_reapparition_s": 300, "ancien_reapparition_s": 360,
    "heraut_apparition_s": 900, "heraut_disparition_s": 1185, "prix_objets": {}, "version_ddragon": "", "patch": "",
}

CONTEXTE_LOCAL = ssl.create_default_context()
CONTEXTE_LOCAL.check_hostname = False            # certificat de Riot pour 127.0.0.1 : on ne parle qu'à son PC
CONTEXTE_LOCAL.verify_mode = ssl.CERT_NONE


# --- Calculs (sans fenêtre, testés) ---------------------------------------------------------------------

def recharge(base, hate, marge=MARGE_S):
    """Recharge réelle avec la hâte (base × 100 / (100 + hâte)), moins la marge de sécurité."""
    return max(0.0, base * 100.0 / (100.0 + hate) - marge)


def id_champion(joueur):
    """Identifiant Data Dragon du champion (« MonkeyKing » pour Wukong), pour son portrait."""
    brut = joueur.get("rawChampionName") or ""
    return brut.rsplit("_", 1)[-1] if "_" in brut else (joueur.get("championName") or "").replace(" ", "").replace("'", "")


def nom_joueur(j):
    return j.get("riotId") or j.get("summonerName") or j.get("riotIdGameName") or ""


def a_le_sort(joueur, motif="SummonerFlash"):
    sorts = joueur.get("summonerSpells") or {}
    return any(motif in ((sorts.get(c) or {}).get("rawDisplayName") or "") for c in ("summonerSpellOne", "summonerSpellTwo"))


def a_inspiration(joueur, valeurs):
    r = joueur.get("runes") or {}
    ident = valeurs["inspiration_id"]
    return any((r.get(c) or {}).get("id") == ident for c in ("primaryRuneTree", "secondaryRuneTree"))


def hate_invocateur(joueur, valeurs):
    """Hâte des invocateurs : objets (une paire de bottes au plus) + Perspicacité cosmique si l'arbre Inspiration est
    pris (supposée : le jeu ne donne pas les petites runes des autres ; c'est le côté prudent, le sort revient plus tôt)."""
    objets = [valeurs["hate_invocateur_objets"].get(str(o.get("itemID")), 0) for o in joueur.get("items") or []]
    return (max(objets) if objets else 0) + (valeurs["cosmic_hate_invocateur"] if a_inspiration(joueur, valeurs) else 0)


def hate_objets(joueur, valeurs):
    return valeurs["cosmic_hate_objets"] if a_inspiration(joueur, valeurs) else 0


def a_zhonya(joueur, valeurs):
    return any(str(o.get("itemID")) in valeurs["zhonya_ids"] for o in joueur.get("items") or [])


def or_objets(joueur, valeurs):
    """Or dépensé dans ses objets (prix total Data Dragon ; à défaut, le prix donné par le jeu), consommables exclus."""
    total = 0
    for o in joueur.get("items") or []:
        if o.get("consumable"):
            continue
        prix = valeurs["prix_objets"].get(str(o.get("itemID")))
        total += (prix if prix is not None else o.get("price") or 0) * max(1, o.get("count") or 1)
    return total


def format_or(x):
    return f"{x / 1000:.1f}k" if x >= 1000 else str(int(x))


def format_temps(s):
    s = max(0, int(round(s)))
    return f"{s // 60}:{s % 60:02d}"


def equipes(donnees):
    """(mon équipe, liste des adversaires, nom -> équipe) d'après les données du jeu."""
    joueurs = donnees.get("allPlayers") or []
    actif = donnees.get("activePlayer") or {}
    moi = {actif.get("riotId"), actif.get("summonerName"), actif.get("riotIdGameName")} - {None, ""}
    mon_equipe = next((j.get("team") for j in joueurs if moi & {j.get("riotId"), j.get("summonerName"), j.get("riotIdGameName")}), "ORDER")
    noms = {}
    for j in joueurs:
        for n in (j.get("riotId"), j.get("summonerName"), j.get("riotIdGameName"), j.get("championName")):
            if n:
                noms[n] = j.get("team")
    return mon_equipe, [j for j in joueurs if j.get("team") != mon_equipe], noms


def objectifs(temps, evenements, noms_equipes, valeurs):
    """[(nom, apparition en secondes de jeu ou None si fini, en vie ?)] pour le dragon et le Héraut."""
    dragons = [e for e in evenements if e.get("EventName") == "DragonKill"]
    # Âme : une équipe a tué 4 dragons élémentaires ; ensuite, la fosse ne donne plus que le Dragon ancien.
    compte, ame = {}, False
    for e in dragons:
        if e.get("DragonType") != "Elder":
            equipe = noms_equipes.get(e.get("KillerName"), "?")
            compte[equipe] = compte.get(equipe, 0) + 1
            if equipe != "?" and compte[equipe] >= 4:
                ame = True
    if sum(1 for e in dragons if e.get("DragonType") != "Elder") >= 7:      # 7 dragons : une âme forcément
        ame = True
    if not dragons:
        prochain, nom = valeurs["dragon_premier_s"], "Dragon"
    elif ame:
        prochain, nom = dragons[-1]["EventTime"] + valeurs["ancien_reapparition_s"], "Ancien"
    else:
        prochain, nom = dragons[-1]["EventTime"] + valeurs["dragon_reapparition_s"], "Dragon"
    resultat = [(nom, prochain, temps >= prochain)]
    heraut_tue = any(e.get("EventName") == "HeraldKill" for e in evenements)
    if heraut_tue or temps >= valeurs["heraut_disparition_s"]:
        resultat.append(("Héraut", None, False))
    else:
        resultat.append(("Héraut", valeurs["heraut_apparition_s"], temps >= valeurs["heraut_apparition_s"]))
    return resultat


class Suivi:
    """Les comptes à rebours lancés au clic, en temps de jeu (la pause et les ralentissements ne les faussent pas)."""

    def __init__(self):
        self.debuts = {}            # (champion, "F" ou "Z") -> temps de jeu du clic
        self.partie = None

    def nouvelle_partie(self, cle):
        if cle != self.partie:
            self.partie, self.debuts = cle, {}

    def basculer(self, champion, sort, temps, fin_restante):
        """Clic : démarre le compte à rebours, ou le remet à zéro s'il tourne encore."""
        cle = (champion, sort)
        if cle in self.debuts and fin_restante is not None and fin_restante > 0:
            del self.debuts[cle]
        else:
            self.debuts[cle] = temps

    def restant(self, champion, sort, temps, duree):
        """Secondes restantes (la durée est recalculée à chaque fois : des bottes achetées entre-temps comptent)."""
        debut = self.debuts.get((champion, sort))
        if debut is None:
            return None
        reste = debut + duree - temps
        if reste <= 0:
            del self.debuts[(champion, sort)]
            return None
        return reste


# --- Valeurs du patch et portraits ------------------------------------------------------------------------

def charger_valeurs(dossier):
    """Valeurs du patch : téléchargées (et copiées dans le dossier), sinon la copie, sinon les valeurs par défaut."""
    copie = dossier / "surcouche_valeurs.json"
    valeurs = dict(VALEURS_DEFAUT)
    try:
        with urllib.request.urlopen(URL_VALEURS, timeout=8) as r:
            lues = json.load(r)
        copie.write_text(json.dumps(lues, ensure_ascii=False), encoding="utf-8")
    except (urllib.error.URLError, OSError, ValueError):
        try:
            lues = json.loads(copie.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            lues = {}
    valeurs.update({k: v for k, v in lues.items() if k in VALEURS_DEFAUT and v not in (None, "")})
    if not valeurs["prix_objets"] and valeurs["version_ddragon"]:
        try:      # prix absents du fichier : directement dans Data Dragon
            with urllib.request.urlopen(f"{DDRAGON}/{valeurs['version_ddragon']}/data/en_US/item.json", timeout=8) as r:
                valeurs["prix_objets"] = {k: o["gold"]["total"] for k, o in json.load(r)["data"].items()}
        except (urllib.error.URLError, OSError, ValueError, KeyError):
            pass
    return valeurs


def portrait(dossier, version, champion):
    """Chemin du portrait du champion (téléchargé une fois), ou None."""
    if not version or not champion:
        return None
    cache = dossier / "surcouche_portraits"
    chemin = cache / f"{champion}.png"
    if not chemin.exists():
        try:
            cache.mkdir(exist_ok=True)
            with urllib.request.urlopen(f"{DDRAGON}/{version}/img/champion/{champion}.png", timeout=5) as r:
                chemin.write_bytes(r.read())
        except (urllib.error.URLError, OSError):
            return None
    return chemin


def lire_jeu():
    """Données de la partie en cours, ou None hors partie."""
    try:
        with urllib.request.urlopen(API_JEU, context=CONTEXTE_LOCAL, timeout=2) as r:
            donnees = json.load(r)
        return donnees if donnees.get("allPlayers") else None
    except (urllib.error.URLError, OSError, ValueError):
        return None


# --- La fenêtre -------------------------------------------------------------------------------------------

FOND, TEXTE, GRIS, VERT, ORANGE, ROUGE, OR = "#14161a", "#e8e8e8", "#7d8590", "#4ade80", "#fb923c", "#f87171", "#facc15"


def bip():
    try:
        import winsound
        winsound.Beep(880, 150)
        winsound.Beep(1175, 200)
    except (ImportError, RuntimeError):
        pass


class Fenetre:
    def __init__(self, dossier):
        import tkinter as tk
        self.tk, self.dossier = tk, dossier
        self.valeurs = charger_valeurs(dossier)
        self.suivi = Suivi()
        self.donnees, self.temps_lu, self.verrou = None, 0.0, threading.Lock()
        self.alertes_faites, self.lignes, self.images = set(), [], {}
        self.position_fichier = dossier / "surcouche_position.json"

        self.racine = tk.Tk()
        self.racine.withdraw()
        self.racine.title("Panda")
        self.racine.overrideredirect(True)
        self.racine.attributes("-topmost", True)
        try:
            self.racine.attributes("-alpha", 0.88)
        except tk.TclError:
            pass
        self.racine.configure(bg=FOND)
        police = ("Segoe UI", 9)
        self.police, self.police_gras = police, ("Segoe UI", 9, "bold")

        self.bandeau = tk.Label(self.racine, text="", bg=FOND, fg=TEXTE, font=self.police_gras, anchor="w", padx=6, pady=3)
        self.bandeau.pack(fill="x")
        self.ligne_or = tk.Label(self.racine, text="", bg=FOND, fg=GRIS, font=police, anchor="w", padx=6)
        self.ligne_or.pack(fill="x")
        self.cadre = tk.Frame(self.racine, bg=FOND, padx=4, pady=3)
        self.cadre.pack(fill="both")
        for w in (self.bandeau, self.ligne_or):           # déplacer la fenêtre en tirant le haut
            w.bind("<ButtonPress-1>", self._debut_glisser)
            w.bind("<B1-Motion>", self._glisser)
            w.bind("<ButtonRelease-1>", self._fin_glisser)
        self._placer()
        threading.Thread(target=self._lecture, daemon=True).start()
        self.racine.after(300, self._rafraichir)

    # Position : bord droit, au tiers de la hauteur, puis là où tu l'as laissée.
    def _placer(self):
        try:
            x, y = json.loads(self.position_fichier.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            x, y = self.racine.winfo_screenwidth() - 190, int(self.racine.winfo_screenheight() * 0.30)
        self.racine.geometry(f"+{x}+{y}")

    def _debut_glisser(self, e):
        self._ecart = (e.x_root - self.racine.winfo_x(), e.y_root - self.racine.winfo_y())

    def _glisser(self, e):
        self.racine.geometry(f"+{e.x_root - self._ecart[0]}+{e.y_root - self._ecart[1]}")

    def _fin_glisser(self, _e):
        try:
            self.position_fichier.write_text(json.dumps([self.racine.winfo_x(), self.racine.winfo_y()]), encoding="utf-8")
        except OSError:
            pass

    # Lecture du jeu toutes les secondes, à part (la fenêtre ne doit jamais attendre le réseau).
    def _lecture(self):
        while True:
            d = lire_jeu()
            with self.verrou:
                self.donnees, self.temps_lu = d, time.monotonic()
            time.sleep(1.0)

    def _temps(self, donnees):
        """Temps de jeu, avancé depuis la dernière lecture pour que les comptes défilent sans à-coups."""
        base = float((donnees.get("gameData") or {}).get("gameTime") or 0)
        return base + min(1.5, time.monotonic() - self.temps_lu)

    def _image(self, champion):
        if champion not in self.images:
            chemin = portrait(self.dossier, self.valeurs.get("version_ddragon"), champion)
            try:
                self.images[champion] = self.tk.PhotoImage(file=str(chemin)).subsample(4) if chemin else None
            except self.tk.TclError:
                self.images[champion] = None
        return self.images[champion]

    def _construire(self, adversaires):
        tk = self.tk
        for w in self.cadre.winfo_children():
            w.destroy()
        self.lignes = []
        for i, j in enumerate(adversaires):
            champ = id_champion(j)
            img = self._image(champ)
            if img:
                tete = tk.Label(self.cadre, image=img, bg=FOND)
            else:
                tete = tk.Label(self.cadre, text=(j.get("championName") or "?")[:4], bg=FOND, fg=TEXTE, font=self.police, width=4)
            tete.grid(row=i, column=0, padx=(0, 4), pady=1)
            or_ = tk.Label(self.cadre, text="", bg=FOND, fg=OR, font=self.police, width=5, anchor="e")
            or_.grid(row=i, column=1)
            flash = tk.Label(self.cadre, text="", bg=FOND, font=self.police_gras, width=5, cursor="hand2")
            flash.grid(row=i, column=2, padx=2)
            flash.bind("<Button-1>", lambda _e, c=champ: self._clic(c, "F"))
            zho = tk.Label(self.cadre, text="", bg=FOND, font=self.police_gras, width=5, cursor="hand2")
            zho.grid(row=i, column=3)
            zho.bind("<Button-1>", lambda _e, c=champ: self._clic(c, "Z"))
            self.lignes.append({"champion": champ, "or": or_, "F": flash, "Z": zho})

    def _durees(self, j):
        v = self.valeurs
        return {"F": recharge(v["flash_s"], hate_invocateur(j, v)), "Z": recharge(v["zhonya_s"], hate_objets(j, v))}

    def _clic(self, champion, sort):
        with self.verrou:
            donnees = self.donnees
        if not donnees:
            return
        temps = self._temps(donnees)
        _, adversaires, _ = equipes(donnees)
        j = next((a for a in adversaires if id_champion(a) == champion), None)
        if j is None:
            return
        duree = self._durees(j)[sort]
        self.suivi.basculer(champion, sort, temps, self.suivi.restant(champion, sort, temps, duree))
        self._rafraichir(planifier=False)

    def _rafraichir(self, planifier=True):
        try:
            with self.verrou:
                donnees = self.donnees
            if not donnees:
                if self.racine.state() != "withdrawn":
                    self.racine.withdraw()
                return
            temps = self._temps(donnees)
            mon_equipe, adversaires, noms = equipes(donnees)
            cle = tuple(sorted(id_champion(j) + (j.get("team") or "") for j in donnees.get("allPlayers") or []))
            if cle != self.suivi.partie:                       # nouvelle partie : tout repart de zéro
                self.suivi.nouvelle_partie(cle)
                self.alertes_faites = set()
                self._construire(adversaires)
            if self.racine.state() == "withdrawn":
                self.racine.deiconify()
                self.racine.attributes("-topmost", True)

            # Objectifs
            morceaux, alerte = [], False
            for nom, apparition, en_vie in objectifs(temps, (donnees.get("events") or {}).get("Events") or [], noms, self.valeurs):
                if apparition is None:
                    continue
                if en_vie:
                    morceaux.append(f"{nom} dispo")
                    continue
                reste = apparition - temps
                morceaux.append(f"{nom} {format_temps(reste)}")
                if reste <= ALERTE_AVANT_S:
                    alerte = True
                    if (nom, apparition) not in self.alertes_faites:
                        self.alertes_faites.add((nom, apparition))
                        threading.Thread(target=bip, daemon=True).start()
            self.bandeau.configure(text="   ".join(morceaux) or "—", fg=ORANGE if alerte else TEXTE)

            # Or des objets des deux équipes
            nous = sum(or_objets(j, self.valeurs) for j in donnees.get("allPlayers") or [] if j.get("team") == mon_equipe)
            eux = sum(or_objets(j, self.valeurs) for j in adversaires)
            self.ligne_or.configure(text=f"Objets  nous {format_or(nous)} · eux {format_or(eux)}")

            # Chaque adversaire
            par_champion = {id_champion(j): j for j in adversaires}
            for ligne in self.lignes:
                j = par_champion.get(ligne["champion"])
                if j is None:
                    continue
                ligne["or"].configure(text=format_or(or_objets(j, self.valeurs)))
                durees = self._durees(j)
                cosmic = " ✦" if a_inspiration(j, self.valeurs) else ""
                for sort, present in (("F", a_le_sort(j)), ("Z", a_zhonya(j, self.valeurs))):
                    w = ligne[sort]
                    if not present:
                        w.configure(text="")
                        continue
                    reste = self.suivi.restant(ligne["champion"], sort, temps, durees[sort])
                    if reste is None:
                        w.configure(text=sort + (cosmic if sort == "F" else ""), fg=VERT if sort == "F" else OR)
                    else:
                        w.configure(text=format_temps(reste), fg=ROUGE if reste > 30 else ORANGE)
        finally:
            if planifier:
                self.racine.after(250, self._rafraichir)

    def lancer(self):
        self.racine.mainloop()


def lancer(dossier):
    """Ouvre la surcouche (bloque jusqu'à la fermeture). Rend False si aucune fenêtre n'est possible."""
    try:
        Fenetre(Path(dossier)).lancer()
        return True
    except Exception as e:          # pas d'écran, pas de tkinter… : le lien client continue sans surcouche
        print(f"Surcouche en jeu indisponible ({e}) : le lien client continue sans.", file=sys.stderr)
        return False


if __name__ == "__main__":
    lancer(Path(__file__).resolve().parent)
