"""Interface Streamlit d'Ouranos, lancée par main.py (streamlit run src/main.py).

Streamlit réexécute main.py à chaque interaction ; tout l'affichage est donc dans des
fonctions appelées par afficher_application(), pas au niveau du module (un module importé
n'est exécuté qu'une fois). La logique (validation, prédiction) est dans modele.py.
"""

import os
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from donnees import moment_journee, saison as calculer_saison
from exceptions import DonneeInvalideError, ErreurPredictionError, ModeleNonTrouveError
from modele import NUMERIQUES_FACULTATIVES, Prediction, Predicteur

CHEMIN_HISTORIQUE = os.path.join("historique", "predictions.csv")


@st.cache_resource   #Le modèle est chargé une seule fois et gardé en mémoire vive (jamais réentraîné)
def charger() -> Predicteur:
    "Charge le Predicteur (Pipeline + métadonnées + variables) depuis modeles/."
    return Predicteur.depuis_dossier()


#Champs numériques : (colonne, étiquette, valeur par défaut). Zones de texte : pas de boutons
#+/−, « 7,6 » ou « 7.6 » acceptés ; la validation est faite par les classes Variable.
CHAMPS_NUMERIQUES = [
    ("Temp (°C)", "Température (°C)", "8,5"),
    ("Dew Point Temp (°C)", "Point de rosée (°C)", "7,6"),
    ("Rel Hum (%)", "Humidité (%)", "94"),
    ("Stn Press (kPa)", "Pression (kPa)", "101,2"),
    ("Wind Spd (km/h)", "Vent (km/h)", "4"),
    ("Visibility (km)", "Visibilité (km)", "24"),
]


def champ_numerique(numeriques: dict, colonne: str, etiquette: str, defaut: str) -> str:
    "Zone de texte pour une variable numérique ; l'aide rappelle les limites tirées du JSON."
    limites = numeriques[colonne]
    facultatif = colonne in NUMERIQUES_FACULTATIVES
    aide = f"Entre {limites['min_physique']:g} et {limites['max_physique']:g}."
    if facultatif:
        aide += " Laisser vide si inconnu."
    return st.sidebar.text_input(etiquette + (" — facultatif" if facultatif else ""), value=defaut, help=aide)


def lire_saisie(metadonnees: dict) -> tuple[dict, datetime, bool]:
    """Affiche la barre latérale de saisie.

    Entrée : les métadonnées (stations, bornes et catégories tirées du JSON).
    Sortie : (saisie {colonne: valeur}, date et heure de la mesure, bouton « Prédire » cliqué).
    """
    numeriques = metadonnees["numeriques"]
    categorielles = metadonnees["categorielles"]

    st.sidebar.header("Conditions mesurées")
    st.sidebar.markdown("À la station de référence choisie")

    station_ref = st.sidebar.selectbox("Station de référence", categorielles["Station Name"])
    date_mesure = st.sidebar.date_input("Date")
    heure_mesure = st.sidebar.slider("Heure (HNL)", 0, 23, 23)

    #Détermination automatique de la saison et du moment de la journée (même logique que l'entraînement)
    saison = calculer_saison(date_mesure.month)
    moment = moment_journee(heure_mesure)
    st.sidebar.markdown(f"**Saison :** {saison} — **Moment :** {moment} *(calculés automatiquement)*")

    #Saisie des variables numériques et catégorielles (limites et choix tirés du JSON)
    saisie: dict = {colonne: champ_numerique(numeriques, colonne, etiquette, defaut)
                    for colonne, etiquette, defaut in CHAMPS_NUMERIQUES}
    saisie["Station Name"] = station_ref
    saisie["direction_8_points"] = st.sidebar.selectbox("Direction du vent", categorielles["direction_8_points"])
    #Valeurs en minuscules comme dans station.py ; format_func ne change que l'affichage.
    saisie["tendance_pression"] = st.sidebar.radio(
        "Tendance de la pression (3h)", categorielles["tendance_pression"], format_func=str.capitalize
    )

    bouton_predire = st.sidebar.button("Prédire", type="primary")
    date_heure = datetime(date_mesure.year, date_mesure.month, date_mesure.day, heure_mesure)
    return saisie, date_heure, bouton_predire


def afficher_resultat(station_ref: str, prediction: Prediction, rmse_modele: float) -> None:
    "Affiche l'écart prédit et la température estimée au centre-ville, avec la RMSE comme marge."
    st.markdown("Résultat")
    colonne1, colonne2 = st.columns(2)

    with colonne1:
        st.metric(
            label="Écart prédit (McTavish - Référence)",
            value=f"{prediction.ecart:+.1f} °C",
            delta=f"± {rmse_modele:.1f} °C (erreur RMSE, découpage chronologique)",
            delta_color="off",
        )
    with colonne2:
        st.metric(
            label="Température estimée au centre-ville",
            value=f"{prediction.temperature_centre_ville:.1f} °C",
            delta=f"{prediction.temperature_reference:.1f} °C mesurés à {station_ref} {prediction.ecart:+.1f} °C",
            delta_color="off",
        )


