const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const Regle = require("../regle.js");

function catalogue() {
  const lignes = fs
    .readFileSync(path.join(__dirname, "..", "..", "Catalogue.csv"), "utf-8")
    .split(/\r?\n/)
    .filter(Boolean)
    .map((l) => l.split(";"));
  const entete = lignes[1];
  const fiches = {};
  for (const ligne of lignes.slice(2)) {
    const f = Object.fromEntries(entete.map((c, i) => [c, ligne[i] || ""]));
    fiches[f["Champion"]] = {
      principal: f["Style principal"],
      secondaire: f["Style secondaire"],
      tanky: f["Tanky"],
      carry: f["Carry"] === "oui",
      split: f["Split"] === "oui",
      degats: f["Dégâts"],
    };
  }
  return fiches;
}

const fiches = catalogue();

test("compo engage avec Leona et Nami", () => {
  const e = Regle.etiqueter(["Malphite", "Sejuani", "Leona", "Nami", "Samira"], fiches);
  assert.strictEqual(e.scores.Engage, 6);
  assert.strictEqual(e.scores["Counter-engage"], 4);
  assert.strictEqual(e.principal, "Engage");
  assert.strictEqual(e.secondaire, "Counter-engage");
  assert.strictEqual(e.front, "HP+");
  assert.strictEqual(e.protect, true);
  assert.strictEqual(e.degats, "AP");
});

test("égalité de score : le plus de principaux, puis l'ordre des styles", () => {
  const faux = {
    A: { principal: "Poke", secondaire: "", tanky: "", carry: false, split: false, degats: "AD" },
    B: { principal: "Poke", secondaire: "", tanky: "", carry: false, split: false, degats: "AD" },
    C: { principal: "Engage", secondaire: "Pick", tanky: "", carry: false, split: false, degats: "AD" },
    D: { principal: "Pick", secondaire: "Engage", tanky: "", carry: false, split: false, degats: "AD" },
  };
  const e = Regle.etiqueter(["A", "B", "C", "D"], faux);
  assert.deepStrictEqual([e.scores.Poke, e.scores.Engage, e.scores.Pick], [4, 3, 3]);
  assert.strictEqual(e.principal, "Poke");
  assert.strictEqual(e.secondaire, "Engage");
  assert.strictEqual(e.degats, "AD");
});

test("assassin seulement avec un Pick en principal", () => {
  const sansPick = Object.keys(fiches).find((n) => fiches[n].secondaire === "Pick" && fiches[n].principal !== "Pick");
  assert.strictEqual(Regle.etiqueter([sansPick], fiches).assassin, false);
  const avecPick = Object.keys(fiches).find((n) => fiches[n].principal === "Pick");
  assert.strictEqual(Regle.etiqueter([avecPick], fiches).assassin, true);
});

test("une liste dans une condition vaut « l'une de ces valeurs »", () => {
  const e = { principal: "Engage", front: "HP" };
  assert.ok(Regle.correspond(e, { principal: "Engage", front: ["HP", ""] }));
  assert.ok(!Regle.correspond(e, { front: "HP+" }));
  assert.ok(Regle.correspond(e, undefined));
});
