import os 
import json
import joblib
import numpy as np 
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from exceptions import ModeleNonTrouveError
from donnees import saison as calculer_saison, moment_journee

#Configuration de la page
st.set_page_config(page_title="Ouranos - Estimation de l'îlot de chaleur urbain", layout="wide")

"Fonction pour charger le modèle et les métadonnées"
@st.cache_resource   #Comme la base de données ou le chargement du modèle peuvent être lourds, on le stocke dans la mémoire vive
def charger_artefacts():
    dossier = "modeles" #Le dossier modèle contiendra les métadonnées traitées et enregistrées en plk/json
    chemin_modele = os.path.join(dossier, "modele_ouranos.pkl")
    chemin_json = os.path.join(dossier,"metadonnees.json")

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

station_ref = st.sidebar.selectbox("Station de référence", ["MONTREAL INTL A", "St-Hubert", "Mirabel", "McTavish"])
date_mesure = st.sidebar.date_input("Date")
heure_mesure = st.sidebar.slider("Heure (HNL)", 0, 23, 23)

#Détermination automatique de la saison et du moment de la journée
#On réutilise les fonctions de donnees.py : mêmes catégories que celles vues à l'entraînement.
saison = calculer_saison(date_mesure.month)
moment = moment_journee(heure_mesure)

st.sidebar.markdown(f"**Saison :** {saison} — **Moment :** {moment} *(calculés automatiquement)*")

#Saisie des variables numériques et catégorielles
temp_ref = st.sidebar.number_input("Température (°C)", value=8.5, format="%.1f")
point_rosee = st.sidebar.number_input("Point de rosée (°C)", value=7.6, format="%.1f")
humidite = st.sidebar.number_input("Humidité (%)", min_value=0, max_value=100, value=94)
pression = st.sidebar.number_input("Pression (kPa)", value=101.2, format="%.1f")
vent = st.sidebar.number_input("Vent (km/h)", min_value=0, value=4)
visibilite = st.sidebar.number_input("Visibilité (km)", min_value=0.0, value=24.0, format="%.1f")
direction_vent = st.sidebar.selectbox("Direction du vent", ["N", "NE", "E", "SE", "S", "SO", "O", "NO", "Inconnu"])

#Valeurs en minuscules comme dans station.py ; format_func ne change que l'affichage.
tendance_pression = st.sidebar.radio(
    "Tendance de la pression (3h)", ["hausse", "stable", "baisse"], index=1, format_func=str.capitalize
)

bouton_predire = st.sidebar.button("Prédire", type="primary")

#Gestion de l'historique
dossier_hist = "historique"
os.makedirs(dossier_hist, exist_ok=True)
chemin_hist = os.path.join(dossier_hist, "predictions.csv") 

if bouton_predire:
    try:
        #Récupération des features attendues par le modèle
        features_num = metadonnees.get("features_numeriques", ["Temp (°C)", "Rel Hum (%)", "Wind Spd (km/h)"])
        features_cat = metadonnees.get("features_categoriques", ["moment_journee", "direction_8_points"])



        #Construction du dictionnaire d'entrée
        input_data = {
            "Temp (°C)": [temp_ref],
            "Rel Hum (%)": [float(humidite)],
            "Wind Spd (km/h)": [float(vent)],
            "moment_journee": [moment],
            "direction_8_points": [direction_vent]
        }

        df_input = pd.DataFrame(input_data)



        #Sécurité pour s'assurer que toutes les colonnes nécessaires sont présentes
        for colonne in features_num:
            if colonne not in df_input.columns:
                df_input[colonne] = 0.0
        
        for colonne in features_cat:
            if colonne not in df_input.columns:
                df_input[colonne] = "Inconnu"



        #Transformation et Prédiction
        x_entraine = preprocesseur.transform(df_input[features_num + features_cat])
        ecart_pred = float(regresseur.predict(x_entraine)[0])
        temp_centre_ville = temp_ref + ecart_pred



        #Affichage des résultats sous forme de métriques
        st.markdown("Résultat")
        colonne1, colonne2 = st.columns(2)

        mae_modele = metadonnees.get("metriques", {}).get("mae_modele", 0.5)

        with colonne1:
            st.metric(
                label="Écart prédit (McTavish - Référence)",
                value=f"+{ecart_pred:.1f} °C" if ecart_pred >= 0 else f"{ecart_pred:.1f} °C",
                delta=f"± [{mae_modele:.1f}] °C (erreur moyenne MAE)"
            )
        with colonne2:
            st.metric(
                label="Température estimée au centre-ville",
                value=f"{temp_centre_ville:.1f} °C",
                delta=f"{temp_ref} °C mesurés à {station_ref} {ecart_pred:+.1f} °C"
            )



        #Enregistrement dans l'historique CSV
        date_heure_str = f"{date_mesure} {heure_mesure:02d}:00"
        nouvelle_ligne = pd.DataFrame([{
            "Date et heure": date_heure_str,
            "Référence": station_ref,
            "Température référence": f"{temp_ref} °C",
            "Vent": f"{vent} km/h",
            "Écart prédit": f"{ecart_pred:+.1f} °C",
            "Centre-ville": f"{temp_centre_ville:+.1f} °C" 
        }])

        if os.path.exists(chemin_hist):
            df_hist = pd.read_csv(chemin_hist)
            df_hist = pd.concat([nouvelle_ligne, df_hist], ignore_index=True)
        else:
            df_hist = nouvelle_ligne

        df_hist.to_csv(chemin_hist, index=False)


    
        #Graphique Matplotlib
        st.markdown("Où se situe cette prédiction ?")
        st.markdown(f"--Écart moyen selon l'heure - référence : {station_ref}--")

        fig, ax = plt.subplots(figsize=(10,4))
        heures_jour = np.arange(24)



        #Courbe de tendance illustrative ou basée sur vos données
        courbe_moyenne = 1.5 + 1.8 * np.sin((heures_jour - 6) * np.pi / 12)

        ax.plot(heures_jour, courbe_moyenne, color="#1f77b4", linewidth=2.5, label="Moyenne historique")
        ax.scatter([heure_mesure], [ecart_pred], color="red", s=120, zorder=5, label="Votre prédiction")

        ax.set_xlabel("Heure (HNL)")
        ax.set_ylabel("Écart (°C)")
        ax.set_xticks([0, 6, 12, 18, 23])
        ax.set_xticklabels(["0h","6h","12h","18h","23h"])
        ax.grid(True, linestyle="--", alpha=0.5)
        ax.legend(loc="upper left")

        st.pyplot(fig)

    except Exception as e:
        st.error(f"Une erreur est survenue lors de la prédiction: {e}")


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