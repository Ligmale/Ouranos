# Journal d'utilisation de l'IA — Ouranos

Format de chaque entrée : outil · ce qui a été demandé · réponse reçue · vérification faite ·
décision (gardé, modifié, rejeté).

## 1. Création du journal IA (2026-10-28)

- **Outil :** Claude Code (Claude Opus 5.5)
- **Demandé :** créer `JOURNAL_IA.md` pour déclarer l'usage de l'IA, comme l'exige l'énoncé.
- **Réponse reçue :** fichier créé avec le format d'entrée (outil · demandé · réponse reçue ·
  vérification faite · décision), puis tenu à jour par Claude Code à notre demande après chaque
  aide notable. Les entrées sont donc rédigées par l'IA.
- **Vérification faite :** format comparé aux consignes de l'énoncé (au moins 5 entrées, dont
  une vérification qui a changé une décision) ; chaque entrée est relue par l'équipe.
- **Décision :** **gardé.** La colonne « Décision » de chaque entrée reste à remplir par
  l'équipe après relecture.

## 2. Vérification des données et choix de la cible (2026-10-28)

- **Outil :** Claude Code (Claude Opus 5.5)
- **Demandé :** nous aider à choisir les décisions de `DECISIONS.md` par une série de
  questions, puis vérifier si les données 2025 de McTavish, YUL, St-Hubert et Mirabel étaient
  assez complètes pour prédire l'écart de température centre-ville − aéroport.
- **Réponse reçue :** téléchargement des 12 mois de 2025 pour les 4 stations et calcul des
  valeurs manquantes et de l'écart. Température manquante ≤ 0,4 % ; écart McTavish − YUL de
  +0,26 °C en moyenne (+1,7 °C par nuit calme) ; écart McTavish − Mirabel de +2,0 °C (+4,2 °C
  par nuit calme).
- **Vérification faite :** l'inventaire officiel des stations d'ECCC a confirmé les
  `stationID` ; nous avons ouvert les CSV pour confirmer les noms de colonnes.
- **Décision :** **modifiée.** Nous avons abandonné la cible prévue (température dans 3 h)
  pour l'écart centre-ville − station de référence, avec plusieurs références plutôt que YUL
  seule, parce que l'écart avec YUL était trop faible. C'est la vérification qui a changé une
  décision.

## 3. Carte satellite des îlots de chaleur (2026-10-28)

- **Outil :** Claude Code (Claude Opus 5.5), avec recherche web
- **Demandé :** peut-on utiliser un gradient de température vu par satellite ?
- **Réponse reçue :** l'INSPQ publie une carte des îlots de chaleur 2020-2022 (Landsat 8/9,
  CC-BY 4.0) sur Données Québec. Mais elle mesure la température de surface et non celle de
  l'air, ce n'est pas une série horaire, et elle est au format matriciel.
- **Vérification faite :** page du jeu de données sur Données Québec et rapport méthodologique.
- **Décision :** **rejetée** pour le modèle ; notée comme alternative écartée et piste
  d'amélioration.

## 4. Script de téléchargement `src/telechargement.py` (2026-10-28)

- **Outil :** Claude Code (Claude Opus 5.5)
- **Demandé :** écrire en entier le script de téléchargement des données horaires d'ECCC.
- **Réponse reçue :** script complet avec un générateur `generer_mois`, la construction des
  URL, la vérification que la réponse est bien un CSV horaire (en-tête `Date/Time (LST)`), et
  les fichiers déjà présents sautés. Les erreurs réseau sont collectées sans arrêter le script.
- **Vérification faite :** un fichier supprimé, puis le script relancé : seul ce fichier a été
  retéléchargé, et il est identique octet pour octet à l'original. Un second lancement ne
  télécharge plus rien.
- **Décision :** _à compléter après relecture par l'équipe (gardé / modifié / rejeté)_

## 5. Erreur de schéma Polars dans `src/station.py` (2026-11-02)

