// Même règle que analyse/regle.py sur la branche d'analyse : les deux doivent rester identiques.
const Regle = (() => {
  const STYLES = ["Engage", "Pick", "Poke", "Counter-engage", "Disengage"];
  const POINTS_PRINCIPAL = 2;
  const POINTS_SECONDAIRE = 1;
  const SEUIL_PRINCIPAL = 3;
  const SEUIL_SECONDAIRE = 2;
  const SEUIL_DEGATS = 4;

  function choisir(scores, principaux, seuil, exclu) {
    let meilleur = "";
    for (const style of STYLES) {
      if (style === exclu || scores[style] < seuil) continue;
      if (
        !meilleur ||
        scores[style] > scores[meilleur] ||
        (scores[style] === scores[meilleur] && principaux[style] > principaux[meilleur])
      ) {
        meilleur = style;
      }
    }
    return meilleur;
  }

  function etiqueter(champions, catalogue) {
    const fiches = champions.filter((nom) => catalogue[nom]).map((nom) => catalogue[nom]);
    const scores = Object.fromEntries(STYLES.map((s) => [s, 0]));
    const principaux = Object.fromEntries(STYLES.map((s) => [s, 0]));
    for (const fiche of fiches) {
      if (fiche.principal) {
        scores[fiche.principal] += POINTS_PRINCIPAL;
        principaux[fiche.principal] += 1;
      }
      if (fiche.secondaire) scores[fiche.secondaire] += POINTS_SECONDAIRE;
    }

    const principal = choisir(scores, principaux, SEUIL_PRINCIPAL, null);
    const secondaire = principal ? choisir(scores, principaux, SEUIL_SECONDAIRE, principal) : "";

    const tanky = new Set(fiches.map((f) => f.tanky));
    const front = tanky.has("HP+") ? "HP+" : tanky.has("HP") ? "HP" : "";
    const disengage = fiches.some((f) => f.principal === "Disengage" || f.secondaire === "Disengage");
    const ad = fiches.filter((f) => f.degats === "AD" || f.degats === "Hybride").length;
    const ap = fiches.filter((f) => f.degats === "AP" || f.degats === "Hybride").length;
    let degats = "mixte";
    if (ad >= SEUIL_DEGATS && ap < SEUIL_DEGATS) degats = "AD";
    else if (ap >= SEUIL_DEGATS && ad < SEUIL_DEGATS) degats = "AP";

    return {
      principal,
      secondaire,
      assassin: fiches.some((f) => f.principal === "Pick"),
      front,
      protect: fiches.some((f) => f.carry) && disengage,
      side: fiches.some((f) => f.split),
      degats,
      scores,
    };
  }

  function correspond(etiquettes, condition) {
    return Object.entries(condition || {}).every(([cle, attendu]) =>
      Array.isArray(attendu) ? attendu.includes(etiquettes[cle]) : etiquettes[cle] === attendu,
    );
  }

  return { STYLES, etiqueter, correspond };
})();

if (typeof module !== "undefined") module.exports = Regle;
