"""Surcouche en jeu : une petite fenêtre par-dessus League of Legends, lancée par le lien client.

Ce qu'elle affiche, sur le bord droit de l'écran (déplaçable en tirant son bandeau du haut) :
- le prochain dragon (ou le Dragon ancien après une âme) et le Héraut, puis le Nashor quand le Héraut n'est plus
  là, avec un bip 1 min 30 avant ;
- une ligne par poste, en vis-à-vis : à gauche l'adversaire (portrait, or de ses objets, Saut éclair, Sablier de
  Zhonya s'il en a un), à droite ton coéquipier du même poste (or de ses objets, portrait). Le plus riche des deux
  en vert, l'autre en rouge ; les deux en orange à moins de 500 d'écart. Dessous, les deux totaux.
  Clic sur l'icône du Saut éclair ou du Zhonya quand il l'utilise : l'icône devient grise avec le compte à rebours
  par-dessus ; reclic : remis à zéro. Icône en couleur : le sort est disponible.

D'où viennent les informations : l'interface officielle de Riot pendant une partie (« Live Client Data API »,
https://127.0.0.1:2999, sur ton PC seulement). Elle donne le temps de jeu, les objets et sorts de chaque champion
(ce que montre le tableau des scores), et les dragons et Hérauts tués (ce qu'annonce le jeu à tout le monde).
Elle ne dit pas quand un ennemi utilise un sort : c'est le clic. Rien n'est lu dans la mémoire du jeu, rien n'est
envoyé au jeu.

Les recharges tiennent compte de la hâte des invocateurs (Bottes de lucidité ioniennes, Lucidité pourpre, lues dans
ses objets ; Perspicacité cosmique, supposée dès qu'il a l'arbre Inspiration, marquée « ✦ », car le jeu ne donne
pas les petites runes des autres), et on retire une marge de 10 secondes (le temps de cliquer). Les valeurs du patch
viennent de lolalytics/valeurs_jeu.json (branche scraping), téléchargé au lancement et gardé en copie ; les images
(portraits, icônes) de lolalytics/images_surcouche.json, retéléchargé seulement au changement de patch. Les deux
sont préparés par le bouton « 2 · Lolalytics » : la surcouche ne va jamais elle-même sur Data Dragon.

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
URL_IMAGES = "https://raw.githubusercontent.com/LeCoonEtSaBande/panda/scraping/lolalytics/images_surcouche.json"
MARGE_S = 10            # retirée des recharges : le temps de voir le sort et de cliquer
ALERTE_AVANT_S = 90     # bip et surlignage 1 min 30 avant un objectif

# Si le fichier du patch est injoignable et qu'il n'y a pas de copie (vérifiées le 31/10/2026).
VALEURS_DEFAUT = {
    "flash_s": 300, "zhonya_s": 120, "zhonya_ids": ["3157"], "hate_invocateur_objets": {"3158": 10, "3171": 20},
    "cosmic_hate_invocateur": 18, "cosmic_hate_objets": 10, "cosmic_id": 8347, "inspiration_id": 8300,
    "dragon_premier_s": 300, "dragon_reapparition_s": 300, "ancien_reapparition_s": 360,
    "heraut_apparition_s": 900, "heraut_disparition_s": 1185,
    "baron_apparition_s": 1200, "baron_reapparition_s": 360, "prix_objets": {}, "version_ddragon": "", "patch": "",
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
    if not heraut_tue and temps < valeurs["heraut_disparition_s"]:
        resultat.append(("Héraut", valeurs["heraut_apparition_s"], temps >= valeurs["heraut_apparition_s"]))
    else:                                    # Héraut tué ou disparu : le Nashor prend sa place
        barons = [e for e in evenements if e.get("EventName") == "BaronKill"]
        apparition = barons[-1]["EventTime"] + valeurs["baron_reapparition_s"] if barons else valeurs["baron_apparition_s"]
        resultat.append(("Nashor", apparition, temps >= apparition))
    return resultat


POSTES = ("TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY")


def ranger_par_poste(joueurs):
    """Les 5 joueurs d'une équipe dans l'ordre top, jungle, mid, ADC, support (None si la place est vide).
    Poste donné par le jeu ; à défaut, le porteur de Châtiment va en jungle et les autres comblent les trous."""
    places, restants = [None] * 5, []
    for j in joueurs:
        poste = (j.get("position") or "").upper()
        if poste in POSTES and places[POSTES.index(poste)] is None:
            places[POSTES.index(poste)] = j
        else:
            restants.append(j)
    if places[1] is None:
        chatiment = next((j for j in restants if a_le_sort(j, "SummonerSmite")), None)
        if chatiment:
            places[1] = chatiment
            restants.remove(chatiment)
    for j in restants:
        if None in places:
            places[places.index(None)] = j
    return places


def vis_a_vis(donnees):
    """[(adversaire, coéquipier)] par poste, de top à support."""
    mon_equipe, adversaires, _ = equipes(donnees)
    nous = [j for j in donnees.get("allPlayers") or [] if j.get("team") == mon_equipe]
    return list(zip(ranger_par_poste(adversaires), ranger_par_poste(nous)))


def couleurs_or(eux, nous, ecart_min=500):
    """Couleurs des deux chiffres : le plus riche en vert, l'autre en rouge ; les deux en orange si l'écart est
    sous 500 ; gris si l'un des deux manque."""
    if eux is None or nous is None:
        return "gris", "gris"
    if abs(eux - nous) < ecart_min:
        return "orange", "orange"
    return ("vert", "rouge") if eux > nous else ("rouge", "vert")


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


