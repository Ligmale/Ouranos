import os
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from donnees import moment_journee, saison as calculer_saison
from exceptions import DonneeInvalideError, ErreurPredictionError, ModeleNonTrouveError
from modele import charger_artefacts, hors_valeurs_vues, predire, preparer_saisie

#Configuration de la page
st.set_page_config(page_title="Ouranos - Estimation de l'îlot de chaleur urbain", layout="wide")


@st.cache_resource   #Le modèle est chargé une seule fois et gardé en mémoire vive (jamais réentraîné)
def charger():
    "Charge le Pipeline et les métadonnées depuis modeles/ (voir modele.charger_artefacts)."
    return charger_artefacts()


#En-tête principal de l'application
st.title("Ouranos")
st.markdown("Combien fait-il de plus au centre-ville (McTavish) qu'à l'aéroport? Estimation de l'îlot de chaleur urbain à partir des conditions mesurées")

try:
    pipeline, metadonnees = charger()
except ModeleNonTrouveError as erreur:
    st.error(f"Aucun modèle entraîné trouvé. {erreur}")
    st.stop()
    raise  # jamais atteint : st.stop() arrête le script (indique à Pyright que la suite est sûre)

numeriques = metadonnees["numeriques"]
categorielles = metadonnees["categorielles"]


def bornes(colonne: str) -> dict:
    "Limites physiques d'une variable numérique, tirées du JSON, pour st.number_input."
    return {"min_value": float(numeriques[colonne]["min_physique"]), "max_value": float(numeriques[colonne]["max_physique"])}


#Barre latérale pour la saisie
st.sidebar.header("Conditions mesurées")
st.sidebar.markdown("À la station de référence choisie")

station_ref = st.sidebar.selectbox("Station de référence", categorielles["Station Name"])
date_mesure = st.sidebar.date_input("Date")
heure_mesure = st.sidebar.slider("Heure (HNL)", 0, 23, 23)

#Détermination automatique de la saison et du moment de la journée (même logique que l'entraînement)
saison = calculer_saison(date_mesure.month)
moment = moment_journee(heure_mesure)

st.sidebar.markdown(f"**Saison :** {saison} — **Moment :** {moment} *(calculés automatiquement)*")

#Saisie des variables numériques et catégorielles (bornes et choix tirés du JSON)
temp_ref = st.sidebar.number_input("Température (°C)", value=8.5, format="%.1f", **bornes("Temp (°C)"))
point_rosee = st.sidebar.number_input("Point de rosée (°C)", value=7.6, format="%.1f", **bornes("Dew Point Temp (°C)"))
humidite = st.sidebar.number_input("Humidité (%)", value=94.0, format="%.0f", **bornes("Rel Hum (%)"))
pression = st.sidebar.number_input("Pression (kPa)", value=101.2, format="%.1f", **bornes("Stn Press (kPa)"))
vent = st.sidebar.number_input("Vent (km/h)", value=4.0, format="%.0f", **bornes("Wind Spd (km/h)"))
visibilite = st.sidebar.number_input("Visibilité (km)", value=24.0, format="%.1f", **bornes("Visibility (km)"))
direction_vent = st.sidebar.selectbox("Direction du vent", categorielles["direction_8_points"])

#Valeurs en minuscules comme dans station.py ; format_func ne change que l'affichage.
tendance_pression = st.sidebar.radio(
    "Tendance de la pression (3h)", categorielles["tendance_pression"], format_func=str.capitalize
)

bouton_predire = st.sidebar.button("Prédire", type="primary")

#Gestion de l'historique
dossier_hist = "historique"
os.makedirs(dossier_hist, exist_ok=True)
chemin_hist = os.path.join(dossier_hist, "predictions.csv")

if bouton_predire:
    try:
        #Validation de la saisie (classes Variable) et prédiction : la logique est dans modele.py
        saisie = {
            "Temp (°C)": temp_ref,
            "Dew Point Temp (°C)": point_rosee,
            "Rel Hum (%)": humidite,
            "Stn Press (kPa)": pression,
            "Wind Spd (km/h)": vent,
            "Visibility (km)": visibilite,
            "Station Name": station_ref,
            "direction_8_points": direction_vent,
            "tendance_pression": tendance_pression,
        }
        date_heure = datetime(date_mesure.year, date_mesure.month, date_mesure.day, heure_mesure)
        ligne = preparer_saisie(saisie, date_heure, metadonnees)
        ecart_pred = predire(pipeline, ligne)
        temp_centre_ville = temp_ref + ecart_pred

        hors = hors_valeurs_vues(ligne, metadonnees)
        if hors:
            st.warning(f"Valeurs hors de celles vues à l'entraînement : {', '.join(hors)}. Prédiction moins fiable.")

        #Affichage des résultats sous forme de métriques
        st.markdown("Résultat")
        colonne1, colonne2 = st.columns(2)

        rmse_modele = metadonnees["rmse_officielle"]

        with colonne1:
            st.metric(
                label="Écart prédit (McTavish - Référence)",
                value=f"{ecart_pred:+.1f} °C",
                delta=f"± {rmse_modele:.1f} °C (erreur RMSE, découpage chronologique)",
                delta_color="off",
            )
        with colonne2:
            st.metric(
                label="Température estimée au centre-ville",
                value=f"{temp_centre_ville:.1f} °C",
                delta=f"{temp_ref} °C mesurés à {station_ref} {ecart_pred:+.1f} °C",
                delta_color="off",
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

        #Graphique Matplotlib : écart moyen par heure à l'entraînement (tiré du JSON)
        st.markdown("Où se situe cette prédiction ?")
        st.markdown(f"--Écart moyen selon l'heure - référence : {station_ref}--")

        fig, ax = plt.subplots(figsize=(10, 4))
        heures_jour = np.arange(24)
        courbe_moyenne = [np.nan if v is None else v for v in metadonnees["ecart_moyen_par_heure"][station_ref]]

        ax.plot(heures_jour, courbe_moyenne, color="#1f77b4", linewidth=2.5, label="Moyenne historique (2025)")
        ax.scatter([heure_mesure], [ecart_pred], color="red", s=120, zorder=5, label="Votre prédiction")

        ax.set_xlabel("Heure (HNL)")
        ax.set_ylabel("Écart (°C)")
        ax.set_xticks([0, 6, 12, 18, 23])
        ax.set_xticklabels(["0h", "6h", "12h", "18h", "23h"])
        ax.grid(True, linestyle="--", alpha=0.5)
        ax.legend(loc="upper left")

        st.pyplot(fig)

    except (DonneeInvalideError, ErreurPredictionError) as e:
        st.error(f"Prédiction impossible : {e}")


#Section Historique en bas de page
st.markdown("---")
st.markdown("Historique des prédictions")
if os.path.exists(chemin_hist):
    df_hist_affiche = pd.read_csv(chemin_hist)
    st.dataframe(df_hist_affiche, width="stretch")
else:
    st.info("Aucun historique pour le moment. Effectuez une prédiction pour l'alimenter.")

    # Avertissement pédagogique requis par les consignes du projet
st.markdown("---")
st.caption("Exercice pédagogique (INF1007, Polytechnique Montréal). Données : Environnement et Changement climatique Canada, licence du gouvernement ouvert – Canada")
