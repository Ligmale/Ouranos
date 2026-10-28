# Journal d'utilisation de l'IA — Ouranos

Format de chaque entrée : outil · ce qui a été demandé · réponse reçue · vérification faite ·
décision (gardé, modifié, rejeté).

## 1. Vérification des données et choix de la cible (2026-10-28)

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

## 2. Carte satellite des îlots de chaleur (2026-10-28)

- **Outil :** Claude Code (Claude Opus 5.5), avec recherche web
- **Demandé :** peut-on utiliser un gradient de température vu par satellite ?
- **Réponse reçue :** l'INSPQ publie une carte des îlots de chaleur 2020-2022 (Landsat 8/9,
  CC-BY 4.0) sur Données Québec. Mais elle mesure la température de surface et non celle de
  l'air, ce n'est pas une série horaire, et elle est au format matriciel.
- **Vérification faite :** page du jeu de données sur Données Québec et rapport méthodologique.
- **Décision :** **rejetée** pour le modèle ; notée comme alternative écartée et piste
  d'amélioration.

## 3. Script de téléchargement `src/telechargement.py` (2026-10-28)

- **Outil :** Claude Code (Claude Opus 5.5)
- **Demandé :** écrire en entier le script de téléchargement des données horaires d'ECCC.
- **Réponse reçue :** script complet avec un générateur `generer_mois`, la construction des
  URL, la vérification que la réponse est bien un CSV horaire (en-tête `Date/Time (LST)`), et
  les fichiers déjà présents sautés. Les erreurs réseau sont collectées sans arrêter le script.
- **Vérification faite :** un fichier supprimé, puis le script relancé : seul ce fichier a été
  retéléchargé, et il est identique octet pour octet à l'original. Un second lancement ne
  télécharge plus rien.
- **Décision :** _à compléter après relecture par l'équipe (gardé / modifié / rejeté)_
