"""Lien entre le client League of Legends et l'Assistant Draft : la page voit les picks toute seule.

Le client League expose, sur ton propre PC seulement, une interface locale (« LCU ») qui donne l'état de la
sélection des champions. Ce programme la lit toutes les secondes et la met à disposition de la page, sur
http://127.0.0.1:47123/draft. Il ne fait QUE lire ce que tu vois déjà dans ton client : champions choisis et
bannis, les pré-picks de ton équipe, ton poste et ceux de ton équipe. Il ne lit jamais le nom ni les stats des autres joueurs, et ne clique
jamais à ta place (règles de Riot pour les applications tierces).

Utilisation : lancer ce programme (ou « Assistant Draft - Lien client.exe » sous Windows) avant ou pendant une
partie, puis ouvrir la page de l'assistant. Il ouvre aussi la page s'il la trouve dans le même dossier.
Bibliothèque standard Python seulement.

    python3 lien_client.py [--port 47123] [--lockfile <chemin>] [--sans-page]
"""

import argparse
import base64
import glob
import json
import os
import platform
import re
import ssl
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = 47123
POSTES = {"top": "top", "jungle": "jgl", "middle": "mid", "bottom": "adc", "utility": "sup"}
LOCKFILES = [
    r"C:\Riot Games\League of Legends\lockfile",
    r"D:\Riot Games\League of Legends\lockfile",
    r"C:\Program Files\Riot Games\League of Legends\lockfile",
    "/Applications/League of Legends.app/Contents/LoL/lockfile",
]


def dossier_du_programme():
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent


# --- Trouver le client ---------------------------------------------------------------------------------

