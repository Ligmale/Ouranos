# Fiche de décisions — Ouranos

Chaque choix important est présenté à l'auxiliaire avant d'être appliqué.

| Choix | Options envisagées | Choix retenu et justification | Validé |
|---|---|---|---|
| Domaine | Météo Montréal ; Rain in Australia ; santé, finance, sport | **Météo, région de Montréal** : données publiques, plausibilité facile à juger, domaine non sensible | A (2026-10-23) |
| Jeu de données | Horaire ou quotidien ; 2024 ou 2025 ; YUL seule ; stations McGill ; aéroports | **ECCC horaire 2025**, McTavish + YUL, St-Hubert, Mirabel : le quotidien n'a ni humidité ni pression ; température manquante < 0,4 % | B (2026-10-23) |
| Cible | Température dans 3 h ; écart à la même heure ; écart dans 3 h ; satellite INSPQ | **Écart McTavish − référence, même heure** (îlot de chaleur, ≈ 26 000 lignes) : phénomène réel (+4,2 °C par nuit calme contre Mirabel) ; la persistance rendait « dans 3 h » trop facile | C (2026-10-23) |
| Variables d'entrée | Conditions de la référence ; de YUL seule ; des 3 aéroports ; + McTavish | **Conditions de la station de référence** + saison, moment, vent en 8 points, tendance de pression ; McTavish exclue (fuite de la cible) | — |
| Valeurs manquantes | Retirer ; imputer | Lignes sans cible **retirées** ; variables imputées par `SimpleImputer` dans le `Pipeline` (médiane ; catégorie « Inconnu ») | — |
| Métrique | MAE ; MAE + RMSE ; R² | **RMSE officielle** (calculée avec NumPy, comparée à scikit-learn dans un test ; pénalise les grosses erreurs, marge « ± » de l'interface) + MAE + R² (score suspect). Validée C le 2026-10-23 avec la MAE principale, changée par l'équipe le 2026-11-17 | — |
| Références | — | Moyenne de l'écart, et moyenne par station de référence | — |
| Découpage | Aléatoire ; chronologique | Aléatoire (exigé) + **chronologique** (~6 derniers jours de chaque mois) ; **score officiel = chronologique**, l'aléatoire est trop optimiste | — |
| Modèle | Linéaire ; arbre ; forêt ; réseau de neurones | **Réseau de neurones** (`MLPRegressor`, couches 50 et 25, hyperparamètres fixes) + linéaire en comparaison, dans un seul `Pipeline` ; capte les interactions (nuit × vent calme) ; importance par permutation. Forêt validée C le 2026-10-23, changée par l'équipe le 2026-11-17 | — |
| Interface | Streamlit ; Tkinter ; Gradio ; Cloud ; Docker | **Streamlit en local** : peu de code, `st.pyplot` ; Cloud et Docker non exigés | D (2026-10-23) |
| Bibliothèque | Polars ; pandas | **pandas** partout, y compris en entrée de scikit-learn | — |
| Appariement | Jointure interne ; externe | **Interne** sur `Date/Time (LST)` : une heure d'un seul côté n'a pas de cible | — |
| Intervalles numériques | Limites physiques ; min/max d'entraînement | **Limites physiques** dans le JSON + min/max d'entraînement pour avertir | — |
| Direction du vent | Garder les degrés ; 8 points cardinaux | **8 points** : `int(dizaines / 4,5 + 0,5) % 8` — secteurs de 45° centrés sur chaque direction, le `% 8` ramène 360° sur N | — |

**Limite connue :** une partie de l'écart avec Mirabel (42 km au nord) vient de la distance, pas de la ville (+2,4 °C même par nuit venteuse).

**Maquette papier :** _à faire_
