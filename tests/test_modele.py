"""Tests de src/modele.py, sans réseau ni dossier donnees/.

Le tableau est synthétique (graine fixe) : janvier et février 2025, deux stations de
référence, un écart qui dépend de la station et du vent, plus du bruit.
"""

import json
import os
from datetime import datetime
from typing import cast

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import mean_squared_error

from donnees import VariableCategorielle, VariableNumerique
from exceptions import DonneeInvalideError, ModeleNonTrouveError
from modele import (
    CARACTERISTIQUES_CATEGORIELLES,
    CARACTERISTIQUES_NUMERIQUES,
    MODELE_RETENU,
    VALEUR_INCONNUE,
    calculer_rmse_numpy,
    Predicteur,
    chronometrer,
    construire_pipeline,
    decouper_chronologique,
    ecart_moyen_par_heure,
    entrainer,
    preparer_saisie,
    sauvegarder_artefacts,
    temperatures_moyennes_par_heure,
    scores_reference,
)
from sklearn.linear_model import LinearRegression


def faux_tableau(nb_jours: int = 59) -> pd.DataFrame:
    """Tableau final synthétique : une ligne par (heure, station), du 1er janvier au 28 février."""
    rng = np.random.default_rng(0)
    heures = pd.date_range("2025-01-01 00:00", periods=nb_jours * 24, freq="h")
    morceaux = []
    for station, decalage in [("MONTREAL INTL A", 1.0), ("MONTREAL MIRABEL INTL A", 3.0)]:
        n = len(heures)
        vent = rng.uniform(0, 40, n)
        direction = rng.choice(np.array(["N", "SO", "O", None], dtype=object), n)
        morceaux.append(pd.DataFrame({
            "Date/Time (LST)": heures.strftime("%Y-%m-%d %H:%M"),
            "Station Name": station,
            "Temp (°C)": rng.normal(-8, 5, n),
            "Dew Point Temp (°C)": rng.normal(-12, 5, n),
            "Rel Hum (%)": rng.uniform(40, 100, n),
            "Stn Press (kPa)": rng.normal(101, 0.8, n),
            "Wind Spd (km/h)": vent,
            "Visibility (km)": np.where(rng.random(n) < 0.05, np.nan, 24.1),
            "saison": "hiver",
            "moment_journee": [("nuit" if h < 6 else "matin" if h < 11 else "apres-midi" if h < 17 else "soir")
                               for h in heures.hour],
            "direction_8_points": direction,
            "tendance_pression": rng.choice(np.array(["hausse", "stable", "baisse", None], dtype=object), n),
            "ecart": decalage + 2.0 * (vent < 10) + rng.normal(0, 0.3, n),
        }))
    return pd.concat(morceaux, ignore_index=True)


@pytest.fixture(scope="module")
def modele_entraine() -> tuple:
    """Entraîné une seule fois pour tout le module (quelques secondes)."""
    return entrainer(faux_tableau())


def saisie_valide() -> dict:
    return {
        "Temp (°C)": "-5,0",
        "Dew Point Temp (°C)": -9.0,
        "Rel Hum (%)": 73,
        "Stn Press (kPa)": 101.0,
        "Wind Spd (km/h)": 4,
        "Visibility (km)": 24.1,
        "Station Name": "MONTREAL INTL A",
        "direction_8_points": VALEUR_INCONNUE,
        "tendance_pression": "stable",
    }


# --- RMSE NumPy -------------------------------------------------------------


def test_rmse_numpy_valeur_connue():
    # erreurs 1, 0, -1 → racine de 2/3
    assert calculer_rmse_numpy(np.array([2.0, 4.0, 6.0]), np.array([1.0, 4.0, 7.0])) == pytest.approx(0.816497, abs=1e-6)


def test_rmse_numpy_egale_sklearn():
    rng = np.random.default_rng(1)
    y_reel, y_predit = rng.normal(size=200), rng.normal(size=200)
    attendu = np.sqrt(mean_squared_error(y_reel, y_predit))
    assert calculer_rmse_numpy(y_reel, y_predit) == pytest.approx(attendu)


