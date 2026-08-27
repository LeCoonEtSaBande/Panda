export default function TachesPage() {
  return (
    <main>
      <h1>Tâches</h1>
      <input type="text" placeholder="Recherche action, historique, interlocuteur" />
      <p className="muted" style={{ marginTop: 16 }}>
        Filtres : A faire avant · A faire/En attente · Pro/Perso. Tri urgence puis
        plus ancienne modif.
      </p>
    </main>
  );
}
