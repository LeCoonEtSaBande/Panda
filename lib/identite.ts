import fs from "node:fs";
import path from "node:path";
import yaml from "js-yaml";

export type Identite = {
  display_name: string;
  aliases: string[];
  organizations: string[];
  tokens_par_mois: number;
  jour_reset: number;
};

export function loadIdentite(): Identite {
  const raw = fs.readFileSync(
    path.join(process.cwd(), "config/identite.yml"),
    "utf8",
  );
  return yaml.load(raw) as Identite;
}

/** Début de période [jour_reset, jour_reset+1 mois). */
export function periodStart(now: Date, jourReset: number): Date {
  const y = now.getFullYear();
  const m = now.getMonth();
  const d = now.getDate();
  if (d >= jourReset) return new Date(y, m, jourReset);
  return new Date(y, m - 1, jourReset);
}

export function tokensThisPeriod(_used: number, identite: Identite) {
  const total = identite.tokens_par_mois;
  const used = Math.max(0, _used);
  const remaining = Math.max(0, total - used);
  const ratio = total > 0 ? Math.min(1, used / total) : 0;
  return { used, remaining, total, ratio };
}
