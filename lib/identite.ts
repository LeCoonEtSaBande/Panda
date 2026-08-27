import fs from "node:fs";
import path from "node:path";
import yaml from "js-yaml";

export type Identite = {
  display_name: string;
  aliases: string[];
  organizations: string[];
};

export function loadIdentite(): Identite {
  const raw = fs.readFileSync(
    path.join(process.cwd(), "config/identite.yml"),
    "utf8",
  );
  return yaml.load(raw) as Identite;
}