- Claude Code (Opus 5.5) · diagnostic de `SchemaError` au `pl.concat` puis ajout de `SCHEMA_NUMERIQUE` (`schema_overrides`) · cause : types devinés sur 100 lignes, colonne vide → String · vérifié : type de la colonne lu dans chaque CSV, puis `python src/station.py` passe · décision : _à compléter (gardé / modifié / rejeté)_

## 6. Choix des colonnes à garder (2026-11-02)

- Claude Code (Opus 5.5) · quelles colonnes ECCC garder, et faut-il garder latitude/longitude · inventaire des 31 colonnes (contenu, % manquant par station) ; McTavish : date + température, références : 9 colonnes ; latitude/longitude/Climate ID retirés (3 valeurs, même information que la station) · vérifié : % manquant recalculé sur les 48 CSV, d'où deux corrections (Mirabel n'a pas de précipitations non plus ; `Weather` vaut `"NA"`, pas vide) · décision : _à compléter_

## 7. Tendance de pression sur 3 h dans `clean_data` (2026-11-02)

- Claude Code (Opus 5.5) · ajouter la tendance de pression à `clean_data` · correction de `.alias` (mal placé, il écrasait la pression), tri par date, `delta_pression3h` avec `shift(3)` puis `tendance_pression` (hausse/stable/baisse, seuil ± 0,1 kPa, manquants gardés `null`) · vérifié : 8 760 lignes par station avec un pas d'1 h, environ 50 % stable / 25 % hausse / 25 % baisse · décision : _à compléter_

## 8. Types de `self._data` et de `make_target` dans `src/station.py` (2026-11-03)

- **Outil :** Claude Code (Claude Opus 5.5)
- **Demandé :** déduire le type de retour de `make_target`, puis corriger l'erreur de Pyright
  sur `self._data`.
- **Réponse reçue :** `make_target` retourne un `pl.DataFrame` (`.select` sur un DataFrame).
  L'erreur venait de `self._data`, qui était d'abord une liste vide (`[]`, type inconnu) dans
  `load_data` puis un `DataFrame` dans `clean_data` : Pyright choisissait alors la version de
  `pl.concat` qui retourne une `Series`, sans méthode `.select`. Correction : deux attributs
  d'un seul type chacun, déclarés dans `__init__` : `self._brutes: list[pl.DataFrame]` (mois
  bruts, remplis par `load_data`) et `self._data: pl.DataFrame` (tableau nettoyé, rempli par
  `clean_data`) ; annotations `-> pl.DataFrame` sur la propriété `data` et sur `make_target`.
  Signalé aussi : avant `clean_data()`, `station.data` est maintenant un DataFrame vide.
- **Vérification faite :** `pyright src/station.py` passe de 1 erreur à 0 erreur.
- **Décision :** _à compléter après relecture par l'équipe (gardé / modifié / rejeté)_

## 9. Squelette de `src/donnees.py` (2026-11-03)

- **Outil :** Claude Code (Claude Opus 5.5)
- **Demandé :** où calculer l'écart de température (dans `Station` ou dans `donnees.py`), puis
  un squelette de `src/donnees.py`.