def test_rmse_numpy_parfaite_vaut_zero():
    y = np.array([1.5, -2.0, 3.0])
    assert calculer_rmse_numpy(y, y) == 0.0


@pytest.mark.parametrize("y_reel, y_predit", [([1.0, 2.0], [1.0]), ([], [])])
def test_rmse_numpy_erreurs(y_reel, y_predit):
    with pytest.raises(DonneeInvalideError):
        calculer_rmse_numpy(np.array(y_reel), np.array(y_predit))


# --- Découpage chronologique ------------------------------------------------


def test_decoupage_chronologique_derniers_jours():
    entrainement, test = decouper_chronologique(faux_tableau())
    jours_test = pd.to_datetime(cast(pd.Series, test["Date/Time (LST)"]))
    # janvier : 26 au 31 ; février (28 jours) : 23 au 28
    assert set(jours_test.loc[jours_test.dt.month == 1].dt.day) == {26, 27, 28, 29, 30, 31}
    assert set(jours_test.loc[jours_test.dt.month == 2].dt.day) == {23, 24, 25, 26, 27, 28}
    assert len(entrainement) + len(test) == len(faux_tableau())


def test_decoupage_chronologique_heure_jamais_des_deux_cotes():
    entrainement, test = decouper_chronologique(faux_tableau())
    assert set(entrainement["Date/Time (LST)"]).isdisjoint(test["Date/Time (LST)"])


def test_decoupage_chronologique_cote_vide():
    # 5 jours de janvier seulement : aucun jour après le 25 → test vide
    with pytest.raises(DonneeInvalideError):
        decouper_chronologique(faux_tableau(nb_jours=5))


# --- Références, écart moyen par heure ---------------------------------------


def test_reference_par_station():
    entrainement = pd.DataFrame({"Station Name": ["A", "A", "B"], "ecart": [1.0, 3.0, 5.0]})
    test = pd.DataFrame({"Station Name": ["A", "B"], "ecart": [2.0, 5.0]})
    scores = scores_reference(entrainement, test)
    # par station : prédit 2 pour A et 5 pour B → parfait
    assert scores["moyenne_par_station"]["rmse"] == pytest.approx(0.0)
    # globale : prédit 3 partout → erreurs 1 et 2
    assert scores["moyenne_globale"]["mae"] == pytest.approx(1.5)


def test_ecart_moyen_par_heure():
    tableau = pd.DataFrame({
        "Date/Time (LST)": ["2025-01-01 00:00", "2025-01-02 00:00", "2025-01-01 05:00"],
        "Station Name": ["A", "A", "A"],
        "ecart": [1.0, 3.0, 4.0],
    })
    resultat = ecart_moyen_par_heure(tableau)["A"]
    assert len(resultat) == 24
    assert resultat[0] == pytest.approx(2.0)
    assert resultat[5] == pytest.approx(4.0)
    assert resultat[1] is None


def test_temperatures_moyennes_par_heure():
    tableau = pd.DataFrame({
        "Date/Time (LST)": ["2025-01-01 00:00", "2025-01-02 00:00", "2025-07-01 00:00"],
        "Station Name": ["A", "A", "A"],
        "saison": ["hiver", "hiver", "ete"],
        "Temp (°C)": [-10.0, -6.0, 20.0],
        "ecart": [1.0, 3.0, 0.5],
    })
    resultat = temperatures_moyennes_par_heure(tableau)["A"]
    assert resultat["hiver"]["reference"][0] == pytest.approx(-8.0)
    assert resultat["hiver"]["centre_ville"][0] == pytest.approx(-6.0)  # (-9 + -3) / 2
    assert resultat["ete"]["centre_ville"][0] == pytest.approx(20.5)
    assert resultat["ete"]["reference"][1] is None
    assert set(resultat) == {"hiver", "ete"}


# --- Pipeline, entraînement, métadonnées ------------------------------------


