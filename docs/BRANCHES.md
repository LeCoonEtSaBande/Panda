# Branches GitHub (lisibles)

Panda n’a **pas besoin** d’une forêt de branches. Deux suffisent.

| Branche | Rôle | Tu y touches ? |
|---|---|---|
| **`main`** | Version « officielle ». **Vercel déploiera celle-ci** une fois la PR fusionnée. | Seulement via « Merge » de la PR, pas à la main. |
| **`cursor/spec-livrables-04ba`** | **Branche de travail actuelle** : spec + proto de l’app. Pull request [#1](https://github.com/LeCoonEtSaBande/Panda/pull/1). | C’est là que Cursor (et toi) commit. |

```text
main  ←  (plus tard) merge de la PR
   \________________________________
        cursor/spec-livrables-04ba     ← tu es ici
```

Le préfixe `cursor/` + le suffixe `-04ba` sont imposés à l’agent cloud. Le milieu (`spec-livrables`, plus tard `fix-taches`, etc.) décrit le sujet.

**Ne crée pas** `dev`, `prod`, `lee`, etc. : on se perd. Une PR, une branche de travail, `main` = ce qui est en ligne.
