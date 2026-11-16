import os 
import json
import joblib
import numpy as np 
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from exceptions import ModeleNonTrouveError

#Configuration de la page
st.set_page_config(page_title="Ouranos - Estimation de l'îlot de chaleur urbain", layout="wide")

"Fonction pour charger le modèle et les métadonnées"
@st.cache_resource   #Comme la base de données ou le chargement du modèle peuvent être lourds, on le stocke dans la mémoire vive
def charger_artefacts():
    dossier = "modeles" #Le dossier modèle contiendra les métadonnées traitées et enregistrées en plk/json
    chemin_modele = os.path.join(dossier, "modele_ouranos.pkl")
    chemin_json = os.path.join(dossier,"metadonnes.json")

    if not os.path.exists(chemin_modele) or not os.path.exists(chemin_json):
        raise ModeleNonTrouveError("Le modèle entraîné ou le fichier de métadonnées est introuvable...")

    with open(chemin_modele, "rb") as f:
        artefacts = joblib.load(f)
    with open(chemin_json, "r", encoding="utf-8") as f:
        metadonnees = json.load(f)

    return artefacts, metadonnees





artefacts, metadonnees = charger_artefacts()

#En-tête principal de l'application
st.title("Ouranos")
st.markdown("Combien fait-il de plus au centre-ville (McTavish) qu'à l'aéroport? Estimation de l'îlot de chaleur urbain à partir des conditions mesurées")

if artefacts is None or metadonnees is None:
    st.error("Aucun modèle entraîné trouvé dans le dossier 'modeles/'. Veuillez lancer l'entraînement au préalable")
    st.stop()

preprocesseur = artefacts.get("preprocesseur")
regresseur = artefacts.get("regresseur")

#Barre latérale pour la saisie
st.sidebar.header("Conditions mesurées")
st.sidebar.markdown("À la station de référence choisie")

station_ref = st.sidebar.selectbox("Station de rfrence", ["MONTREAL INTL A", "St-Hubert", "Mirabel", "McTavish"])
date_mesure = st.sidebar.date_input("Date")
heure_mesure = st.sidebar.slider("Heure (HNL)", 0, 23, 23)

#Détermination automatique de la saison et du moment de la journée
mois = date_mesure.month

if mois in [12, 1, 2]:
    saison = "hiver"
elif mois in [3, 4, 5]:
    saison = "printemps"
elif mois in [6, 7, 8]:
    saison = "été"
else:
    saison = "automne"

if heure_mesure < 6:
    moment = "nuit"
elif heure_mesure < 12:
    moment = "matin"
elif heure_mesure < 18:
    moment = "midi"
else:
    moment = "soir"

st.sidebar.markdown(f"**Saison :** {saison} — **Moment :** {moment} *(calculés automatiquement)*")

#Saisie des variables numériques et catégorielles
temp_ref = st.sidebar.number_input("Température (°C)", value=8.5, format="%.1f")
point_rosee = st.sidebar.number_input("Point de rosée (°C)", value=7.6, format="%.1f")
humidite = st.sidebar.number_input("Humidité (%)", min_value=0, max_value=100, value=94)
pression = st.sidebar.number_input("Pression (kPa)", value=101.2, format="%.1f")
vent = st.sidebar.number_input("Vent (km/h)", min_value=0, value=4)
visibilite = st.sidebar.number_input("Visibilité (km)", min_value=0.0, value=24.0, format="%.1f")
direction_vent = st.sidebar.selectbox("Direction du vent", ["N", "NE", "E", "SE", "S", "SO", "O", "NO", "Inconnu"])

tendance_pression = st.sidebar.radio("Tendance de la pression (3h)", ["Hausse", "Stable", "Baisse"], index=1)

bouton_predire = st.sidebar.button("Prédire", type="primary")

#Gestion de l'historique
dossier_hist = "historique"
os.makedirs(dossier_hist, exist_ok=True)
chemin_hist = os.path.join(dossier_hist, "predictions.csv") 

#TODO: Coder la logique du bouton_predire
    #Récupération dess features attendues par le modèle
    #Construction du dictionnaire d'entrée
    #Sécurité pour s'assurer que toutes les colonnes nécessaires sont présentes
    #Transformation et Prédiction
    #Affichage des résultats sous forme de métriques
    #Enregistrement dans l'historique CSV
    #Graphique Matplotlib
    #Courbe de tendance



#Section Historique en bas de page
st.markdown("---")
st.markdown("Historique des prédictions")
if os.path.exists(chemin_hist):
    df_hist_affiche = pd.read_csv(chemin_hist)
    st.dataframe(df_hist_affiche, use_container_width=True)
else:
    st.info("Aucun historique pour le moment. Effectuez une prédiction pour l'alimenter.")

    # Avertissement pédagogique requis par les consignes du projet
st.markdown("---")
st.caption("Exercice pédagogique (INF1007, Polytechnique Montréal). Données : Environnement et Changement climatique Canada, licence du gouvernement ouvert – Canada")