def test_pipeline_accepte_les_manquants():
    tableau = faux_tableau(nb_jours=3)
    tableau.loc[0, "Temp (°C)"] = np.nan
    tableau.loc[1, "direction_8_points"] = None
    x = tableau[CARACTERISTIQUES_NUMERIQUES + CARACTERISTIQUES_CATEGORIELLES]
    pipeline = construire_pipeline(LinearRegression()).fit(x, tableau["ecart"])
    assert np.isfinite(pipeline.predict(x)).all()


def test_entrainer_metadonnees(modele_entraine):
    _, meta = modele_entraine
    assert meta["metrique_officielle"] == "rmse"
    assert meta["modele_retenu"] == MODELE_RETENU == "regression_lineaire"
    assert meta["rmse_officielle"] == meta["scores"]["chronologique"]["regression_lineaire"]["rmse"]
    for decoupage in ("chronologique", "aleatoire"):
        assert set(meta["scores"][decoupage]) == {
            "moyenne_globale", "moyenne_par_station", "regression_lineaire", "mlp"
        }
    for nom in ("regression_lineaire", "mlp"):
        assert set(meta["importance_variables"][nom]) == set(CARACTERISTIQUES_NUMERIQUES + CARACTERISTIQUES_CATEGORIELLES)
    assert VALEUR_INCONNUE in meta["categorielles"]["direction_8_points"]
    assert len(meta["temperatures_moyennes_par_heure"]["MONTREAL INTL A"]["hiver"]["centre_ville"]) == 24
    assert VALEUR_INCONNUE not in meta["categorielles"]["Station Name"]
    json.dumps(meta)  # tout doit être sérialisable en JSON


def test_modeles_battent_la_moyenne_globale(modele_entraine):
    scores = modele_entraine[1]["scores"]["chronologique"]
    for nom in ("regression_lineaire", "mlp"):
        assert scores[nom]["rmse"] < scores["moyenne_globale"]["rmse"]


def test_entrainer_tableau_vide():
    with pytest.raises(DonneeInvalideError):
        entrainer(pd.DataFrame())


def test_entrainer_colonne_manquante():
    with pytest.raises(DonneeInvalideError):
        entrainer(faux_tableau().drop(columns="Visibility (km)"))


# --- Sauvegarde et chargement -----------------------------------------------


def test_sauvegarde_puis_chargement(modele_entraine, tmp_path):
    pipelines, meta = modele_entraine
    chemins = sauvegarder_artefacts(pipelines, meta, str(tmp_path))
    # un fichier par modèle + le JSON
    assert [os.path.basename(c) for c in chemins] == ["regression_lineaire.joblib", "mlp.joblib", "metadonnees.json"]
    assert all(os.path.exists(c) for c in chemins)
    recharge = Predicteur.depuis_dossier(str(tmp_path))  # charge le modèle retenu
    assert recharge.metadonnees == meta
    date = datetime(2025, 1, 15, 3)
    attendu = Predicteur(pipelines[MODELE_RETENU], meta).predire(saisie_valide(), date).ecart
    assert recharge.predire(saisie_valide(), date).ecart == pytest.approx(attendu)


def test_chargement_dossier_vide(tmp_path):
    with pytest.raises(ModeleNonTrouveError):
        Predicteur.depuis_dossier(str(tmp_path))


# --- Saisie et prédiction ---------------------------------------------------


@pytest.fixture(scope="module")
def predicteur(modele_entraine) -> Predicteur:
    pipelines, meta = modele_entraine
    return Predicteur(pipelines[MODELE_RETENU], meta)


def test_predicteur_contient_les_variables(predicteur):
    variables = predicteur.variables
    # un champ par variable saisie ; saison et moment sont calculés depuis la date
    assert set(variables) == set(CARACTERISTIQUES_NUMERIQUES + CARACTERISTIQUES_CATEGORIELLES) - {"saison", "moment_journee"}
    assert isinstance(variables["Rel Hum (%)"], VariableNumerique)
    assert isinstance(variables["Station Name"], VariableCategorielle)
    variables.clear()  # copie : le Predicteur n'est pas modifié
    assert len(predicteur.variables) == 9


