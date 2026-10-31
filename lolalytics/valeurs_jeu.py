"""Valeurs et timers du patch pour la surcouche en jeu (flashs, Zhonya, dragons, Héraut, or des objets).

Lancé par le bouton « 2 · Lolalytics », après le scraper, à chaque passage. Écrit lolalytics/valeurs_jeu.json,
que la surcouche du lien client télécharge au lancement (et garde en copie pour jouer sans connexion).

D'où viennent les valeurs, dans l'ordre :
1. Data Dragon (les fichiers officiels de Riot) : version du patch, recharge de Saut éclair, hâte des invocateurs
   des objets (Bottes de lucidité ioniennes, Lucidité pourpre, et tout nouvel objet qui en donne), hâte de la
   rune Perspicacité cosmique, prix total de chaque objet, identifiant du Sablier de Zhonya.
2. Le wiki League of Legends : recharge du Sablier de Zhonya, apparition des dragons et du Héraut (Data Dragon ne
   les donne pas). Une valeur lue n'est gardée que si elle reste dans une fourchette plausible.
3. Sinon, la valeur du fichier précédent, et en dernier recours la valeur par défaut (vérifiée le 31/10/2026).

Le résumé dit, pour chaque valeur, d'où elle vient et si elle a changé. Bibliothèque standard Python seulement.

    python3 lolalytics/valeurs_jeu.py [--sortie lolalytics/valeurs_jeu.json]
"""

import argparse
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ICI = Path(__file__).resolve().parent
DDRAGON = "https://ddragon.leagueoflegends.com"
WIKI = "https://wiki.leagueoflegends.com/en-us/api.php?action=parse&format=json&prop=text&page="
ENTETES = {"User-Agent": "Mozilla/5.0 (compatible; panda-draft/1.0; projet personnel, une fois par patch)"}

# Valeurs vérifiées le 31/10/2026 (patch 16.21), en secondes de jeu.
DEFAUTS = {
    "flash_s": 300,                     # recharge de base de Saut éclair
    "zhonya_s": 120,                    # recharge de base du Sablier de Zhonya
    "zhonya_ids": ["3157"],
    "hate_invocateur_objets": {"3158": 10, "3171": 20},   # Bottes de lucidité ioniennes, Lucidité pourpre
    "cosmic_hate_invocateur": 18,       # Perspicacité cosmique (arbre Inspiration)
    "cosmic_hate_objets": 10,
    "cosmic_id": 8347,
    "inspiration_id": 8300,
    "dragon_premier_s": 300,            # premier dragon à 5:00
    "dragon_reapparition_s": 300,       # 5 min après chaque dragon élémentaire
    "ancien_reapparition_s": 360,       # Dragon ancien : 6 min après l'âme, puis après chaque ancien
    "heraut_apparition_s": 900,         # Héraut à 15:00, une seule fois par partie
    "heraut_disparition_s": 1185,       # disparaît à 19:45 s'il n'est pas tué
}

# Fourchettes plausibles : une valeur lue en dehors est ignorée (page mal lue, texte d'un autre mode de jeu…).
FOURCHETTES = {
    "flash_s": (120, 420), "zhonya_s": (60, 240), "cosmic_hate_invocateur": (5, 40), "cosmic_hate_objets": (0, 30),
    "dragon_premier_s": (180, 480), "dragon_reapparition_s": (180, 480), "ancien_reapparition_s": (240, 600),
    "heraut_apparition_s": (480, 1200), "heraut_disparition_s": (900, 1500),
}


def telecharger(url, essais=3):
    for essai in range(essais):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=ENTETES), timeout=30) as r:
                return r.read().decode("utf-8")
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            if essai == essais - 1:
                print(f"  échec : {url} ({e})", flush=True)
                return None
            time.sleep(3 * (essai + 1))


def texte_brut(fragment):
    """Texte sans balises ni entités, espaces tassés."""
    sans = re.sub(r"<[^>]+>", " ", fragment or "")
    return re.sub(r"\s+", " ", html.unescape(sans)).strip()


def plausible(cle, valeur):
    bas, haut = FOURCHETTES.get(cle, (float("-inf"), float("inf")))
    return valeur is not None and bas <= valeur <= haut


