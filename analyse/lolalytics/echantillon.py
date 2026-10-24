"""Télécharge quelques pages de Lolalytics, telles quelles, pour écrire le lecteur à partir de vraies pages.

Une page toutes les 3 secondes, une dizaine de pages en tout. Écrit dans analyse/lolalytics/echantillon/.
"""

import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ICI = Path(__file__).resolve().parent
SORTIE = ICI / "echantillon"
PAGES = {
    "tierlist_jungle": "https://lolalytics.com/lol/tierlist/?lane=jungle&tier=platinum_plus&region=euw",
    "tierlist_jungle_sans_filtre": "https://lolalytics.com/lol/tierlist/?lane=jungle",
    "counters_fiddlesticks_jungle": "https://lolalytics.com/lol/fiddlesticks/counters/?lane=jungle&tier=platinum_plus&region=euw",
    "counters_garen_top": "https://lolalytics.com/lol/garen/counters/?lane=top&tier=platinum_plus&region=euw",
    "build_fiddlesticks_jungle": "https://lolalytics.com/lol/fiddlesticks/build/?lane=jungle&tier=platinum_plus&region=euw",
    "vs_fiddlesticks_kayn": "https://lolalytics.com/lol/fiddlesticks/vs/kayn/build/?lane=jungle&vslane=jungle&tier=platinum_plus&region=euw",
}
ENTETES = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
           "Accept": "text/html,application/xhtml+xml", "Accept-Language": "en-US,en;q=0.9"}


def main():
    SORTIE.mkdir(parents=True, exist_ok=True)
    for nom, url in PAGES.items():
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=ENTETES), timeout=30) as r:
                (SORTIE / f"{nom}.html").write_bytes(r.read())
                print(f"{nom} : {r.status}, {(SORTIE / f'{nom}.html').stat().st_size} octets")
        except urllib.error.URLError as e:
            print(f"{nom} : échec ({e})")
        time.sleep(3)
    for chemin in ("robots.txt",):
        try:
            with urllib.request.urlopen(urllib.request.Request("https://lolalytics.com/" + chemin, headers=ENTETES), timeout=30) as r:
                (SORTIE / chemin).write_bytes(r.read())
        except urllib.error.URLError as e:
            print(f"{chemin} : échec ({e})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
