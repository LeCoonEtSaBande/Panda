export default function CoursesPage() {
  return (
    <main>
      <h1>Courses</h1>
      <p className="muted">
        Cochage + ligne d’ajout. OK = barrés disparus. L’Assistant écrit ici sans
        carte Valider.
      </p>
      <input type="text" placeholder="Ajouter un article" />
      <button type="button" className="btn">
        OK
      </button>
    </main>
  );
}
