# Ouranos — l'îlot de chaleur urbain de Montréal

Projet 2 du cours INF1007 (Polytechnique Montréal, A2026) : « De la donnée à l'application ».

Ouranos estime **combien il fait plus chaud au centre-ville de Montréal (station McTavish)
qu'à un aéroport de la région**, à la même heure, à partir des conditions mesurées à
l'aéroport. On saisit la station de référence, la date, l'heure et la météo mesurée ;
l'application prédit l'écart de température et en déduit la température au centre-ville.

> Exercice pédagogique : les estimations ne remplacent pas les observations ni les
> prévisions officielles d'Environnement et Changement climatique Canada.

**Équipe :** Ligmale et PatriceWu123 (comptes GitHub)

## Jeu de données

- **Source :** Environnement et Changement climatique Canada (ECCC), données climatiques
  historiques **horaires**, service de téléchargement en lot —
  <https://climat.meteo.gc.ca/historical_data/search_historic_data_f.html>
- **Licence :** [Licence du gouvernement ouvert – Canada](https://ouvert.canada.ca/fr/licence-du-gouvernement-ouvert-canada)
- **Période :** 1ᵉʳ janvier au 31 décembre 2025 (heure normale locale), téléchargée le 2026-10-28
- **Stations :**

  | Station | Rôle | `stationID` |
  |---|---|---|
  | MCTAVISH (McGill, centre-ville) | ville : sert seulement à calculer la cible | 10761 |
  | MONTREAL INTL A (Trudeau, Dorval) | référence | 51157 |
  | MONTREAL/ST-HUBERT (Longueuil) | référence | 48374 |
  | MONTREAL MIRABEL INTL A (rural, 42 km au nord) | référence | 49608 |

- **Fichiers bruts :** 48 CSV (4 stations × 12 mois), 6,4 Mo, dans `donnees/brutes/`.
  Ils **ne sont pas inclus dans le dépôt** : chacun les télécharge une fois avec
  `python src/telechargement.py` (voir Utilisation).
- **Tableau final :** **26 179 lignes**, une par (heure, station de référence) :
  - **cible** `ecart` = température McTavish − température de la référence, à la même heure
    (régression, en °C) ; les heures sans cible sont retirées, jamais imputées ;
  - **6 caractéristiques numériques**, mesurées à la référence : température, point de rosée,
    humidité relative, pression, vitesse du vent, visibilité ;
  - **5 caractéristiques catégorielles** : station de référence, saison, moment de la
    journée, direction du vent en 8 points, tendance de la pression sur 3 h.
  - Aucune mesure de McTavish n'est une caractéristique (sinon on recalculerait la cible).

## Installation

Python 3.14.

```bash
git clone https://github.com/Ligmale/Ouranos.git
cd Ouranos
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

## Utilisation

Toutes les commandes se lancent **depuis la racine du dépôt**.

```bash
python src/telechargement.py     # 1. télécharger les données (une seule fois)
python src/modele.py             # 2. entraîner et sauvegarder les modèles (< 1 min)
streamlit run src/main.py        # 3. lancer l'application : http://localhost:8501
```

Pour télécharger d'autres années, les donner en arguments :
`python src/telechargement.py 2023 2024 2025` (un CSV par station, par année et par mois ;
les fichiers déjà présents ne sont pas retéléchargés). L'entraînement utilise seulement 2025.

Les modèles entraînés sont inclus dans le dépôt (`modeles/`) : pour seulement **utiliser**
l'application, l'étape 3 suffit. L'application n'entraîne jamais de modèle au lancement.

L'interface ([Streamlit](https://streamlit.io), en local seulement) fonctionne **sans
réseau** : les polices (Inter, et Cinzel pour les titres) sont servies depuis `src/static/` et le thème sombre est réglé
dans `.streamlit/config.toml`.

- **Saisie** (barre latérale) : station de référence, date, heure, puis les mesures. Seule la
  température est obligatoire ; une mesure laissée vide est remplacée par la médiane
  d'entraînement, et la direction du vent et la tendance de pression acceptent « Inconnu ».
  « 7,6 » et « 7.6 » sont acceptés. Saison et moment de la journée sont calculés à partir de
  la date et de l'heure.
- **Validation :** une saisie vide (obligatoire), non numérique ou hors des limites physiques
  affiche un message clair, jamais un traceback. Une valeur hors de celles vues à
  l'entraînement affiche un avertissement.
- **Résultat :** écart prédit et température estimée au centre-ville, avec l'erreur typique
  du modèle (± RMSE).
- **Graphiques :** à gauche l'écart moyen selon l'heure pour la station choisie, à droite les
  températures moyennes de la saison à la référence et au centre-ville, avec la prédiction.
- **Historique :** chaque prédiction est ajoutée à `historique/predictions.csv` et affichée en
  bas de la page.

## Tests

```bash
pytest
coverage run --source=src -m pytest && coverage report
```

131 tests pytest, sans réseau ni dossier `donnees/` (petits CSV dans `tests/fake_donnees/` et
tableau synthétique) : cas usuels, cas limites, cas d'erreur avec `pytest.raises`, flottants
avec `pytest.approx`. Le workflow GitHub Actions (`.github/workflows/tests.yml`) lance
`pytest` à chaque push.

**Couverture** (`coverage`, mesurée le 2026-11-17) :

| Module | Couverture |
|---|---|
| `src/donnees.py` | 93 % |
| `src/modele.py` | 91 % |
| `src/exceptions.py` | 91 % |
| `src/station.py` | 79 % |
| `src/telechargement.py` | 72 % (sans réseau : le téléchargement lui-même n'est pas testé) |
| **Logique (5 modules ci-dessus)** | **88 %** |
| `src/interface.py`, `src/main.py` | 0 % (interface Streamlit, non testée par pytest) |
| **Tout `src/`** | **70 %** |

## Structure du code

```
src/
  telechargement.py  téléchargement unique des CSV d'ECCC (générateur generer_mois)
  station.py         classe Station : chargement, nettoyage, tendance de pression sur 3 h
  donnees.py         conversions (saison, moment, vent en 8 points), appariement McTavish ×
                     référence, tableau final, classes Variable / VariableNumerique /
                     VariableCategorielle
  modele.py          découpages, Pipeline, entraînement, scores, métadonnées, sauvegarde,
                     classes Predicteur et Prediction ; script d'entraînement
  exceptions.py      exceptions personnalisées (DonneeInvalideError, ModeleNonTrouveError…)
  interface.py       interface Streamlit (affichage seulement, la logique est dans modele.py)
  main.py            point d'entrée : streamlit run src/main.py
  static/            polices Inter et Cinzel et leurs licences
tests/               tests pytest (test_donnees.py, test_modele.py, fake_donnees/)
modeles/             regression_lineaire.joblib, mlp.joblib, metadonnees.json
donnees/brutes/      CSV d'ECCC (non versionnés, créés par telechargement.py)
historique/          historique des prédictions (créé par l'application)
.streamlit/          configuration de l'interface (thème sombre, police)
```

**Classes :** `Variable` (abstraite) → `VariableNumerique` et `VariableCategorielle`, qui
redéfinissent chacune `valider` ; `Station` ; `Predicteur`, qui **contient** le `Pipeline`,
les métadonnées et une `Variable` par champ (composition) ; `Prediction` (résultat immuable).

## Résultats du modèle

**Modèle retenu : régression linéaire** (`LinearRegression`), dans un seul `Pipeline`
scikit-learn : médiane pour les numériques manquantes puis mise à l'échelle ; catégorie
« Inconnu » pour les catégorielles manquantes puis encodage one-hot. Tout le prétraitement est
ajusté sur l'entraînement seulement.

**Métrique :** RMSE en °C (racine de l'erreur quadratique moyenne, calculée avec NumPy et
vérifiée contre scikit-learn dans un test), avec MAE et R² en complément.

**Découpages :** `train_test_split` aléatoire (20 %, graine 42), exigé, et **chronologique** :
les 6 derniers jours de chaque mois en test (5 161 lignes), le reste en entraînement (21 018).
Une même heure apparaît 3 fois (une par référence) et les heures voisines se ressemblent : le
découpage aléatoire est trop optimiste. **Le score officiel est le chronologique.**

| Approche | RMSE chrono. | MAE chrono. | R² chrono. | RMSE aléatoire |
|---|---|---|---|---|
| Référence : moyenne globale | 1,67 | 1,23 | 0,00 | 1,74 |
| Référence : moyenne par station | 1,52 | 1,08 | 0,17 | 1,55 |
| **Régression linéaire (retenue)** | **1,31** | **0,97** | **0,38** | 1,28 |
| Réseau de neurones (MLP, comparaison) | 1,20 | 0,84 | 0,48 | 0,97 |

**Score officiel : RMSE = 1,31 °C** (découpage chronologique, régression linéaire).

**Analyse :**

- La régression linéaire bat les deux références (1,31 contre 1,52 °C pour la moyenne par
  station) : les conditions météo apportent de l'information au-delà de « quelle station ».
- Un réseau de neurones (`MLPRegressor`) fait mieux (1,20 °C), surtout parce qu'il capte des
  interactions (nuit × vent calme) qu'un modèle linéaire ne peut pas représenter. Il est
  sauvegardé (`modeles/mlp.joblib`) pour la comparaison, mais **n'est pas utilisé par
  l'interface** : l'énoncé limite le modèle à une régression linéaire/logistique, des k plus
  proches voisins, un arbre ou une forêt, et exclut l'apprentissage profond.
- Le découpage aléatoire donne un score meilleur (1,28 et 0,97 °C) : c'est l'effet attendu
  des heures voisines présentes des deux côtés, d'où le choix du chronologique.
- R² = 0,38 : le modèle explique une partie seulement des variations. Aucun score suspect
  (R² proche de 1) : l'importance par permutation place en tête la station, l'humidité et le
  point de rosée, pas de fuite visible.

**Constats sur les données** (écart moyen selon l'heure, entraînement) :

- L'îlot de chaleur est surtout **nocturne** : pour les trois références, l'écart est maximal
  entre 2 h et 4 h et minimal entre 12 h et 16 h.
- Les références ne se comportent pas pareil : écart moyen de +0,25 °C avec Trudeau, +0,52 °C
  avec St-Hubert et **+2,04 °C avec Mirabel** (jusqu'à +3,2 °C la nuit).

**Limites :**

- Une partie de l'écart avec Mirabel (42 km au nord, rural) vient de la distance et non de la
  ville : il reste d'environ +2,4 °C même par nuit venteuse.
- McTavish est une seule station : elle représente le centre-ville, pas toute l'île.
- Une seule année (2025) : une année exceptionnelle pèserait sur le modèle.
- Une mesure laissée vide est remplacée par la médiane, ce qui rend la prédiction moins précise.
- L'erreur typique (± 1,3 °C) est du même ordre que l'écart moyen avec Trudeau et St-Hubert :
  pour ces deux références, la prédiction indique surtout une tendance.

## Direction du vent en 8 points

ECCC donne la direction en dizaines de degrés (1 à 36). `direction_8_points` la convertit en
N, NE, E, SE, S, SO, O ou NO avec `int(dizaines / 4.5 + 0.5) % 8` : chaque secteur fait 45°
(4,5 dizaines) et est centré sur sa direction, le `+ 0.5` arrondit au secteur le plus proche
et le `% 8` ramène 360° sur N (le secteur N va de 337,5° à 22,5°).

## Outils du chapitre 7

- **Générateur :** `generer_mois` (`src/telechargement.py`) produit un triplet (station, année,
  mois) à la fois avec `yield`, pour télécharger les fichiers un par un sans construire la liste.
- **Décorateur :** `@chronometrer` (`src/modele.py`) mesure la durée de chaque entraînement
  sans toucher au code de `ajuster`, et la range dans le JSON de métadonnées.
- **Lambda :** `key=lambda paire: paire[1]` (`importance_variables`) trie les variables de la
  plus à la moins importante.

## Documentation consultée

- pandas — `DataFrame.pivot_table` :
  <https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.pivot_table.html>
- pandas — `merge` (jointure interne de l'appariement) :
  <https://pandas.pydata.org/docs/reference/api/pandas.merge.html>
- scikit-learn — Pipelines et `ColumnTransformer` :
  <https://scikit-learn.org/stable/modules/compose.html>
- scikit-learn — importance par permutation :
  <https://scikit-learn.org/stable/modules/permutation_importance.html>
- Streamlit — mise en cache (`st.cache_resource`) :
  <https://docs.streamlit.io/develop/concepts/architecture/caching>
- Streamlit — thème et polices :
  <https://docs.streamlit.io/develop/concepts/configuration/theming>
- Matplotlib — `pyplot.subplots` :
  <https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.subplots.html>

## Licences

- Données : Licence du gouvernement ouvert – Canada (ECCC).
- Police Inter : SIL Open Font License 1.1 (`src/static/Inter-OFL.txt`).
- Police Cinzel (titres) : SIL Open Font License 1.1 (`src/static/Cinzel-OFL.txt`).

## Voir aussi

- [DECISIONS.md](DECISIONS.md) — fiche de décisions
- [JOURNAL_IA.md](JOURNAL_IA.md) — journal d'utilisation de l'IA
