# Ouranos — prédire la température dans 3 heures

Projet 2 du cours INF1007 (A2026). Ouranos prédit la température qu'il fera dans 3 heures
à partir des conditions météo actuelles mesurées autour de Montréal, grâce à un modèle
entraîné sur les données horaires d'Environnement et Changement climatique Canada.

> Outil pédagogique : les prédictions ne remplacent pas les prévisions officielles
> d'Environnement Canada.

**Équipe :** _à compléter_

## Jeu de données

- **Source :** Environnement et Changement climatique Canada, données climatiques historiques
  horaires — <https://climat.meteo.gc.ca>
- **Stations :** _à compléter_ (ex. MONTREAL INTL A, St-Hubert, Mirabel, McTavish)
- **Période :** _à compléter_ (ex. 1ᵉʳ janvier au 31 décembre 2024), téléchargée le _date_
- **Licence :** [Licence du gouvernement ouvert – Canada](https://ouvert.canada.ca/fr/licence-du-gouvernement-ouvert-canada)
- **Taille :** _à compléter_ lignes, _à compléter_ colonnes

## Installation

```bash
git clone <url-du-depot>
cd Ouranos
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

## Utilisation

L'interface est faite avec [Streamlit](https://streamlit.io).

**En local :**

```bash
python src/telechargement.py     # (facultatif) retélécharger les données brutes
streamlit run src/main.py        # ouvre http://localhost:8501
```

**En ligne :** _lien Streamlit Community Cloud à compléter_. Sur cette version, l'historique
n'est pas conservé lors des redémarrages du serveur.

## Tests

```bash
pytest
coverage run -m pytest && coverage report
```

**Couverture :** _à compléter_

## Structure du code

```
donnees/       jeu de données (CSV)
modeles/       modèle entraîné et métadonnées JSON
figures/       graphiques d'exploration
historique/    historique des prédictions
src/           code source (données, modèle, exceptions, interface, main)
tests/         tests pytest
```

## Résultats du modèle

| Modèle | MAE (°C) | RMSE (°C) |
|---|---|---|
| Référence : moyenne | _à compléter_ | _à compléter_ |
| Référence : persistance | _à compléter_ | _à compléter_ |
| _Modèle retenu_ | _à compléter_ | _à compléter_ |

_Analyse et limites : à compléter._

## Outil du chapitre 7

_À compléter (une phrase)._

## Documentation consultée

- pandas : _à compléter_
- scikit-learn : _à compléter_
- Streamlit : _à compléter_ (ex. <https://docs.streamlit.io>)

## Voir aussi

- [DECISIONS.md](DECISIONS.md) — fiche de décisions
- [JOURNAL_IA.md](JOURNAL_IA.md) — journal d'utilisation de l'IA
