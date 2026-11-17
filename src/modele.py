"""Entraînement, évaluation, sauvegarde et prédiction du modèle de l'écart de température.

- Découpages : aléatoire (exigé) et chronologique (score officiel).
- Un seul Pipeline scikit-learn : imputation, mise à l'échelle, encodage, régresseur.
- Comparaison : réseau de neurones (MLP, retenu), régression linéaire, deux scores de référence.
- Métadonnées JSON : tout ce dont l'interface a besoin, sans relire les données.
- predire() : valide une saisie avec les classes Variable et retourne l'écart prédit.
"""

import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from typing import Any, cast

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

from donnees import COLONNE_DATE, VariableCategorielle, VariableNumerique, moment_journee, saison
from exceptions import DonneeInvalideError, ErreurPredictionError, ModeleNonTrouveError

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# Toutes mesurées à la station de référence : aucune mesure de McTavish (fuite de la cible).
CARACTERISTIQUES_NUMERIQUES = [
    "Temp (°C)",
    "Dew Point Temp (°C)",
    "Rel Hum (%)",
    "Stn Press (kPa)",
    "Wind Spd (km/h)",
    "Visibility (km)",
]
CARACTERISTIQUES_CATEGORIELLES = [
    "Station Name",
    "saison",
    "moment_journee",
    "direction_8_points",
    "tendance_pression",
]
CIBLE = "ecart"

# Valeur donnée aux catégories manquantes ; l'interface peut la proposer pour ces colonnes.
VALEUR_INCONNUE = "Inconnu"
CATEGORIES_FACULTATIVES = ["direction_8_points", "tendance_pression"]
# Champs numériques qu'on peut laisser vides (remplacés par la médiane d'entraînement).
# La température reste obligatoire : elle sert à estimer la température du centre-ville.
NUMERIQUES_FACULTATIVES = [c for c in CARACTERISTIQUES_NUMERIQUES if c != "Temp (°C)"]

# Limites physiques (validation de la saisie), larges mais réalistes pour Montréal.
LIMITES_PHYSIQUES = {
    "Temp (°C)": (-50.0, 45.0),
    "Dew Point Temp (°C)": (-60.0, 35.0),
    "Rel Hum (%)": (0.0, 100.0),
    "Stn Press (kPa)": (90.0, 110.0),
    "Wind Spd (km/h)": (0.0, 200.0),
    "Visibility (km)": (0.0, 100.0),
}

JOURS_TEST_PAR_MOIS = 6
GRAINE = 42

DOSSIER_MODELES = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "modeles"))
NOM_MODELE = "modele_ouranos.joblib"
NOM_METADONNEES = "metadonnees.json"


# ---------------------------------------------------------------------------
# Outil : décorateur de chronométrage
# ---------------------------------------------------------------------------


def chronometrer(fonction: Callable) -> Callable:
    """Décorateur qui mesure la durée d'un appel, sans rien afficher.

    Entrée : la fonction à chronométrer.
    Sortie : une fonction enveloppe ; après chaque appel, sa durée en secondes est
        dans l'attribut « derniere_duree » de l'enveloppe.
    Échec : aucun (les exceptions de la fonction remontent telles quelles).
    """

    @wraps(fonction)
    def enveloppe(*args: Any, **kwargs: Any) -> Any:
        debut = time.perf_counter()
        resultat = fonction(*args, **kwargs)
        enveloppe.derniere_duree = time.perf_counter() - debut  # type: ignore[attr-defined]
        return resultat

    enveloppe.derniere_duree = 0.0  # type: ignore[attr-defined]
    return enveloppe


# ---------------------------------------------------------------------------
# Métriques
# ---------------------------------------------------------------------------


def calculer_rmse_numpy(y_reel: np.ndarray, y_predit: np.ndarray) -> float:
    """Calcule la racine de l'erreur quadratique moyenne avec NumPy (calcul vectorisé).

    Entrées : valeurs réelles et prédites, de même taille.
    Sortie : la RMSE, dans l'unité de la cible (°C).
    Échec : DonneeInvalideError si les tailles diffèrent ou si les tableaux sont vides.
    """
    y_reel = np.asarray(y_reel, dtype=float)
    y_predit = np.asarray(y_predit, dtype=float)
    if y_reel.shape != y_predit.shape:
        raise DonneeInvalideError("Les tableaux réel et prédit ne sont pas de la même taille.")
    if y_reel.size == 0:
        raise DonneeInvalideError("Impossible de calculer la RMSE sur des tableaux vides.")
    return float(np.sqrt(np.mean((y_reel - y_predit) ** 2)))


