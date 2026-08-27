"use client";

import { useState } from "react";
import {
  addGrocery,
  commitGrocery,
  toggleGrocery,
} from "@/lib/local-db";
import { useDb } from "@/lib/use-db";

export default function CoursesPage() {
  const db = useDb();
  const [line, setLine] = useState("");

  return (
    <main>
      <h1>Courses</h1>
      <ul className="task-list">
        {db.grocery.map((g) => (
          <li key={g.id}>
            <label className={g.checked ? "struck" : undefined}>
              <input
                type="checkbox"
                checked={g.checked}
                onChange={() => toggleGrocery(g.id)}
              />{" "}
              {g.label}
            </label>
          </li>
        ))}
      </ul>
      <input
        type="text"
        placeholder="Ajouter un article"
        value={line}
        onChange={(e) => setLine(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            addGrocery(line);
            setLine("");
          }
        }}
      />
      <button
        type="button"
        className="btn"
        onClick={() => {
          if (line.trim()) {
            addGrocery(line);
            setLine("");
          }
          commitGrocery();
        }}
      >
        OK
      </button>
    </main>
  );
}