def minutes_secondes(texte):
    m = re.match(r"(\d{1,2}):(\d{2})$", texte)
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


# --- Data Dragon -----------------------------------------------------------------------------------

def hate_invocateur_du_texte(texte):
    m = re.search(r"(\d+)\s*Summoner Spell Haste", texte_brut(texte), re.I)
    return int(m.group(1)) if m else None


def lire_objets(items):
    """Depuis item.json : prix total de chaque objet de la Faille, objets qui donnent de la hâte des invocateurs,
    identifiants du Sablier de Zhonya."""
    prix, hate, zhonya = {}, {}, []
    for ident, o in items.get("data", {}).items():
        if not o.get("maps", {}).get("11", False):
            continue
        prix[ident] = int(o.get("gold", {}).get("total", 0) or 0)
        h = hate_invocateur_du_texte(o.get("description", ""))
        if h:
            hate[ident] = h
        if "zhonya" in (o.get("name") or "").lower():
            zhonya.append(ident)
    return prix, hate, sorted(zhonya)


def lire_cosmic(runes):
    """Hâte des invocateurs et des objets de Perspicacité cosmique, depuis runesReforged.json."""
    for arbre in runes:
        for rangee in arbre.get("slots", []):
            for rune in rangee.get("runes", []):
                if rune.get("key") == "CosmicInsight" or rune.get("id") == DEFAUTS["cosmic_id"]:
                    txt = texte_brut(rune.get("longDesc") or rune.get("shortDesc") or "")
                    inv = re.search(r"(\d+)\s*Summoner Spell Haste", txt, re.I)
                    obj = re.search(r"(\d+)\s*Item Haste", txt, re.I)
                    return {"cosmic_id": rune.get("id"), "inspiration_id": arbre.get("id"),
                            "cosmic_hate_invocateur": int(inv.group(1)) if inv else None,
                            "cosmic_hate_objets": int(obj.group(1)) if obj else None}
    return {}


def lire_flash(sorts):
    cd = sorts.get("data", {}).get("SummonerFlash", {}).get("cooldown") or []
    return int(cd[0]) if cd else None


# --- Wiki --------------------------------------------------------------------------------------------

def page_wiki(titre):
    brut = telecharger(WIKI + urllib.parse.quote(titre))
    try:
        return texte_brut(json.loads(brut)["parse"]["text"]["*"]) if brut else None
    except (ValueError, KeyError, TypeError):
        return None


def lire_zhonya_wiki(texte):
    """Recharge de Stase, par exemple « Stasis … (120 seconds cooldown) » ou « Cooldown 120 »."""
    if not texte:
        return None
    for motif in (r"Stasis.{0,400}?(\d{2,3})\s*(?:seconds?|s)\s*cooldown", r"[Cc]ooldown[^0-9]{0,15}(\d{2,3})\b"):
        m = re.search(motif, texte, re.S)
        if m and plausible("zhonya_s", int(m.group(1))):
            return int(m.group(1))
    return None


def lire_heraut_wiki(texte):
    """Apparition et disparition du Héraut : « spawns at 15:00 », « despawns at 19:45 »."""
    if not texte:
        return {}
    r = {}
    m = re.search(r"spawns?\s+(?:at|after)\s+(\d{1,2}:\d{2})", texte, re.I)
    if m:
        r["heraut_apparition_s"] = minutes_secondes(m.group(1))
    m = re.search(r"despawns?\s+(?:at|after)\s+(\d{1,2}:\d{2})", texte, re.I)
    if m:
        r["heraut_disparition_s"] = minutes_secondes(m.group(1))
    return r


def lire_dragons_wiki(texte):
    """Premier dragon (« first … spawns at 5:00 ») et réapparitions (« respawn … 5 minutes »)."""
    if not texte:
        return {}
    r = {}
    m = re.search(r"(?:first|initial)[^.]{0,80}?(?:spawn\w*)[^.]{0,40}?(\d{1,2}:\d{2})", texte, re.I)
    if m:
        r["dragon_premier_s"] = minutes_secondes(m.group(1))
    m = re.search(r"[Ee]lemental [Dd]rakes?[^.]{0,120}?respawn\w*[^.]{0,40}?(\d+(?:[.,]\d+)?)\s*minutes", texte)
    if m:
        r["dragon_reapparition_s"] = int(float(m.group(1).replace(",", ".")) * 60)
    m = re.search(r"Elder Dragon[^.]{0,160}?respawn\w*[^.]{0,40}?(\d+(?:[.,]\d+)?)\s*minutes", texte)
    if m:
        r["ancien_reapparition_s"] = int(float(m.group(1).replace(",", ".")) * 60)
    return r


