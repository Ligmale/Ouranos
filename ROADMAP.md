# Feuille de route — Ouranos

Ce document liste ce qu'il reste à faire, **sans dire comment le faire** : c'est à nous de
trouver les solutions. Cocher les cases au fur et à mesure. Se répartir les étapes pour que
chacun ait des commits dans chaque partie et puisse expliquer chaque ligne à l'oral.

Déjà fait : téléchargement des données (`src/telechargement.py`), classe `Station` (chargement,
nettoyage, tendance de pression, cible côté McTavish).

---

## 1. Finir les données

**Objectif :** obtenir le tableau final, une ligne par (heure, station de référence), avec la
cible et toutes les caractéristiques prévues.

- [ ] McTavish et chaque référence sont appariées à la même heure
- [ ] La colonne d'écart existe ; les lignes sans cible sont retirées
- [ ] Saison, moment de la journée et direction du vent en 8 points sont calculés
- [ ] Le nombre de lignes final est dans les bornes de l'énoncé

**À se demander :**
- Quel type de jointure, et que devient une heure présente d'un seul côté ?
- Ces conversions sont-elles de la logique (testable) ou du nettoyage ? Où les mettre ?
- Aucune mesure de McTavish ne reste-t-elle dans les caractéristiques ?

## 2. Classes de variables et exception

**Objectif :** des classes qui savent valider une saisie, réutilisables par l'interface.

- [ ] Une classe parente abstraite et deux classes filles qui redéfinissent la validation
- [ ] Au moins une exception personnalisée, levée avec un message clair
- [ ] Au moins une méthode spéciale utile
- [ ] Au moins 3 classes au total, avec encapsulation

**À se demander :**
- Qu'est-ce qu'une saisie invalide pour une variable numérique ? pour une catégorielle ?
- D'où viennent les intervalles et les catégories permises (codés à la main ou tirés des données) ?

## 3. Exploration

**Objectif :** comprendre l'écart avant de modéliser.

- [ ] Un graphique d'exploration enregistré dans `figures/`
- [ ] Deux ou trois constats notés (dans le README ou DECISIONS)

**À se demander :**
- Qu'est-ce que ce graphique doit nous apprendre ? Le vent change-t-il vraiment l'écart ?
- Les trois références se comportent-elles pareil ?

## 4. Modèle

**Objectif :** un modèle entraîné, évalué honnêtement et sauvegardé avec ses métadonnées.

- [ ] Des scores de référence simples pour savoir si le modèle apporte quelque chose
- [ ] Un modèle simple et le modèle retenu, comparés
- [ ] Les deux découpages (aléatoire exigé, chronologique officiel)
- [ ] Prétraitement dans un pipeline, après le découpage
- [ ] Une métrique calculée à la main avec NumPy
- [ ] Importance des variables regardée
- [ ] Modèle et métadonnées JSON sauvegardés dans `modeles/`

**À se demander :**
- Comment garder les lignes d'une même heure du même côté du découpage ?
- Le score est-il trop beau ? Si oui, d'où vient la fuite ?
- Que doit contenir le JSON pour que l'interface se construise sans lire les données ?
- La forêt reste-t-elle assez petite pour GitHub ?

## 5. Interface Streamlit

**Objectif :** une application locale qui appelle la logique sans la contenir.

- [ ] Un champ par variable, adapté à son type, construit depuis le JSON
- [ ] Saisie invalide → message clair, jamais de traceback
- [ ] Bouton « Prédire » avec un résultat lisible et une marge d'erreur
- [ ] Un graphique Matplotlib dans l'interface
- [ ] Historique des prédictions enregistré et consultable
- [ ] `main.py` sert de point d'entrée
- [ ] Maquette papier

**À se demander :**
- Quelles lignes de l'interface pourrait-on déplacer dans un module testable ?
- Que se passe-t-il si le modèle ou le JSON est absent ?
- Le modèle est-il rechargé (ou pire, réentraîné) à chaque clic ?

## 6. Tests et intégration continue

**Objectif :** prouver que la logique marche, sans réseau.

- [ ] Un petit CSV d'exemple dans `tests/`
- [ ] Au moins 8 tests : cas usuel, cas limite, cas d'erreur, flottants
- [ ] Couverture mesurée et notée dans le README
- [ ] Un workflow GitHub Actions qui lance les tests à chaque push, vert

**À se demander :**
- Quelles fonctions sont les plus risquées ? Les tester en premier.
- Les tests passent-ils sur une machine qui n'a pas `donnees/` ?

## 7. Exigences transversales

À vérifier sur tout le code avant la remise :

- [ ] Fonctions courtes, avec docstring (entrées, sortie, cas d'échec) et annotations de type
- [ ] Les calculs retournent une valeur ; l'affichage est ailleurs
- [ ] Aucun `except` nu
- [ ] Chemins avec `os`, existence vérifiée avant d'ouvrir, `with` partout
- [ ] Au moins 4 modules + `main.py`
- [ ] Au moins un outil du chapitre 7, expliqué en une phrase dans le README
- [ ] `requirements.txt` à jour (il manque encore des bibliothèques)

## 8. Livrables

- [ ] `README.md` : lancement, score officiel, couverture, 3 pages de documentation, limites
- [ ] `DECISIONS.md` : 1 à 2 pages, chaque choix validé par l'auxiliaire (A, B, C, D)
- [ ] `JOURNAL_IA.md` : au moins 5 entrées, colonne « Décision » remplie
- [ ] Commit final qui inclut `modeles/`
- [ ] Dépôt GitHub public, cloné et lancé sur une autre machine pour vérifier

**Dernière question :** chacun de nous peut-il expliquer chaque ligne du projet ?