def depuis_processus():
    """Port et mot de passe lus sur la ligne de commande de LeagueClientUx (marche où que le jeu soit installé)."""
    try:
        if platform.system() == "Windows":
            sortie = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-CimInstance Win32_Process -Filter \"name='LeagueClientUx.exe'\" | Select-Object -ExpandProperty CommandLine"],
                capture_output=True, text=True, timeout=10, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
        else:
            sortie = subprocess.run(["ps", "-A", "-o", "args"], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    port = re.search(r"--app-port=(\d+)", sortie)
    jeton = re.search(r"--remoting-auth-token=([\w-]+)", sortie)
    return (int(port.group(1)), jeton.group(1)) if port and jeton else None


def depuis_lockfile(chemins):
    for chemin in chemins:
        for c in glob.glob(chemin):
            try:
                morceaux = Path(c).read_text(encoding="utf-8").strip().split(":")
                return int(morceaux[2]), morceaux[3]
            except (OSError, IndexError, ValueError):
                continue
    return None


def trouver_client(lockfile=None):
    if lockfile:
        return depuis_lockfile([lockfile])
    return depuis_processus() or depuis_lockfile(LOCKFILES)


# --- Lire la sélection -------------------------------------------------------------------------------------

class Client:
    def __init__(self, port, jeton):
        self.base = f"https://127.0.0.1:{port}"
        self.entete = "Basic " + base64.b64encode(f"riot:{jeton}".encode()).decode()
        # Certificat du client signé par Riot pour 127.0.0.1 : on ne parle qu'à sa propre machine.
        self.ssl = ssl.create_default_context()
        self.ssl.check_hostname = False
        self.ssl.verify_mode = ssl.CERT_NONE

    def get(self, chemin):
        req = urllib.request.Request(self.base + chemin, headers={"Authorization": self.entete, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, context=self.ssl, timeout=3) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:          # pas de sélection en cours
                return None
            raise


def resumer(session):
    """Ce que la page a besoin de savoir : rien sur les joueurs, seulement champions (verrouillés, et pré-picks
    de ton équipe), postes, bans et phase."""
    if not session:
        return {"etat": "hors_selection"}
    moi = session.get("localPlayerCellId")
    actions = [a for groupe in session.get("actions", []) for a in groupe]
    choisis = {a["actorCellId"]: a["championId"] for a in actions if a.get("type") == "pick" and a.get("completed") and a.get("championId")}
    bans = [a["championId"] for a in actions if a.get("type") == "ban" and a.get("completed") and a.get("championId")]
    bans += [c for c in session.get("bans", {}).get("myTeamBans", []) + session.get("bans", {}).get("theirTeamBans", []) if c]
    # Un champion compte quand son choix est verrouillé (action « pick » terminée) ; sans actions (partie à
    # l'aveugle), on prend le champion affiché.
    verrouille = (lambda j: choisis.get(j.get("cellId"), 0)) if actions else (lambda j: j.get("championId") or 0)
    # Pré-picks de TON équipe (ce que le client t'affiche aussi) : le champion survolé pendant son tour, sinon
    # celui annoncé avant (« intention »). Ceux de l'équipe adverse ne sont jamais envoyés au client.
    survols = {a["actorCellId"]: a["championId"] for a in actions
               if a.get("type") == "pick" and not a.get("completed") and a.get("championId")}
    nous = []
    for j in sorted(session.get("myTeam", []), key=lambda j: j.get("cellId", 0)):
        cid = verrouille(j)
        intention = 0 if cid else (survols.get(j.get("cellId")) or j.get("championPickIntent") or 0)
        nous.append({"poste": POSTES.get((j.get("assignedPosition") or "").lower(), ""), "champion": cid or 0,
                     "intention": intention, "moi": j.get("cellId") == moi})
    eux = []
    for j in sorted(session.get("theirTeam", []), key=lambda j: j.get("cellId", 0)):
        eux.append({"champion": verrouille(j) or 0})
    phase = (session.get("timer") or {}).get("phase", "")
    return {"etat": "selection", "partie": session.get("gameId") or 0, "phase": phase, "nous": nous, "eux": eux,
            "bans": sorted(set(b for b in bans if b and b > 0))}


# --- Le petit serveur local pour la page --------------------------------------------------------------

class Etat:
    def __init__(self):
        self.verrou = threading.Lock()
        self.dernier = {"etat": "client_ferme"}

    def poser(self, valeur):
        with self.verrou:
            self.dernier = valeur

    def lire(self):
        with self.verrou:
            return dict(self.dernier)


def serveur(etat, port):
    class Gestion(BaseHTTPRequestHandler):
        def _entetes(self, code=200, type_="application/json"):
            self.send_response(code)
            self.send_header("Content-Type", type_ + "; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Private-Network", "true")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

        def do_OPTIONS(self):
            self._entetes(204)

        def do_GET(self):
            if self.path.startswith("/draft"):
                self._entetes()
                self.wfile.write(json.dumps(etat.lire()).encode())
            else:
                self._entetes(404)

        def log_message(self, *args):
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", port), Gestion)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def ouvrir_page():
    pages = sorted(dossier_du_programme().glob("Assistant Draft - DL - *.html"))
    if pages:
        webbrowser.open(pages[-1].resolve().as_uri())
        print(f"Page ouverte : {pages[-1].name}")
    else:
        print("Ouvre la page de l'assistant dans ton navigateur : elle se reliera toute seule.")


def boucle(etat, lockfile=None, une_fois=False):
    client, annonce = None, None
    while True:
        try:
            if client is None:
                trouve = trouver_client(lockfile)
                if trouve:
                    client = Client(*trouve)
            if client is None:
                valeur = {"etat": "client_ferme"}
            else:
                valeur = resumer(client.get("/lol-champ-select/v1/session"))
        except (urllib.error.URLError, OSError, ValueError):
            client, valeur = None, {"etat": "client_ferme"}
        etat.poser(valeur)
        message = {"client_ferme": "En attente du client League…", "hors_selection": "Client trouvé : en attente d'une sélection des champions.",
                   "selection": "Sélection en cours : la page se remplit toute seule."}[valeur["etat"]]
        if message != annonce:
            print(message, flush=True)
            annonce = message
        if une_fois:
            return valeur
        time.sleep(1.0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--lockfile", help="chemin du lockfile du client, si le jeu est installé ailleurs")
    parser.add_argument("--sans-page", action="store_true", help="ne pas ouvrir la page de l'assistant")
    args = parser.parse_args()
    etat = Etat()
    try:
        serveur(etat, args.port)
    except OSError:
        print(f"Le port {args.port} est déjà pris : le lien client tourne sans doute déjà.")
        return 1
    print(f"Lien client prêt (http://127.0.0.1:{args.port}/draft). Laisse cette fenêtre ouverte pendant tes parties.")
    if not args.sans_page:
        ouvrir_page()
    try:
        boucle(etat, args.lockfile)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