def calculer_scores(y_reel: np.ndarray, y_predit: np.ndarray) -> dict[str, float]:
    """Regroupe les trois métriques du projet.

    Entrées : valeurs réelles et prédites.
    Sortie : {"rmse", "mae", "r2"} ; la RMSE (officielle) est calculée avec NumPy.
    Échec : DonneeInvalideError (voir calculer_rmse_numpy).
    """
    return {
        "rmse": calculer_rmse_numpy(y_reel, y_predit),
        "mae": float(mean_absolute_error(y_reel, y_predit)),
        "r2": float(r2_score(y_reel, y_predit)),
    }


# ---------------------------------------------------------------------------
# Découpages
# ---------------------------------------------------------------------------


def verifier_tableau(tableau: pd.DataFrame) -> None:
    """Vérifie que le tableau final contient la date, la cible et les caractéristiques.

    Entrée : le tableau final (sortie de donnees.construire_tableau).
    Sortie : aucune.
    Échec : DonneeInvalideError si le tableau est vide ou s'il manque des colonnes.
    """
    if tableau.empty:
        raise DonneeInvalideError("Le tableau fourni est vide.")
    requises = [COLONNE_DATE, CIBLE, *CARACTERISTIQUES_NUMERIQUES, *CARACTERISTIQUES_CATEGORIELLES]
    manquantes = [c for c in requises if c not in tableau.columns]
    if manquantes:
        raise DonneeInvalideError(f"Colonnes manquantes dans le tableau : {manquantes}")


