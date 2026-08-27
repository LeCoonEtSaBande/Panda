import { loadIdentite } from "@/lib/identite";

export default function ParametresPage() {
  const id = loadIdentite();
  return (
    <main>
      <h1>Paramètres</h1>
      <p className="muted">Seed actuel (fichier, puis table settings) :</p>
      <p>
        {id.display_name}
        <br />
        {id.aliases.join(", ")}
        <br />
        Orgs : {id.organizations.join(", ")}
        <br />
        {id.tokens_par_mois.toLocaleString("fr-FR")} tokens / mois · reset jour{" "}
        {id.jour_reset}
      </p>
    </main>
  );
}
