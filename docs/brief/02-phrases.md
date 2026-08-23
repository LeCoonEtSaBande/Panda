# 02 — Phrases (le livrable le plus important)

Une fiche = **une** situation réelle. Copie le bloc `FICHE` autant de fois que besoin.

**Minimum pour coder :** 8 fiches, dont 2 avec un collage mail ou SMS.

N’écris pas de roman autour. Remplis les champs. Si tu ne sais pas, mets `?`.

---

## Modèle (recopie tel quel)

```md
### FICHE n°
- Mode : À faire | Fait | Reçu | Envoyé | Rédiger | Libre
- Ce que je tape ou je colle :

> (ici la phrase OU l’extrait mail/SMS, tel que sur le téléphone)

- Ce que je veux VOIR dans la carte proposition (pas du SQL, du français) :
  - Tâches créées / touchées :
  - Champs : (durée, perso/pro, contact, attente retour, butoir, sous-tâche, notes, liens…)
- Ce que l’IA ne doit PAS faire :
- Si plusieurs tâches dans un mail : (une proposition groupée / une carte par tâche)
```

---

## Exemples déjà remplis (ne pas recopy comme « tes » tests — c’est le style)

### Exemple A — mode À faire

- Mode : **À faire**
- Ce que je tape :

> Je dois contacter un plombier pour la maison

- Proposition attendue :
  - **Créer** 1 tâche perso, durée 15 min, pas de butoir, pas de contact
- Ne pas faire : inventer un nom de plombier, mettre un butoir « bientôt »

### Exemple B — mode Fait

- Mode : **Fait**
- Ce que je tape :

> J’ai appelé le plombier

- Proposition attendue :
  - **Modifier** la tâche plombier déjà ouverte : attente de retour = oui, date de contact = aujourd’hui
- Ne pas faire : créer une 2ᵉ tâche « Appel plombier »

### Exemple C — mode Reçu (collage)

- Mode : **Reçu**
- Ce que je colle :

> De: qualitec@example.com
> Objet: Devis fuite cuisine
> Bonjour, suite à votre appel on peut passer jeudi 10h ou vendredi 16h. Devis 180€ HT. Merci de confirmer. Cordialement, Martin Qualitec 06 06 06 06 06

- Proposition attendue :
  - **Modifier** la tâche plombier : contact Martin / Qualitec, tél, lien ou note = extraits utiles
  - **Créer** éventuellement une sous-tâche « Confirmer créneau Qualitec » butoir avant jeudi
  - Ne pas marquer la tâche parente « faite »
- Ne pas faire : inventer un 2ᵉ artisan ; tout coller en description à la place d’une note

### Exemple D — mode Envoyé

- Mode : **Envoyé**
- Ce que je colle :

> (SMS) Bonjour, ok pour jeudi 10h. Merci. 

- Proposition attendue :
  - Tâche « Confirmer créneau » → faite **ou** archivée (dis-moi dans la fiche)
  - Tâche plombier : attente de retour = oui (on attend qu’ils viennent / confirment)
  - Extraire le SMS dans `notes`
- Ne pas faire : créer « SMS envoyé » comme nouvelle tâche à part entière

### Exemple E — mode Rédiger

- Mode : **Rédiger**
- Ce que je tape :

> Mail à Qualitec pour qu’il me dise tout ce qu’il me faut avant de venir (accès, coupure eau, créneau)

- Proposition attendue :
  - **Pas d’écriture base** d’abord
  - Un **texte de mail** (objet + corps) que je copie
  - Case optionnelle : « Sauver ce brouillon dans les notes de la tâche plombier »

---

## Tes fiches (à toi)

### FICHE n°1
- Mode :
- Ce que je tape ou je colle :

>

- Proposition attendue :
- Ne pas faire :

### FICHE n°2
- Mode :
- Ce que je tape ou je colle :

>

- Proposition attendue :
- Ne pas faire :

### FICHE n°3
- Mode :
- Ce que je tape ou je colle :

>

- Proposition attendue :
- Ne pas faire :

### FICHE n°4
- Mode :
- Ce que je tape ou je colle :

>

- Proposition attendue :
- Ne pas faire :

### FICHE n°5
- Mode :
- Ce que je tape ou je colle :

>

- Proposition attendue :
- Ne pas faire :

### FICHE n°6
- Mode :
- Ce que je tape ou je colle :

>

- Proposition attendue :
- Ne pas faire :

### FICHE n°7
- Mode :
- Ce que je tape ou je colle :

>

- Proposition attendue :
- Ne pas faire :

### FICHE n°8
- Mode :
- Ce que je tape ou je colle :

>

- Proposition attendue :
- Ne pas faire :

*(Duplique en n°9, 10… si tu as le courage. 8 bien faits suffisent pour v1.)*

---

## Recette déjà convenue (ne réécris pas sauf correction)

Ces 10-là restent des **tests automatiques / manuels** après code. Corrige uniquement si tu changes d’avis.

1. Plombier maison → créer perso, 15 min, pas butoir, pas contact  
2. Qualitec 0606060606 → maj contact  
3. J’ai appelé → attente oui, date contact aujourd’hui  
4. Store salon avant fin septembre → perso, butoir **30 sept**, **demander** la durée si absente  
5. Contacter électricien diagnostic → sous-tâche du store, même butoir  
6. Souffiane 0707070707 → maj **électricien**, pas le store  
7. Pas avant décembre → cascade butoir **15 déc** (parent + sous-tâches ouvertes)  
8. Demi-heure → suggestion ≤ 30 min, pas « en attente », pas parent bloqué  
9. Je ne travaille pas → suggestions **perso**  
10. Rappeler maman aujourd’hui → contact Maman, butoir aujourd’hui, 15 min  

---

## Pièges (lis avant d’écrire 30 fiches)

- **Mode Fait** + phrase « je dois… » = mauvaise fiche. Change de mode, ou dis-le dans « ne pas faire ».
- Un mail de 3 sujets = **dis** si tu veux 3 tâches ou 1 tâche + 2 sous-tâches.
- Les numéros / mails dans tes exemples : tu peux **anonymiser** (`06 00 00 00 00`, `martin@…). L’important c’est la **forme**.
- « Propose-moi ce que je peux faire » = plutôt mode **À faire** ou **Libre** ? **Tranche-le** dans une fiche, sinon je mets ça en À faire + outil `suggest`.