def test_predicteur_rmse_et_repr(predicteur, modele_entraine):
    assert predicteur.rmse == pytest.approx(modele_entraine[1]["rmse_officielle"])
    assert repr(predicteur).startswith("Predicteur(")


def test_preparer_saisie_calcule_saison_et_moment(predicteur):
    ligne = preparer_saisie(saisie_valide(), datetime(2025, 7, 10, 14), predicteur.variables)
    assert ligne.loc[0, "saison"] == "ete"
    assert ligne.loc[0, "moment_journee"] == "apres-midi"
    assert ligne.loc[0, "Temp (°C)"] == pytest.approx(-5.0)  # « -5,0 » accepté


def test_predire_retourne_une_prediction(predicteur):
    prediction = predicteur.predire(saisie_valide(), datetime(2025, 1, 15, 3))
    assert isinstance(prediction.ecart, float)
    assert -10 < prediction.ecart < 10
    assert prediction.temperature_reference == pytest.approx(-5.0)
    assert prediction.temperature_centre_ville == pytest.approx(-5.0 + prediction.ecart)
    assert prediction.hors_valeurs_vues == [] and prediction.champs_vides == []


def test_predire_champs_facultatifs_vides(predicteur):
    saisie = saisie_valide() | {"Visibility (km)": "", "Wind Spd (km/h)": "  ", "Rel Hum (%)": None}
    prediction = predicteur.predire(saisie, datetime(2025, 1, 15, 3))
    assert np.isfinite(prediction.ecart)
    assert prediction.champs_vides == ["Rel Hum (%)", "Wind Spd (km/h)", "Visibility (km)"]
    assert prediction.hors_valeurs_vues == []  # une case vide n'est pas « hors des valeurs vues »


def test_predire_temperature_obligatoire(predicteur):
    with pytest.raises(DonneeInvalideError):
        predicteur.predire(saisie_valide() | {"Temp (°C)": ""}, datetime(2025, 1, 15, 3))


@pytest.mark.parametrize("colonne, valeur", [
    ("Rel Hum (%)", 150),             # hors limites physiques
    ("Temp (°C)", "chaud"),            # non numérique
    ("Wind Spd (km/h)", "abc"),        # non numérique, même si le champ est facultatif
    ("Station Name", "MCTAVISH"),      # catégorie non permise (et fuite)
])
def test_predire_saisie_invalide(predicteur, colonne, valeur):
    saisie = saisie_valide() | {colonne: valeur}
    with pytest.raises(DonneeInvalideError):
        predicteur.predire(saisie, datetime(2025, 1, 15, 3))


@pytest.mark.parametrize("colonne, valeur, attendu_valide", [
    ("Temp (°C)", "8,5", True),          # virgule acceptée
    ("Temp (°C)", "", False),            # obligatoire
    ("Rel Hum (%)", "", True),           # facultatif vide
    ("Rel Hum (%)", "150", False),       # hors limites
    ("Wind Spd (km/h)", "abc", False),   # non numérique
    ("Colonne inconnue", "1", False),
])
def test_erreur_champ(predicteur, colonne, valeur, attendu_valide):
    message = predicteur.erreur_champ(colonne, valeur)
    assert (message is None) == attendu_valide
    if not attendu_valide:
        assert isinstance(message, str) and message


def test_predire_champ_absent(predicteur):
    saisie = saisie_valide()
    del saisie["Visibility (km)"]
    with pytest.raises(DonneeInvalideError):
        predicteur.predire(saisie, datetime(2025, 1, 15, 3))


def test_predire_hors_valeurs_vues(predicteur):
    prediction = predicteur.predire(saisie_valide() | {"Temp (°C)": 40}, datetime(2025, 1, 15, 3))
    assert prediction.hors_valeurs_vues == ["Temp (°C)"]


# --- Décorateur -------------------------------------------------------------


def test_chronometrer():
    @chronometrer
    def doubler(x: int) -> int:
        return 2 * x

    assert doubler(21) == 42
    assert getattr(doubler, "derniere_duree") >= 0.0
    assert doubler.__name__ == "doubler"