- **Réponse reçue :** l'écart va dans `donnees.py`, car il combine deux stations alors qu'une
  `Station` ne connaît que ses propres données. Squelette sans logique (corps en
  `raise NotImplementedError`), avec signatures typées, docstrings (entrées, sortie, cas
  d'échec) et `TODO` sous forme de questions : conversions `saison`, `moment_journee`,
  `direction_8_points` ; appariement `apparier` (jointure interne, renommer la température de
  McTavish avant, la retirer après pour éviter la fuite), `ajouter_categories`,
  `construire_tableau` ; classes `Variable` (abstraite), `VariableNumerique`,
  `VariableCategorielle`. Signalé : `src/exceptions.py` reste à créer, et pytest devra ajouter
  `src/` au chemin d'import.
- **Vérification faite :** `pyright src/donnees.py` : 0 erreur.
- **Décision :** _à compléter après relecture par l'équipe (gardé / modifié / rejeté)_

## 10. Découpage de la journée : `moment_journee` (2026-11-05)

- **Outil :** Claude Code (Claude Opus 5.5)
- **Demandé :** est-il nécessaire de découper l'heure en périodes, puis terminer
  `moment_journee` dans `src/donnees.py`.
- **Réponse reçue :** le découpage est peu utile pour la forêt aléatoire, qui trouve seule ses
  coupures sur l'heure brute (0 à 23), mais utile pour la régression linéaire (îlot de chaleur
  non linéaire selon l'heure). Conseil : garder l'heure brute en numérique **et**
  `moment_journee`, puis comparer la MAE chronologique avec et sans. Limite signalée : en heure
  normale, le coucher du soleil varie d'environ 16 h (décembre) à 20 h (juin), donc une même
  période ne correspond pas à la même situation selon la saison. Fonction terminée avec nos
  bornes (nuit 0-5, matin 6-10, après-midi 11-16, soir 17-23, `ValueError` hors de 0 à 23).
- **Vérification faite :** fonction appelée sur chaque heure de transition (0, 5, 6, 10, 11,
  16, 17, 23) et sur −1 et 24 : résultats et erreurs attendus.
- **Décision :** _à compléter après relecture par l'équipe (gardé / modifié / rejeté)_

## 11. Tests de `moment_journee` (2026-11-05)

- **Outil :** Claude Code (Claude Opus 5.5)
- **Demandé :** écrire les tests de `moment_journee` dans `tests/test_donnees.py`.
- **Réponse reçue :** 3 tests paramétrés, sans le décorateur `@A_ECRIRE` : une heure typique
  par moment (3, 8, 14, 20), les bornes (0, 23 et chaque transition 5/6, 10/11, 16/17) et les
  heures invalides (−1, 24) avec `pytest.raises(ValueError)` ; import de `moment_journee`
  ajouté.
- **Vérification faite :** `pytest tests/test_donnees.py -k moment_journee` : 14 cas réussis.
- **Décision :** _à compléter après relecture par l'équipe (gardé / modifié / rejeté)_

## 12. Passage de Polars à pandas (2026-11-14)

- **Outil :** Claude Code (Claude Opus 5.5)
- **Demandé :** convertir tout le code qui utilise Polars en pandas.
- **Réponse reçue :** `src/station.py` réécrit avec pandas (`pd.read_csv` avec
  `dtype=SCHEMA_NUMERIQUE` et `encoding="utf-8-sig"`, `pd.concat` + `sort_values` +
  `reset_index`, `shift(3)` pour la tendance de pression, masques booléens pour
  hausse/stable/baisse, manquant gardé si la pression manque) ; types et `.assign` dans
  `src/donnees.py` ; `requirements.txt` (Polars retiré, `pandas==3.1.1`, `python-dateutil`,
  `tzdata`) ; `DECISIONS.md` §8 et `CLAUDE.md` mis à jour. Signalé : les deux premières lignes
  de `apparier` n'ont aucun effet (résultat non réassigné), et `station.py` lit un CSV entier à
  l'import pour vérifier son existence (`os.path.exists` suffirait).
- **Vérification faite :** `python src/station.py` passe ; `pytest` : 26 réussis, 28 ignorés ;
  pour les 4 stations, le tableau pandas est identique à celui de l'ancienne logique Polars
  (8 760 lignes × 11 colonnes, mêmes valeurs et mêmes tendances).
- **Décision :** _à compléter après relecture par l'équipe (gardé / modifié / rejeté)_

## 13. Séance de questions sur `src/modele.py` (2026-11-17)

- **Outil :** Claude Code (Claude Opus 5.5)
- **Demandé :** nous poser des questions sur tous les choix du modèle, une série à la fois,
  avec une recommandation pour chacune, puis résumer les décisions.
- **Réponse reçue :** 20 questions (type de modèle, découpage, métrique, valeurs manquantes,
  forme de l'objet sauvegardé, scores de référence, contenu du JSON, structure du code,
  tests) et explications du `Pipeline` contre le dict et des scores de référence. Décisions
  prises : MLP gardé (contre la forêt validée) + régression linéaire en comparaison, sans
  revalidation ; découpage chronologique officiel (6 derniers jours de chaque mois) ; **RMSE
  officielle**, calculée avec NumPy ; imputation dans un seul `Pipeline` (médiane, constante
  « Inconnu ») ; références moyenne globale et moyenne par station ; `permutation_importance` ;
  JSON avec colonnes, catégories, limites, scores et écart moyen par heure ; `predire()` dans
  `modele.py` ; petites fonctions et tests.
- **Vérification faite :** chaque question comparée au code de `src/modele.py` et à
  `DECISIONS.md`. Cette vérification a changé une décision : le décalage optimisé avec scipy
  était calculé sur le jeu de test (fuite) ; nous l'avons retiré.
- **Décision :** _à compléter après relecture par l'équipe (gardé / modifié / rejeté)_

## 14. Modèle retenu vérifié contre l'énoncé (2026-11-17)

- **Outil :** Claude Code (Claude Opus 5.5)
- **Demandé :** finir le `README.md` (résultats du modèle, couverture, documentation, outils du
  chapitre 7).
- **Réponse reçue :** avant d'écrire, Claude a relu l'énoncé et signalé que le Volet 2 limite le
  modèle à « régression linéaire ou logistique, k plus proches voisins, arbre de décision ou
  forêt aléatoire » et que « l'apprentissage profond est exclu », alors que notre modèle retenu
  était un réseau de neurones (`MLPRegressor`), choisi lors de la séance de questions (entrée 13)
  sans revalidation par l'auxiliaire.
- **Vérification faite :** lecture du Volet 2 de `Énoncé_Projet.pdf` (page 2). Comparaison des
  scores sur le découpage chronologique : MLP RMSE 1,20 °C, régression linéaire 1,31 °C,
  moyenne par station 1,52 °C.
- **Décision :** **modifié.** La régression linéaire devient le modèle retenu et le seul utilisé
  par l'interface (score officiel RMSE 1,31 °C) ; le MLP est encore entraîné et sauvegardé
  (`modeles/mlp.joblib`), en comparaison seulement. `DECISIONS.md`, le JSON de métadonnées et le
  `README.md` sont mis à jour.

## 15. Comparaison du code avec l'énoncé, graphique d'exploration et docstrings (2026-11-23)

- **Outil :** Claude Code (Claude Opus 5.5)
- **Demandé :** comparer le projet à l'énoncé (`Projet_2_INF1007_Enonce.pdf`, sur Moodle) pour
  trouver ce qui manque, puis faire le graphique d'exploration et compléter les docstrings.
- **Réponse reçue :** liste des manques ; les deux principaux dans le code étaient l'absence de
  graphique d'exploration enregistré avec `savefig` (exigé au chapitre 13) et des fonctions
  sans docstring ni annotations (exigées au chapitre 6), surtout dans la classe `Station` et dans
  `exceptions.py`. Code produit : `src/exploration.py` (écart moyen selon l'heure par référence et
  distribution de l'écart, enregistrés dans `figures/exploration_ecart.png`),
  `tests/test_exploration.py` (7 tests), docstrings et annotations ajoutées, `README.md` mis à
  jour (graphique, commande, structure, 144 tests, couverture remesurée à 88 % pour la logique).
- **Vérification faite :** relecture de l'énoncé (sections 3, 5 et 8) ; tests lancés (144
  passent) ; un script `ast` qui liste les fonctions de `src/` sans docstring ni annotation (plus
  aucune) ; le graphique ouvert et regardé : la légende cachait la courbe de Mirabel et a été
  déplacée deux fois. Les moyennes par heure du graphique concordent avec les constats déjà
  écrits dans le README (écart maximal vers 2 h à 4 h, minimal vers 12 h à 16 h).
- **Décision :** **gardé**, poussé sur `main`. Ces commits (et quatre plus anciens) ont
  « Claude » comme auteur dans l'historique Git : ils ont été faits depuis la session Claude Code,
  pas par un membre de l'équipe.