def decouper_chronologique(
    tableau: pd.DataFrame, jours_test: int = JOURS_TEST_PAR_MOIS
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Met en test les derniers jours de chaque mois, le reste en entraînement.

    Le découpage se fait sur la date : les lignes d'une même heure (une par référence)
    tombent toujours du même côté.

    Entrées : le tableau avec « Date/Time (LST) », le nombre de jours de test par mois.
    Sortie : (entraînement, test).
    Échec : DonneeInvalideError si la date est absente ou si un des côtés est vide.
    """
    if COLONNE_DATE not in tableau.columns:
        raise DonneeInvalideError(f"Colonne « {COLONNE_DATE} » absente du tableau.")
    date = pd.to_datetime(tableau[COLONNE_DATE])
    # Ex. 6 jours : du 26 au 31 en janvier, du 23 au 28 en février.
    en_test = date.dt.day > date.dt.days_in_month - jours_test
    entrainement, test = tableau.loc[~en_test], tableau.loc[en_test]
    if entrainement.empty or test.empty:
        raise DonneeInvalideError("Le découpage chronologique laisse un côté vide.")
    return entrainement, test


def decouper_aleatoire(tableau: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Découpage aléatoire exigé par l'énoncé (20 % en test, graine fixe).

    Entrée : le tableau final.
    Sortie : (entraînement, test).
    Échec : ValueError de scikit-learn si le tableau a moins de 2 lignes.
    """
    entrainement, test = train_test_split(tableau, test_size=0.2, random_state=GRAINE)
    return cast(pd.DataFrame, entrainement), cast(pd.DataFrame, test)


def separer_x_y(tableau: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Sépare les caractéristiques (X) de la cible (y).

    Entrée : un tableau avec les caractéristiques et la cible.
    Sortie : (X, y).
    Échec : KeyError si une colonne est absente (vérifier avec verifier_tableau avant).
    """
    x = tableau.loc[:, CARACTERISTIQUES_NUMERIQUES + CARACTERISTIQUES_CATEGORIELLES]
    y = cast(pd.Series, tableau[CIBLE])
    return x, y


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


def none_en_nan(x: pd.DataFrame) -> pd.DataFrame:
    """Remplace None par NaN : SimpleImputer ne reconnaît pas None comme manquant.

    Entrée : les colonnes catégorielles.
    Sortie : copie de type objet, NaN à la place de None.
    Échec : aucun.
    """
    x = pd.DataFrame(x).astype(object)
    return x.where(x.notna(), np.nan)


def construire_pipeline(regresseur: Any) -> Pipeline:
    """Assemble le prétraitement et un régresseur dans un seul Pipeline.

    Numériques : médiane puis mise à l'échelle (indispensable pour le MLP).
    Catégorielles : manquant → « Inconnu », puis encodage one-hot.
    Tout est ajusté pendant fit, donc sur l'entraînement seulement (pas de fuite).

    Entrée : un régresseur scikit-learn non entraîné.
    Sortie : le Pipeline non entraîné.
    Échec : aucun.
    """
    numerique = Pipeline([
        ("imputation", SimpleImputer(strategy="median")),
        ("echelle", StandardScaler()),
    ])
    categorielle = Pipeline([
        ("none_en_nan", FunctionTransformer(none_en_nan)),
        ("imputation", SimpleImputer(strategy="constant", fill_value=VALEUR_INCONNUE)),
        ("encodage", OneHotEncoder(handle_unknown="ignore")),
    ])
    pretraitement = ColumnTransformer([
        ("num", numerique, CARACTERISTIQUES_NUMERIQUES),
        ("cat", categorielle, CARACTERISTIQUES_CATEGORIELLES),
    ])
    return Pipeline([("pretraitement", pretraitement), ("regresseur", regresseur)])


def creer_mlp() -> MLPRegressor:
    """Réseau de neurones retenu, hyperparamètres fixes (voir DECISIONS.md).

    Sortie : MLPRegressor non entraîné, graine fixe pour des résultats reproductibles.
    """
    return MLPRegressor(hidden_layer_sizes=(50, 25), max_iter=500, early_stopping=True, random_state=GRAINE)


@chronometrer
def ajuster(pipeline: Pipeline, entrainement: pd.DataFrame) -> Pipeline:
    """Entraîne un Pipeline (durée mesurée par @chronometrer).

    Entrées : le Pipeline et le tableau d'entraînement.
    Sortie : le même Pipeline, entraîné.
    Échec : ValueError de scikit-learn si les données sont inutilisables.
    """
    x, y = separer_x_y(entrainement)
    return pipeline.fit(x, y)


def evaluer(pipeline: Pipeline, test: pd.DataFrame) -> dict[str, float]:
    """Évalue un Pipeline entraîné sur le tableau de test.

    Entrées : le Pipeline entraîné et le tableau de test.
    Sortie : {"rmse", "mae", "r2"}.
    Échec : DonneeInvalideError si le test est vide.
    """
    x, y = separer_x_y(test)
    return calculer_scores(y.to_numpy(), pipeline.predict(x))


# ---------------------------------------------------------------------------
# Scores de référence, importance des variables
# ---------------------------------------------------------------------------


def scores_reference(entrainement: pd.DataFrame, test: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Scores de deux prédictions sans apprentissage, calculées sur l'entraînement.

    - moyenne_globale : toujours l'écart moyen de l'entraînement ;
    - moyenne_par_station : l'écart moyen de la station de référence de la ligne
      (moyenne globale pour une station absente de l'entraînement).

    Entrées : tableaux d'entraînement et de test (avec « Station Name » et la cible).
    Sortie : {nom de la référence: {"rmse", "mae", "r2"}}.
    Échec : DonneeInvalideError si le test est vide.
    """
    y_entrainement = cast(pd.Series, entrainement[CIBLE])
    y_test = cast(pd.Series, test[CIBLE]).to_numpy()
    moyenne = float(y_entrainement.mean())
    par_station = cast(pd.Series, y_entrainement.groupby(entrainement["Station Name"]).mean()).to_dict()
    prediction_station = cast(pd.Series, test["Station Name"]).map(par_station).fillna(moyenne).to_numpy()
    return {
        "moyenne_globale": calculer_scores(y_test, np.full(len(y_test), moyenne)),
        "moyenne_par_station": calculer_scores(y_test, prediction_station),
    }


def importance_variables(pipeline: Pipeline, test: pd.DataFrame) -> dict[str, float]:
    """Importance par permutation : hausse de la RMSE quand on mélange une colonne.

    Marche pour n'importe quel modèle, sur les colonnes d'origine (avant one-hot).

    Entrées : le Pipeline entraîné et le tableau de test.
    Sortie : {colonne: hausse moyenne de la RMSE en °C}, de la plus à la moins importante.
    Échec : ValueError de scikit-learn si le test est vide.
    """
    x, y = separer_x_y(test)
    resultat = permutation_importance(
        pipeline, x, y, scoring="neg_root_mean_squared_error", n_repeats=5, random_state=GRAINE
    )
    importances = dict(zip(x.columns, (float(v) for v in resultat["importances_mean"])))
    return dict(sorted(importances.items(), key=lambda paire: paire[1], reverse=True))


def ecart_moyen_par_heure(tableau: pd.DataFrame) -> dict[str, list[float | None]]:
    """Écart moyen pour chaque heure (0 à 23), par station de référence.

    Entrée : un tableau avec la date, « Station Name » et la cible.
    Sortie : {station: 24 valeurs}, None pour une heure sans donnée.
    Échec : DonneeInvalideError si la date est absente.
    """
    if COLONNE_DATE not in tableau.columns:
        raise DonneeInvalideError(f"Colonne « {COLONNE_DATE} » absente du tableau.")
    avec_heure = tableau.assign(heure=pd.to_datetime(tableau[COLONNE_DATE]).dt.hour)
    # Une ligne par station, une colonne par heure (0 à 23) ; NaN pour une heure sans donnée.
    moyennes = avec_heure.pivot_table(index="Station Name", columns="heure", values=CIBLE, aggfunc="mean")
    moyennes = moyennes.reindex(columns=range(24))
    resultat: dict[str, list[float | None]] = {}
    for station, par_heure in moyennes.iterrows():
        resultat[str(station)] = [None if pd.isna(v) else round(float(v), 3) for v in par_heure]
    return resultat


# ---------------------------------------------------------------------------
# Métadonnées
# ---------------------------------------------------------------------------


def decrire_variables(entrainement: pd.DataFrame) -> dict[str, dict]:
    """Décrit chaque variable d'entrée pour construire l'interface et valider la saisie.

    Entrée : le tableau d'entraînement.
    Sortie : {"numeriques": {colonne: {min/max physiques et d'entraînement}},
              "categorielles": {colonne: valeurs permises}}.
    Échec : aucun.
    """
    numeriques = {}
    for colonne in CARACTERISTIQUES_NUMERIQUES:
        minimum, maximum = LIMITES_PHYSIQUES[colonne]
        valeurs = cast(pd.Series, entrainement[colonne])
        numeriques[colonne] = {
            "min_physique": minimum,
            "max_physique": maximum,
            "min_entrainement": float(valeurs.min()),
            "max_entrainement": float(valeurs.max()),
        }
    categorielles = {}
    for colonne in CARACTERISTIQUES_CATEGORIELLES:
        valeurs = sorted(str(v) for v in entrainement[colonne].dropna().unique())
        if colonne in CATEGORIES_FACULTATIVES:
            valeurs.append(VALEUR_INCONNUE)
        categorielles[colonne] = valeurs
    return {"numeriques": numeriques, "categorielles": categorielles}


# ---------------------------------------------------------------------------
# Entraînement complet
# ---------------------------------------------------------------------------


def comparer_modeles(entrainement: pd.DataFrame, test: pd.DataFrame) -> tuple[Pipeline, dict]:
    """Entraîne la régression linéaire et le MLP sur un découpage et les compare aux références.

    Entrées : tableaux d'entraînement et de test.
    Sortie : (le Pipeline MLP entraîné, {nom: scores} pour les 4 approches).
    Échec : DonneeInvalideError si un tableau est vide.
    """
    lineaire = ajuster(construire_pipeline(LinearRegression()), entrainement)
    mlp = ajuster(construire_pipeline(creer_mlp()), entrainement)
    scores = {
        **scores_reference(entrainement, test),
        "regression_lineaire": evaluer(lineaire, test),
        "mlp": evaluer(mlp, test),
    }
    return mlp, scores


def entrainer(tableau: pd.DataFrame) -> tuple[Pipeline, dict]:
    """Entraîne, évalue sur les deux découpages et prépare les métadonnées.

    Le modèle retourné est le MLP entraîné sur l'entraînement chronologique : la RMSE
    officielle (chronologique) décrit exactement ce modèle.

    Entrée : le tableau final (sortie de donnees.construire_tableau).
    Sortie : (Pipeline MLP entraîné, métadonnées prêtes pour le JSON).
    Échec : DonneeInvalideError si le tableau est vide, incomplet ou mal découpé.
    """
    verifier_tableau(tableau)
    _, scores_aleatoire = comparer_modeles(*decouper_aleatoire(tableau))
    entrainement, test = decouper_chronologique(tableau)
    mlp, scores_chrono = comparer_modeles(entrainement, test)
    duree: float = getattr(ajuster, "derniere_duree")

    metadonnees = {
        "type_modele": "MLPRegressor (réseau de neurones), hidden_layer_sizes=(50, 25)",
        "date_entrainement": datetime.now().isoformat(timespec="seconds"),
        "duree_entrainement_s": round(duree, 2),
        "cible": CIBLE,
        "caracteristiques_numeriques": CARACTERISTIQUES_NUMERIQUES,
        "caracteristiques_categorielles": CARACTERISTIQUES_CATEGORIELLES,
        "valeur_inconnue": VALEUR_INCONNUE,
        **decrire_variables(entrainement),
        "metrique_officielle": "rmse",
        "rmse_officielle": scores_chrono["mlp"]["rmse"],
        "nb_lignes": {"entrainement": len(entrainement), "test": len(test)},
        "scores": {"chronologique": scores_chrono, "aleatoire": scores_aleatoire},
        "importance_variables": importance_variables(mlp, test),
        "ecart_moyen_par_heure": ecart_moyen_par_heure(entrainement),
    }
    return mlp, metadonnees


# ---------------------------------------------------------------------------
# Sauvegarde et chargement
# ---------------------------------------------------------------------------


def sauvegarder_artefacts(
    pipeline: Pipeline, metadonnees: dict, dossier: str = DOSSIER_MODELES
) -> tuple[str, str]:
    """Sauvegarde le Pipeline (joblib) et les métadonnées (JSON).

    Entrées : le Pipeline entraîné, les métadonnées, le dossier de destination.
    Sortie : (chemin du modèle, chemin du JSON).
    Échec : OSError si le dossier ne peut pas être créé ou écrit.
    """
    os.makedirs(dossier, exist_ok=True)
    chemin_modele = os.path.join(dossier, NOM_MODELE)
    chemin_json = os.path.join(dossier, NOM_METADONNEES)
    with open(chemin_modele, "wb") as fichier:
        joblib.dump(pipeline, fichier)
    with open(chemin_json, "w", encoding="utf-8") as fichier:
        json.dump(metadonnees, fichier, ensure_ascii=False, indent=2)
    return chemin_modele, chemin_json


def charger_artefacts(dossier: str = DOSSIER_MODELES) -> tuple[Pipeline, dict]:
    """Charge le Pipeline et les métadonnées sauvegardés (jamais de réentraînement).

    Entrée : le dossier des modèles.
    Sortie : (Pipeline entraîné, métadonnées).
    Échec : ModeleNonTrouveError si un des deux fichiers est absent.
    """
    chemin_modele = os.path.join(dossier, NOM_MODELE)
    chemin_json = os.path.join(dossier, NOM_METADONNEES)
    for chemin in (chemin_modele, chemin_json):
        if not os.path.exists(chemin):
            raise ModeleNonTrouveError(
                f"Fichier introuvable : {os.path.normpath(chemin)}. Lancer d'abord « python src/modele.py »."
            )
    with open(chemin_modele, "rb") as fichier:
        pipeline = joblib.load(fichier)
    with open(chemin_json, encoding="utf-8") as fichier:
        metadonnees = json.load(fichier)
    return pipeline, metadonnees


# ---------------------------------------------------------------------------
# Prédiction
# ---------------------------------------------------------------------------


def creer_variables(metadonnees: dict) -> dict[str, VariableNumerique | VariableCategorielle]:
    """Crée une Variable par champ de saisie à partir des métadonnées.

    Saison et moment de la journée ne sont pas saisis : predire() les calcule depuis la date.

    Entrée : les métadonnées (voir decrire_variables).
    Sortie : {colonne: Variable}.
    Échec : KeyError si les métadonnées sont incomplètes.
    """
    variables: dict[str, VariableNumerique | VariableCategorielle] = {}
    for colonne, bornes in metadonnees["numeriques"].items():
        variables[colonne] = VariableNumerique(colonne, bornes["min_physique"], bornes["max_physique"])
    for colonne, valeurs in metadonnees["categorielles"].items():
        if colonne not in ("saison", "moment_journee"):
            variables[colonne] = VariableCategorielle(colonne, valeurs)
    return variables


def preparer_saisie(
    saisie: dict, date_heure: datetime, variables: dict[str, VariableNumerique | VariableCategorielle]
) -> pd.DataFrame:
    """Valide une saisie et la met sous la forme d'une ligne pour le Pipeline.

    Entrées : {colonne: valeur saisie} pour chaque champ, la date et l'heure de la mesure,
        les variables qui valident chaque champ (voir creer_variables).
    Sortie : un DataFrame d'une ligne avec toutes les caractéristiques ; un champ numérique
        facultatif laissé vide devient NaN (le Pipeline le remplace par la médiane).
    Échec : DonneeInvalideError si une valeur manque, n'est pas valide ou est hors limites.
    """
    ligne: dict[str, object] = {}
    for colonne, variable in variables.items():
        if colonne not in saisie:
            raise DonneeInvalideError(f"{colonne} : valeur absente de la saisie.")
        if colonne in NUMERIQUES_FACULTATIVES and est_vide(saisie[colonne]):
            ligne[colonne] = np.nan
        else:
            ligne[colonne] = variable.valider(saisie[colonne])
    ligne["saison"] = saison(date_heure.month)
    ligne["moment_journee"] = moment_journee(date_heure.hour)
    return pd.DataFrame([ligne]).loc[:, CARACTERISTIQUES_NUMERIQUES + CARACTERISTIQUES_CATEGORIELLES]


def est_vide(valeur: object) -> bool:
    """Indique si une saisie est vide (None, texte vide ou seulement des espaces).

    Entrée : la valeur saisie.
    Sortie : True si elle est vide.
    """
    return valeur is None or str(valeur).strip() == ""


def hors_valeurs_vues(saisie: pd.DataFrame, metadonnees: dict) -> list[str]:
    """Liste les variables numériques hors du min/max vu à l'entraînement (avertissement).

    Entrées : la ligne préparée par preparer_saisie, les métadonnées.
    Sortie : les noms des colonnes concernées (liste vide si tout est dans les valeurs vues) ;
        une valeur manquante (NaN) n'est pas signalée.
    Échec : KeyError si les métadonnées sont incomplètes.
    """
    hors = []
    for colonne, bornes in metadonnees["numeriques"].items():
        valeur = float(saisie[colonne].iloc[0])
        if not np.isnan(valeur) and not bornes["min_entrainement"] <= valeur <= bornes["max_entrainement"]:
            hors.append(colonne)
    return hors


def predire(pipeline: Pipeline, saisie: pd.DataFrame) -> float:
    """Prédit l'écart McTavish − référence pour une ligne préparée.

    Entrées : le Pipeline entraîné, la ligne retournée par preparer_saisie.
    Sortie : l'écart prédit en °C.
    Échec : ErreurPredictionError si le Pipeline refuse la ligne.
    """
    try:
        return float(pipeline.predict(saisie)[0])
    except (ValueError, KeyError) as erreur:
        raise ErreurPredictionError(f"Le modèle n'a pas pu prédire : {erreur}") from erreur


@dataclass(frozen=True)
class Prediction:
    """Résultat d'une prédiction (immuable)."""

    ecart: float
    temperature_reference: float
    hors_valeurs_vues: list[str]
    champs_vides: list[str]

    @property
    def temperature_centre_ville(self) -> float:
        """Température estimée à McTavish : température de la référence + écart prédit."""
        return self.temperature_reference + self.ecart


class Predicteur:
    """Modèle prêt à l'emploi pour l'interface.

    Composition : un Predicteur contient le Pipeline entraîné, ses métadonnées et une
    Variable par champ de saisie. Les attributs sont privés (encapsulation) : on les lit
    par des propriétés, on ne les remplace pas.
    """

    def __init__(self, pipeline: Pipeline, metadonnees: dict) -> None:
        """Entrées : le Pipeline entraîné et ses métadonnées.
        Échec : KeyError si les métadonnées sont incomplètes.
        """
        self._pipeline = pipeline
        self._metadonnees = metadonnees
        self._variables = creer_variables(metadonnees)

    @classmethod
    def depuis_dossier(cls, dossier: str = DOSSIER_MODELES) -> "Predicteur":
        """Crée un Predicteur à partir des fichiers sauvegardés (jamais de réentraînement).

        Entrée : le dossier des modèles.
        Sortie : le Predicteur.
        Échec : ModeleNonTrouveError si un des fichiers est absent.
        """
        return cls(*charger_artefacts(dossier))

    @property
    def metadonnees(self) -> dict:
        """Métadonnées du modèle (stations, bornes, catégories, scores…)."""
        return self._metadonnees

    @property
    def variables(self) -> dict[str, VariableNumerique | VariableCategorielle]:
        """Copie du dictionnaire des variables : le modifier ne change pas le Predicteur."""
        return dict(self._variables)

    @property
    def rmse(self) -> float:
        """RMSE officielle (découpage chronologique), en °C : la marge d'erreur affichée."""
        return float(self._metadonnees["rmse_officielle"])

    def predire(self, saisie: dict, date_heure: datetime) -> Prediction:
        """Valide la saisie et prédit l'écart McTavish − référence.

        Entrées : {colonne: valeur saisie}, la date et l'heure de la mesure.
        Sortie : la Prediction (écart, température de référence, avertissements).
        Échec : DonneeInvalideError si la saisie est invalide ;
            ErreurPredictionError si le Pipeline refuse la ligne.
        """
        ligne = preparer_saisie(saisie, date_heure, self._variables)
        return Prediction(
            ecart=predire(self._pipeline, ligne),
            temperature_reference=float(ligne.loc[0, "Temp (°C)"]),
            hors_valeurs_vues=hors_valeurs_vues(ligne, self._metadonnees),
            champs_vides=[c for c in NUMERIQUES_FACULTATIVES if pd.isna(ligne.loc[0, c])],
        )

    def __repr__(self) -> str:
        return f"Predicteur({self._metadonnees['type_modele']!r}, RMSE {self.rmse:.2f} °C, {len(self._variables)} variables)"


# ---------------------------------------------------------------------------
# Script d'entraînement : python src/modele.py (après python src/telechargement.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from donnees import construire_tableau
    # Importer depuis « modele » (pas __main__) : joblib enregistre none_en_nan sous ce nom
    # de module, sinon l'interface ne pourrait pas recharger le Pipeline.
    from modele import entrainer, sauvegarder_artefacts
    from station import Station

    ID_MCTAVISH = 10761
    ID_REFERENCES = [51157, 48374, 49608]  # YUL, St-Hubert, Mirabel

    tableau_final = construire_tableau(Station(ID_MCTAVISH), [Station(i) for i in ID_REFERENCES])
    modele, meta = entrainer(tableau_final)
    chemins = sauvegarder_artefacts(modele, meta)

    print(f"{len(tableau_final)} lignes, entraînement du MLP : {meta['duree_entrainement_s']} s")
    for decoupage, scores in meta["scores"].items():
        print(f"\nDécoupage {decoupage} :")
        for nom, valeurs in scores.items():
            print(f"  {nom:22} RMSE {valeurs['rmse']:.3f}  MAE {valeurs['mae']:.3f}  R² {valeurs['r2']:.3f}")
    print("\nImportance des variables (hausse de la RMSE) :")
    for colonne, valeur in meta["importance_variables"].items():
        print(f"  {colonne:22} {valeur:.3f}")
    print(f"\nSauvegardé : {chemins[0]}\n             {chemins[1]}")
