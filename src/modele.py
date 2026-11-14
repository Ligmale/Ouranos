import os
import json
import joblib
import numpy as np
import pandas as pd
import Exceptions
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.metrics import mean_squared_error, mean_absolute_error
from scipy.optimize import minimize_scalar

def calculer_rmse_numpy(y_reel: np.ndarray, y_predit: np.ndarray) -> float:
    "Calcule la RMSE manuellement avec Numpy"
    if len(y_reel) != len(y_predit):
        raise Exceptions.DonneeInvalideError("Les tableaux ne sont pas de la même taille...")
    return float(np.sqrt(np.mean((y_reel - y_predit)**2)))

def fonction_cout(decalage:float, y_reel: np.ndarray, y_predit: np.ndarray) -> float:
    """
    Fonction de coût auxiliare pour l'optimisation du seuil
    
    Sortie: la moyenne des erreurs absolues pour un décalage donné
    """
    
    return float(np.mean(np.abs(y_reel - (y_predit + decalage))))

def optimiser_seuil_prediction(y_reel: np.ndarray, y_predit: np.ndarray) -> float:
    "Trouve un décalage global constant (bias) qui minimise la MAE sur l'ensemble"
    resultat = minimize_scalar(fonction_cout)
    return float(resultat.x)

def entrainer_modele(df: pd.DataFrame, features_numeriques: list[str], features_categoriques: list[str], colonne_cible: str = "ecart") -> tuple:
    #TODO:Entraîne un réseau de neurones (MLPREGRESSOR) dans un pipeline scikit-learn.
        #Prétraitement pour les réseaux de neurones
        
        #Utilisation de MLPRegressor
        
        #Entraînement
        
        #Optimisation d'un biasi avec scipy.optimize
        
        #Référence simple (moyen)

    #return modele, metriques, metadonnees
    pass

def sauvegarder_artefacts(modele, metadonnees:dict, dossier_modeles = "modeles") -> None:
    "Sauvegarde le modèle (.plk) et le JSON des métadonnées"
    os.makedirs(dossier_modeles, exist_ok=True)

    chemin_modele = os.path.join(dossier_modeles, "modele_ouranos.pkl")
    chemin_json = os.path.join(dossier_modeles, "metadonnees.json")

    with open(chemin_modele, "wb") as f_model:
        joblib.dump(modele, f_model)

    with open(chemin_json, "w", encoding="utf-8") as f_json:
        json.dump(metadonnees, f_json, ensure_ascii=False, indent=4)




