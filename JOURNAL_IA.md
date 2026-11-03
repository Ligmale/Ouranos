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
