export default function LibrePage() {
  return (
    <main>
      <h1>Libre</h1>
      <p className="muted">
        Lecture seule sur les bases. Pas d’écriture. Jauge dans le bandeau.
      </p>
      <textarea placeholder="Question…" />
      <button type="button" className="btn">
        Envoyer
      </button>
    </main>
  );
}
