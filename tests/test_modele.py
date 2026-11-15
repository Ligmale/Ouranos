import pytest 
import pandas as pd
import numpy as np
import os 
from src.modele import calculer_rmse_numpy, optimiser_seuil_prediction, entrainer_modele, sauvegarder_artefacts
from src.Exceptions import DonneeInvalideError


def test_calculer_rmse_numpy():
    "Vérifions le calcul manuel de la RMSE avec numpy"
    y_reel = np.array([2.0,4.0,6.0])
    y_predit = np.array([1.0,4.0,7.0])

    rmse = calculer_rmse_numpy(y_reel, y_predit)
    assert isinstance(rmse, float)
    assert pytest.approx(rmse, 0.001) == 0.81649

def test_calculer_rmse_numpy_erreur_taille():
    """Vérifie qu'une exception DonneeInvalideError est levée si les tableaux ont des tailles différentes."""
    y_reel = np.array([1.0, 2.0])
    y_predit = np.array([1.0])

    with pytest.raises(DonneeInvalideError):
        calculer_rmse_numpy(y_reel, y_predit)

def test_optimiser_seuil_prediction():
    """Vérifie l'optimisation du seuil avec scipy.optimize.minimize_scalar."""
    y_reel = np.array([10.0, 20.0, 30.0])
    y_predit = np.array([9.0, 18.0, 29.0])
    
    decalage = optimiser_seuil_prediction(y_reel, y_predit)
    assert isinstance(decalage, float)

def test_entrainer_modele_avec_csv_reels():
    """Teste l'entraînement complet, la vérification numpy/scipy et la sauvegarde à partir des vrais CSV."""
    #Chargement et préparation directe des données des deux stations
    df_mct = pd.read_csv("fake_donnees/10761_2025_01.csv")[["Date/Time (LST)", "Temp (°C)"]].rename(columns={"Temps (°C)": "Temp_mct"})
    df_yul = pd.read_csv("fake_donnees/51157_2025_01.csv")
    df = pd.merge(df_yul, df_mct, on="Date/Time (LST)", how="inner")
    df["ecart"] = df["Temp (°C)"] - df_mct["Temp_mct"]

    heures = pd.to_datetime(df["Date/Time (LST)"]).dt.hour
    df["moment_journee"] = np.where(heures < 6, "nuit", np.where(heures < 12, "matin", np.where(heures < 18, "midi", "soir")))

    df = df.dropna(subset=["Temp (°C)", "Rel Hum (%)", "Wind Spd (km/h)", "ecart"])

    # Duplication pour obtenir suffisamment de lignes pour early_stopping=True de MLPRegressor
    df_entrainement = pd.concat([df] * 5, ignore_index=True)

    features_num = ["Temp (°C)", "Rel Hum (%)", "Wind Spd (km/h)"]
    features_cat = ["moment_journee", "direction_8_points"]

    #Entraînement du modèle
    artefacts, metriques, metadonnees = entrainer_modele(
        df=df_entrainement,
        features_numeriques=features_num,
        features_categoriques=features_cat,
        colonne_cible="ecart",
    )

    assert "preprocesseur" in artefacts
    assert "regresseur" in artefacts
    assert pytest.approx(metriques["rmse_modele"], rel=1e-6) == metriques["rmse_numpy_verif"]
    assert isinstance(metriques["biais_optimise_scipy"], float)
    assert metadonnees["type_modele"] == "MLPRegressor (Reseau de neurones)"

    #Test de la sauvegarde des artefacts
    dossier_test = str("modeles_test")
    sauvegarder_artefacts(artefacts, metadonnees, dossier_modeles=dossier_test)

    assert os.path.exists(os.path.join(dossier_test, "modele_ouranos.pkl"))
    assert os.path.exists(os.path.join(dossier_test, "metadonnees.json"))

def test_entrainer_modele_dataframe_vide():
    """Vérifie que DonneeInvalideError est levée si le DataFrame est vide."""
    with pytest.raises(DonneeInvalideError):
        entrainer_modele(
            df=pd.DataFrame(),
            features_numeriques=["Temp (°C)"],
            features_categoriques=["moment_journee"],
            colonne_cible="ecart",
        )