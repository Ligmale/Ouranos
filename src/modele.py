import os
import json
import joblib
import numpy as np
import pandas as pd
from Exceptions import ErreurPredictionError, DonneeInvalideError
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.metrics import mean_squared_error, mean_absolute_error
from scipy.optimize import minimize_scalar



def calculer_rmse_numpy(y_reel: np.ndarray, y_predit: np.ndarray) -> float:
    "Calcule la RMSE manuellement avec Numpy"
    if len(y_reel) != len(y_predit):
        raise DonneeInvalideError("Les tableaux ne sont pas de la même taille...")
    return float(np.sqrt(np.mean((y_reel - y_predit)**2)))



def fonction_cout(decalage:float, y_reel: np.ndarray, y_predit: np.ndarray) -> float:
    """
    Fonction de coût auxiliare pour l'optimisation du seuil
    
    Sortie: la moyenne des erreurs absolues pour un décalage donné
    """
    
    return float(np.mean(np.abs(y_reel - (y_predit + decalage))))



def optimiser_seuil_prediction(y_reel: np.ndarray, y_predit: np.ndarray) -> float:
    "Trouve un décalage global constant (bias) qui minimise la MAE sur l'ensemble"
    try:
        resultat = minimize_scalar(fonction_cout, args=(y_reel, y_predit))

        if not resultat.success:
            raise ValueError("L'optimisation du seuil a échoué...")

        return float(resultat.x)
    except Exception as e:
        raise DonneeInvalideError(f"Erreur lors de l'optimisation du seuil: {e}")



def entrainer_modele(df: pd.DataFrame, features_numeriques: list[str], features_categoriques: list[str], colonne_cible: str = "ecart") -> tuple:
    
    "Entraîne un réseau de neurones (MLPREGRESSOR) dans un pipeline scikit-learn"
    if df.empty:
        raise DonneeInvalideError("Le dataframe fourni est vide...")

    #On regroupe les caractéristiques numériques et catégorielles + on ajoute la colonne cible à la fin
    colonnes_requises = features_categoriques + features_numeriques
    colonnes_requises.append(colonnes_requises)

    if not set(colonnes_requises).issubset(df.columns):
        raise DonneeInvalideError("Des colonnes requises sont manquantes dans le dataframe...")

    #Séparation des données X et de la cible Y
    x = df[features_numeriques + features_categoriques]
    y = df[colonne_cible]

    #Division en ensembles d'entraînement et de test
    x_entraine, x_test, y_entraine, y_test = train_test_split(x, y, test_size=0.2, random_state=42)

    #Prétraitement pour les réseaux de neurones
    preprocesseur = ColumnTransformer(transformers=[("num", StandardScaler(), features_numeriques), ("cat",OneHotEncoder(handle_unknown="ignore"), features_categoriques)])

    #Application du prétraitement sur l'entraînement et le test 
    try: 
        x_entraine_transforme = preprocesseur.fit_transform(x_entraine)
        x_test_transforme = preprocesseur.transform(x_test)
    except Exception as e:
        raise ErreurPredictionError(f"Échec du prétraitement des données : {e}")
    
    #Création et entraînement du réseau des neurones (MLPRegressor)
    regresseur = MLPRegressor(hidden_layer_sizes=(50,25),max_iter=500,random_state=42,early_stopping=True)

    try: 
        regresseur.fit(x_entraine_transforme, y_entraine)
    except Exception as e:
        raise ErreurPredictionError(f"Échec de l'entraînement du modèle : {e}")

    #Génération des prédictions sur le jeu de test transformé
    try:
        y_predit = regresseur.predict(x_test_transforme)
    except Exception as e:
        raise ErreurPredictionError(f"Échec de la prédiction : {e}")

    #Calcul des métriques 
    rmse_scikit = float(np.sqrt(mean_squared_error(y_test, y_predit)))
    rmse_np = calculer_rmse_numpy(y_test.to_numpy(), y_predit)
    mae = float(mean_absolute_error(y_test, y_predit))

    #Optimisation d'un biais avec scipy.optimize
    meilleur_decalage = optimiser_seuil_prediction(y_test.to_numpy(), y_predit)

    #Moyenne de l'entraînement (référence simple)
    y_ref = np.full_like(y_test, fill_value=y_entraine.mean())
    rmse_ref = calculer_rmse_numpy(y_entraine.to_numpy(),y_ref)

    metriques = {
        "rmse_modele":rmse_scikit, 
        "rmse_numpy_verif": rmse_np, 
        "mae_modele": mae, 
        "rmse_reference_moyenne": rmse_ref, 
        "biais_optimise_scipy": meilleur_decalage
    }

    metadonnees = {
        "type_modele": "MLPRegressor (Reseau de neurones)", 
        "features_numeriques": features_numeriques, 
        "features_categoriques": features_categoriques, 
        "valeurs_permises_cat": {cat: df[cat].dropna().unique().tolist() for cat in features_categoriques}, 
        "intervalles_num": {num: {"min": float(df[num].min()), "max": float(df[num].max())} for num in features_numeriques}, 
        "metriques": metriques
    }

    #On regroupe les deux éléments pour la prédiction dans un dictionnaire
    elements_importants = {"preprocesseur": preprocesseur, "regresseur":regresseur}
    
    return elements_importants, metriques, metadonnees
    


def sauvegarder_artefacts(modele, metadonnees:dict, dossier_modeles = "modeles") -> None:
    "Sauvegarde le modèle (.plk) et le JSON des métadonnées"
    try:
        os.makedirs(dossier_modeles, exist_ok=True)
    except OSError as e:
        raise DonneeInvalideError(f"Il est impossible de créer le dossier de sauvegarde {dossier_modeles} : {e}")

    chemin_modele = os.path.join(dossier_modeles, "modele_ouranos.pkl")
    chemin_json = os.path.join(dossier_modeles, "metadonnees.json")

    with open(chemin_modele, "wb") as f_model:
        joblib.dump(modele, f_model)

    with open(chemin_json, "w", encoding="utf-8") as f_json:
        json.dump(metadonnees, f_json, ensure_ascii=False, indent=4)

    print(f"Modèle sauvegardé dans {chemin_modele}")
    print(f"Métadonnées sauvegardées dans {chemin_json}")