def enregistrer_historique(saisie: dict, date_heure: datetime, prediction: Prediction) -> None:
    "Ajoute la prédiction en tête de l'historique CSV (dossier créé au besoin)."
    vent = str(saisie["Wind Spd (km/h)"]).strip()
    nouvelle_ligne = pd.DataFrame([{
        "Date et heure": date_heure.strftime("%Y-%m-%d %H:00"),
        "Référence": saisie["Station Name"],
        "Température référence": f"{prediction.temperature_reference:.1f} °C",
        "Vent": f"{vent} km/h" if vent else "inconnu",
        "Écart prédit": f"{prediction.ecart:+.1f} °C",
        "Centre-ville": f"{prediction.temperature_centre_ville:+.1f} °C"
    }])

    os.makedirs(os.path.dirname(CHEMIN_HISTORIQUE), exist_ok=True)
    if os.path.exists(CHEMIN_HISTORIQUE):
        df_hist = pd.read_csv(CHEMIN_HISTORIQUE)
        df_hist = pd.concat([nouvelle_ligne, df_hist], ignore_index=True)
    else:
        df_hist = nouvelle_ligne
    df_hist.to_csv(CHEMIN_HISTORIQUE, index=False)


def afficher_graphique(metadonnees: dict, station_ref: str, heure: int, ecart_pred: float) -> None:
    "Graphique Matplotlib : écart moyen par heure à l'entraînement (tiré du JSON) et la prédiction."
    st.markdown("Où se situe cette prédiction ?")
    st.markdown(f"--Écart moyen selon l'heure - référence : {station_ref}--")

    fig, ax = plt.subplots(figsize=(10, 4))
    heures_jour = np.arange(24)
    courbe_moyenne = [np.nan if v is None else v for v in metadonnees["ecart_moyen_par_heure"][station_ref]]

    ax.plot(heures_jour, courbe_moyenne, color="#1f77b4", linewidth=2.5, label="Moyenne historique (2025)")
    ax.scatter([heure], [ecart_pred], color="red", s=120, zorder=5, label="Votre prédiction")

    ax.set_xlabel("Heure (HNL)")
    ax.set_ylabel("Écart (°C)")
    ax.set_xticks([0, 6, 12, 18, 23])
    ax.set_xticklabels(["0h", "6h", "12h", "18h", "23h"])
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(loc="upper left")

    st.pyplot(fig)


def afficher_historique() -> None:
    "Section Historique en bas de page."
    st.markdown("---")
    st.markdown("Historique des prédictions")
    if os.path.exists(CHEMIN_HISTORIQUE):
        st.dataframe(pd.read_csv(CHEMIN_HISTORIQUE), width="stretch")
    else:
        st.info("Aucun historique pour le moment. Effectuez une prédiction pour l'alimenter.")


def afficher_application() -> None:
    "Construit toute la page ; appelée par main.py à chaque réexécution de Streamlit."
    #Configuration de la page
    st.set_page_config(page_title="Ouranos - Estimation de l'îlot de chaleur urbain", layout="wide")

    #En-tête principal de l'application
    st.title("Ouranos")
    st.markdown("Combien fait-il de plus au centre-ville (McTavish) qu'à l'aéroport? Estimation de l'îlot de chaleur urbain à partir des conditions mesurées")

    try:
        predicteur = charger()
    except ModeleNonTrouveError as erreur:
        st.error(f"Aucun modèle entraîné trouvé. {erreur}")
        st.stop()
        raise  # jamais atteint : st.stop() arrête le script (indique à Pyright que la suite est sûre)

    metadonnees = predicteur.metadonnees
    saisie, date_heure, bouton_predire = lire_saisie(metadonnees)

    if bouton_predire:
        try:
            #Validation de la saisie (classes Variable) et prédiction : la logique est dans modele.Predicteur
            prediction = predicteur.predire(saisie, date_heure)
            if prediction.hors_valeurs_vues:
                st.warning(f"Valeurs hors de celles vues à l'entraînement : {', '.join(prediction.hors_valeurs_vues)}. Prédiction moins fiable.")
            if prediction.champs_vides:
                st.info(f"Champs vides remplacés par la valeur médiane de l'entraînement : {', '.join(prediction.champs_vides)}.")

            afficher_resultat(saisie["Station Name"], prediction, predicteur.rmse)
            enregistrer_historique(saisie, date_heure, prediction)
            afficher_graphique(metadonnees, saisie["Station Name"], date_heure.hour, prediction.ecart)
        except (DonneeInvalideError, ErreurPredictionError) as e:
            st.error(f"Prédiction impossible : {e}")

    afficher_historique()

    # Avertissement pédagogique requis par les consignes du projet
    st.markdown("---")
    st.caption("Exercice pédagogique (INF1007, Polytechnique Montréal). Données : Environnement et Changement climatique Canada, licence du gouvernement ouvert – Canada")