# --- Valeurs du patch et images ------------------------------------------------------------------------

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
    return valeurs


def charger_images(dossier, patch):
    """Images de la surcouche ({côté : {« champion_Aatrox », « spell_SummonerFlash », « item_3157 »… : PNG en base64}}),
    préparées par le bouton « 2 · Lolalytics » (branche scraping). Retéléchargées seulement au changement de patch ;
    sinon la copie gardée à côté du programme."""
    copie = dossier / "surcouche_images.json"
    try:
        gardees = json.loads(copie.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        gardees = {}
    bon_format = any(c.isdigit() for c in gardees.get("images", {}))       # {côté : {image : PNG}}
    if bon_format and (not patch or gardees.get("patch") == patch):
        return gardees["images"]
    try:
        with urllib.request.urlopen(URL_IMAGES, timeout=15) as r:
            lues = json.load(r)
        copie.write_text(json.dumps(lues), encoding="utf-8")
        return lues.get("images", {})
    except (urllib.error.URLError, OSError, ValueError):
        return gardees.get("images", {})


def lire_jeu():
    """Données de la partie en cours, ou None hors partie."""
    try:
        with urllib.request.urlopen(API_JEU, context=CONTEXTE_LOCAL, timeout=2) as r:
            donnees = json.load(r)
        return donnees if donnees.get("allPlayers") else None
    except (urllib.error.URLError, OSError, ValueError):
        return None


# --- La fenêtre -------------------------------------------------------------------------------------------

# FOND est la couleur « clé » : sous Windows, tout ce qui est de cette couleur devient transparent (et laisse passer
# les clics vers le jeu). Seuls les textes, icônes et portraits restent visibles.
FOND, TEXTE, GRIS = "#010203", "#f2f2f2", "#9aa3ad"
COULEURS = {"vert": "#4ade80", "rouge": "#f87171", "orange": "#fb923c", "gris": "#7d8590"}
EUX, NOUS = "#ef4444", "#3b82f6"          # rouge : l'équipe adverse ; bleu : la tienne
# Tailles pour un écran de 1080 pixels de haut, comme le tableau des scores du jeu ; proportionnelles au-delà.
HAUTEUR_REF, PORTRAIT_REF, ICONE_REF, TEXTE_REF = 1080, 18, 16, 10
# Zones du jeu à ne jamais couvrir (fractions de la hauteur de l'écran) : en haut, le bandeau des scores et le chrono
# de la partie ; en bas à droite, la minimap. La fenêtre reste entre les deux. Par défaut, elle se cale en haut à
# droite, juste sous le bandeau des scores et au-dessus du fil des kills (qui commence vers 17 % de la hauteur).
HAUT_LIBRE, BAS_LIBRE, FIL_DES_KILLS = 0.045, 0.70, 0.175


def borner(x, y, largeur, hauteur, ecran_l, ecran_h):
    """Position gardée dans l'écran, sous le chrono et au-dessus de la minimap."""
    x = min(max(0, x), max(0, ecran_l - largeur))
    haut, bas = round(ecran_h * HAUT_LIBRE), round(ecran_h * BAS_LIBRE) - hauteur
    return x, max(haut, min(y, bas))


def cote_proche(voulu, disponibles):
    """Le côté préparé le plus proche de celui voulu (« 0 » : image d'origine, à réduire)."""
    tailles = [int(c) for c in disponibles if c.isdigit() and int(c) > 0]
    return str(min(tailles, key=lambda c: abs(c - voulu))) if tailles else ("0" if "0" in disponibles else None)


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
        self.donnees_images = charger_images(dossier, self.valeurs.get("patch"))
        self.suivi = Suivi()
        self.donnees, self.temps_lu, self.verrou = None, 0.0, threading.Lock()
        self.alertes_faites, self.lignes, self.images = set(), [], {}
        self.position_fichier = dossier / "surcouche_position.json"

        try:                       # vrais pixels de l'écran (sinon Windows agrandit la fenêtre et la rend floue)
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (ImportError, AttributeError, OSError):
            pass
        self.racine = tk.Tk()
        self.racine.withdraw()
        self.racine.title("Panda")
        self.racine.overrideredirect(True)
        self.racine.attributes("-topmost", True)
        self.racine.configure(bg=FOND)
        try:
            self.racine.attributes("-transparentcolor", FOND)          # fond transparent (Windows)
        except tk.TclError:
            pass
        echelle = self.racine.winfo_screenheight() / HAUTEUR_REF
        self.portrait, self.icone = round(PORTRAIT_REF * echelle), round(ICONE_REF * echelle)
        taille = -round(TEXTE_REF * echelle)                           # négatif : en pixels, comme le jeu
        self.police, self.police_gras = ("Segoe UI", taille), ("Segoe UI", taille, "bold")
        self.police_compte = ("Segoe UI", -round(8 * echelle), "bold")
        self.marge = max(1, round(2 * echelle))

        # Bandeau : le dragon à gauche, le Héraut (puis le Nashor) à droite.
        self.bandeau = tk.Frame(self.racine, bg=FOND, padx=4, pady=0)
        self.bandeau.pack(fill="x")
        self.objectif_gauche = tk.Label(self.bandeau, text="", bg=FOND, fg=TEXTE, font=self.police_gras, pady=0)
        self.objectif_gauche.pack(side="left")
        self.objectif_droite = tk.Label(self.bandeau, text="", bg=FOND, fg=TEXTE, font=self.police_gras, pady=0)
        self.objectif_droite.pack(side="right")
        for w in (self.bandeau, self.objectif_gauche, self.objectif_droite):     # déplacer en tirant le bandeau
            w.bind("<ButtonPress-1>", self._debut_glisser)
            w.bind("<B1-Motion>", self._glisser)
            w.bind("<ButtonRelease-1>", self._fin_glisser)
        self.cadre = tk.Frame(self.racine, bg=FOND, padx=2, pady=1)
        self.cadre.pack(fill="both")
        self._placer()
        threading.Thread(target=self._lecture, daemon=True).start()
        self.racine.after(300, self._rafraichir)

    # Position : par défaut en haut à droite, entre le bandeau des scores et le fil des kills ; sinon là où tu l'as
    # laissée ; toujours entre le chrono et la minimap.
    def _placer(self):
        try:
            x, y = json.loads(self.position_fichier.read_text(encoding="utf-8"))
            self.position_choisie = True
        except (OSError, ValueError, TypeError):
            x, y = self.racine.winfo_screenwidth() - round(14 * self.icone), round(self.racine.winfo_screenheight() * HAUT_LIBRE)
            self.position_choisie = False
        self.racine.geometry(f"+{x}+{y}")

    def _caler_par_defaut(self):
        """Collée au bord droit, juste sous le bandeau des scores (une fois sa largeur connue)."""
        if not self.position_choisie:
            self.racine.update_idletasks()
            x = self.racine.winfo_screenwidth() - self.racine.winfo_width() - round(self.icone / 2)
            self.racine.geometry(f"+{x}+{round(self.racine.winfo_screenheight() * HAUT_LIBRE)}")

    def _borner(self):
        self.racine.update_idletasks()
        x, y = self.racine.winfo_x(), self.racine.winfo_y()
        bx, by = borner(x, y, self.racine.winfo_width(), self.racine.winfo_height(),
                        self.racine.winfo_screenwidth(), self.racine.winfo_screenheight())
        if (bx, by) != (x, y):
            self.racine.geometry(f"+{bx}+{by}")

    def _debut_glisser(self, e):
        self._ecart = (e.x_root - self.racine.winfo_x(), e.y_root - self.racine.winfo_y())

    def _glisser(self, e):
        self.racine.geometry(f"+{e.x_root - self._ecart[0]}+{e.y_root - self._ecart[1]}")

    def _fin_glisser(self, _e):
        self.position_choisie = True
        self._borner()
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

    # Images : portraits et icônes de Saut éclair et de Zhonya, à la taille de l'écran, et leur version grisée.
    def _image(self, genre, nom, grise=False):
        cle = (genre, nom, grise)
        if cle not in self.images:
            if grise:
                normale = self._image(genre, nom)
                self.images[cle] = self._griser(normale) if normale else None
            else:
                voulu = self.portrait if genre == "champion" else self.icone
                cote = cote_proche(voulu, self.donnees_images)
                donnees = (self.donnees_images.get(cote) or {}).get(f"{genre}_{nom}") if cote else None
                try:
                    img = self.tk.PhotoImage(data=donnees) if donnees else None
                    if img is not None and img.width() > voulu * 1.5:      # image d'origine : réduite
                        img = img.subsample(max(1, round(img.width() / voulu)))
                    self.images[cle] = img
                except self.tk.TclError:
                    self.images[cle] = None
        return self.images[cle]

    def _griser(self, img):
        """Copie en gris foncé (comme un sort en recharge dans le jeu)."""
        l, h = img.width(), img.height()
        grise = self.tk.PhotoImage(width=l, height=h)
        lignes = []
        for y in range(h):
            pixels = []
            for x in range(l):
                r, g, b = img.get(x, y)[:3]
                v = int((0.3 * r + 0.59 * g + 0.11 * b) * 0.4)
                pixels.append(f"#{v:02x}{v:02x}{v:02x}")
            lignes.append("{" + " ".join(pixels) + "}")
        grise.put(" ".join(lignes))
        return grise

    def _portrait(self, ligne, colonne, joueur, couleur_equipe):
        tk = self.tk
        if joueur is None:
            w = tk.Label(self.cadre, text="", bg=FOND, width=4)
        else:
            img = self._image("champion", id_champion(joueur))
            if img:
                w = tk.Label(self.cadre, image=img, bg=FOND, highlightthickness=1, highlightbackground=couleur_equipe)
            else:
                w = tk.Label(self.cadre, text=(joueur.get("championName") or "?")[:4], bg=FOND, fg=couleur_equipe,
                             font=self.police_gras, width=4)
        w.grid(row=ligne, column=colonne, pady=0, padx=self.marge)

    def _construire(self, paires):
        tk = self.tk
        for w in self.cadre.winfo_children():
            w.destroy()
        for col, taille in ((2, self.icone + 2), (3, 8), (4, self.icone + 2)):
            self.cadre.grid_columnconfigure(col, minsize=taille)
        self.cadre.grid_columnconfigure(5, minsize=self.icone // 2)    # espace entre les deux équipes
        self.lignes = []
        for i, (eux, nous) in enumerate(paires):
            self._portrait(i, 0, eux, EUX)
            or_eux = tk.Label(self.cadre, text="", bg=FOND, font=self.police, width=5, anchor="e", pady=0)
            or_eux.grid(row=i, column=1)
            champ = id_champion(eux) if eux else None
            ligne = {"eux": eux, "nous": nous, "champion": champ, "or_eux": or_eux}
            for sort, col in (("F", 2), ("Z", 4)):
                w = tk.Label(self.cadre, text="", bg=FOND, fg=TEXTE, font=self.police_compte, cursor="hand2",
                             compound="center", bd=0)
                w.grid(row=i, column=col, pady=1)
                if champ:
                    w.bind("<Button-1>", lambda _e, c=champ, s=sort: self._clic(c, s))
                ligne[sort] = w
            cosmic = tk.Label(self.cadre, text="", bg=FOND, fg=COULEURS["orange"], font=("Segoe UI", -max(7, self.icone // 2)), pady=0)
            cosmic.grid(row=i, column=3, sticky="n")
            ligne["cosmic"] = cosmic
            or_nous = tk.Label(self.cadre, text="", bg=FOND, font=self.police, width=5, anchor="e", pady=0)
            or_nous.grid(row=i, column=6)
            ligne["or_nous"] = or_nous
            self._portrait(i, 7, nous, NOUS)
            self.lignes.append(ligne)
        # Dernière ligne : les deux totaux sous leurs colonnes d'or, avec le nom de chaque équipe à côté
        # (EUX en rouge sous les portraits adverses, NOUS en bleu sous les tiens).
        tk.Frame(self.cadre, bg="#3a3f47", height=1).grid(row=5, column=0, columnspan=8, sticky="ew", pady=(1, 0))
        tk.Label(self.cadre, text="EUX", bg=FOND, fg=EUX, font=self.police_gras, pady=0).grid(row=6, column=0)
        self.total_eux = tk.Label(self.cadre, text="", bg=FOND, font=self.police_gras, width=5, anchor="e", pady=0)
        self.total_eux.grid(row=6, column=1)
        self.total_nous = tk.Label(self.cadre, text="", bg=FOND, font=self.police_gras, width=5, anchor="e", pady=0)
        self.total_nous.grid(row=6, column=6)
        tk.Label(self.cadre, text="NOUS", bg=FOND, fg=NOUS, font=self.police_gras, pady=0).grid(row=6, column=7)
        self._caler_par_defaut()

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
        if j is None or not (a_le_sort(j) if sort == "F" else a_zhonya(j, self.valeurs)):
            return                   # pas de Saut éclair (ou pas de Zhonya) : case vide, le clic ne fait rien
        duree = self._durees(j)[sort]
        self.suivi.basculer(champion, sort, temps, self.suivi.restant(champion, sort, temps, duree))
        self._rafraichir(planifier=False)

    def _icone(self, w, sort, present, reste):
        """Icône en couleur : disponible ; grisée avec le compte à rebours par-dessus : en recharge."""
        if not present:
            w.configure(image="", text="")
            return
        genre, nom = ("spell", "SummonerFlash") if sort == "F" else ("item", self.valeurs["zhonya_ids"][0])
        img = self._image(genre, nom, grise=reste is not None)
        texte = format_temps(reste) if reste is not None else ("" if img else sort)
        couleur = TEXTE if img else (COULEURS["vert"] if reste is None else COULEURS["rouge"])
        w.configure(image=img or "", text=texte, fg=couleur)

    def _rafraichir(self, planifier=True):
        try:
            with self.verrou:
                donnees = self.donnees
            if not donnees:
                if self.racine.state() != "withdrawn":
                    self.racine.withdraw()
                return
            temps = self._temps(donnees)
            _, _, noms = equipes(donnees)
            paires = vis_a_vis(donnees)
            cle = tuple(sorted(id_champion(j) + (j.get("team") or "") for j in donnees.get("allPlayers") or []))
            if cle != self.suivi.partie:                       # nouvelle partie : tout repart de zéro
                self.suivi.nouvelle_partie(cle)
                self.alertes_faites = set()
                self._construire(paires)
            if self.racine.state() == "withdrawn":
                self.racine.deiconify()
                self.racine.attributes("-topmost", True)
                self._borner()

            # Objectifs : dragon, puis Héraut (ou Nashor quand le Héraut n'est plus là).
            for w, (nom, apparition, en_vie) in zip((self.objectif_gauche, self.objectif_droite),
                                                   objectifs(temps, (donnees.get("events") or {}).get("Events") or [], noms, self.valeurs)):
                if apparition is None:
                    w.configure(text="")
                elif en_vie:
                    w.configure(text=f"{nom} dispo", fg=TEXTE)
                else:
                    reste = apparition - temps
                    w.configure(text=f"{nom} {format_temps(reste)}", fg=COULEURS["orange"] if reste <= ALERTE_AVANT_S else TEXTE)
                    if reste <= ALERTE_AVANT_S and (nom, apparition) not in self.alertes_faites:
                        self.alertes_faites.add((nom, apparition))
                        threading.Thread(target=bip, daemon=True).start()

            # Chaque vis-à-vis : or des objets (couleurs du plus riche), Saut éclair et Zhonya de l'adversaire.
            actuels = {(j.get("team"), id_champion(j)): j for j in donnees.get("allPlayers") or []}
            total_eux = total_nous = 0
            for ligne in self.lignes:
                eux = actuels.get((ligne["eux"].get("team"), ligne["champion"])) if ligne["eux"] else None
                nous = actuels.get((ligne["nous"].get("team"), id_champion(ligne["nous"]))) if ligne["nous"] else None
                or_e = or_objets(eux, self.valeurs) if eux else None
                or_n = or_objets(nous, self.valeurs) if nous else None
                total_eux += or_e or 0
                total_nous += or_n or 0
                c_e, c_n = couleurs_or(or_e, or_n)
                ligne["or_eux"].configure(text=format_or(or_e) if or_e is not None else "", fg=COULEURS[c_e])
                ligne["or_nous"].configure(text=format_or(or_n) if or_n is not None else "", fg=COULEURS[c_n])
                if eux is None:
                    continue
                durees = self._durees(eux)
                for sort, present in (("F", a_le_sort(eux)), ("Z", a_zhonya(eux, self.valeurs))):
                    self._icone(ligne[sort], sort, present, self.suivi.restant(ligne["champion"], sort, temps, durees[sort]))
                ligne["cosmic"].configure(text="✦" if a_inspiration(eux, self.valeurs) and a_le_sort(eux) else "")
            c_e, c_n = couleurs_or(total_eux, total_nous)
            self.total_eux.configure(text=format_or(total_eux), fg=COULEURS[c_e])
            self.total_nous.configure(text=format_or(total_nous), fg=COULEURS[c_n])
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