# --- Assemblage ----------------------------------------------------------------------------------------

def assembler(precedent, lus):
    """Pour chaque valeur : la valeur lue si elle est plausible, sinon la précédente, sinon le défaut.
    Rend (valeurs, sources, changements)."""
    valeurs, sources, changements = {}, {}, []
    for cle, defaut in DEFAUTS.items():
        lu, origine = lus.get(cle, (None, None))
        if lu not in (None, {}, []) and (not isinstance(lu, (int, float)) or plausible(cle, lu)):
            valeurs[cle], sources[cle] = lu, origine
        elif cle in precedent:
            valeurs[cle], sources[cle] = precedent[cle], "fichier précédent"
        else:
            valeurs[cle], sources[cle] = defaut, "valeur par défaut (vérifiée le 31/10/2026)"
        if cle in precedent and precedent[cle] != valeurs[cle]:
            changements.append(f"{cle} : {precedent[cle]} → {valeurs[cle]}")
    return valeurs, sources, changements


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sortie", default=str(ICI / "valeurs_jeu.json"))
    args = parser.parse_args()
    sortie = Path(args.sortie)
    try:
        precedent = json.loads(sortie.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        precedent = {}

    lus, prix, version = {}, precedent.get("prix_objets", {}), precedent.get("version_ddragon", "")
    versions = telecharger(f"{DDRAGON}/api/versions.json")
    if versions:
        version = json.loads(versions)[0]
        dd = f"{DDRAGON}/cdn/{version}/data/en_US"
        brut = telecharger(f"{dd}/summoner.json")
        if brut:
            lus["flash_s"] = (lire_flash(json.loads(brut)), "Data Dragon")
        brut = telecharger(f"{dd}/item.json")
        if brut:
            prix_lus, hate, zhonya = lire_objets(json.loads(brut))
            prix = prix_lus or prix
            lus["hate_invocateur_objets"] = (hate, "Data Dragon")
            lus["zhonya_ids"] = (zhonya, "Data Dragon")
        brut = telecharger(f"{dd}/runesReforged.json")
        if brut:
            for cle, val in lire_cosmic(json.loads(brut)).items():
                lus[cle] = (val, "Data Dragon")

    lus["zhonya_s"] = (lire_zhonya_wiki(page_wiki("Zhonya's Hourglass")), "wiki")
    for cle, val in lire_heraut_wiki(page_wiki("Rift Herald")).items():
        lus[cle] = (val, "wiki")
    for cle, val in lire_dragons_wiki(page_wiki("Dragon")).items():
        lus[cle] = (val, "wiki")

    valeurs, sources, changements = assembler(precedent, lus)
    patch = ".".join(version.split(".")[:2]) if version else precedent.get("patch", "")
    resultat = {"patch": patch, "version_ddragon": version, "date": time.strftime("%Y-%m-%d"), **valeurs,
                "sources": sources, "prix_objets": prix}
    sortie.write_text(json.dumps(resultat, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    if patch and (ICI / patch).is_dir():
        (ICI / patch / "valeurs_jeu.json").write_text(sortie.read_text(encoding="utf-8"), encoding="utf-8")

    lignes = [f"### Valeurs et timers du patch {patch or '?'} (surcouche en jeu)", "",
              "| Valeur | Retenue | Source |", "|---|---|---|"]
    for cle in DEFAUTS:
        lignes.append(f"| `{cle}` | {json.dumps(valeurs[cle], ensure_ascii=False)} | {sources[cle]} |")
    lignes += ["", f"Prix de {len(prix)} objets."]
    lignes += ["", "**Changements depuis le dernier passage :** " + ("; ".join(changements) if changements else "aucun.")]
    texte = "\n".join(lignes) + "\n"
    print(texte)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(texte)
    return 0


if __name__ == "__main__":
    sys.exit(main())
