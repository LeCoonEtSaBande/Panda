import { loadIdentite, tokensThisPeriod } from "@/lib/identite";

/** Compteur local : somme token_usage (0 tant que Claude n’est pas branché). */
export function Gauge() {
  const id = loadIdentite();
  const { remaining, total, ratio } = tokensThisPeriod(0, id);
  const pct = Math.round(ratio * 100);
  return (
    <div className="gauge" title={`Reset le ${id.jour_reset} du mois`}>
      {remaining.toLocaleString("fr-FR")} / {total.toLocaleString("fr-FR")}
      <div className="gauge-track">
        <div className="gauge-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
