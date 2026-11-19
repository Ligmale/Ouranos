"""Interface Streamlit d'Ouranos, lancée par main.py (streamlit run src/main.py).

Streamlit réexécute main.py à chaque interaction ; tout l'affichage est donc dans des
fonctions appelées par afficher_application(), pas au niveau du module (un module importé
n'est exécuté qu'une fois). La logique (validation, prédiction) est dans modele.py.
"""

import os
from datetime import datetime, time

import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd
import streamlit as st

from donnees import moment_journee, saison as calculer_saison
from exceptions import DonneeInvalideError, ErreurPredictionError, ModeleNonTrouveError
from modele import NUMERIQUES_FACULTATIVES, Prediction, Predicteur

CHEMIN_HISTORIQUE = os.path.join("historique", "predictions.csv")
DOSSIER_STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
CHEMIN_POLICE = os.path.join(DOSSIER_STATIC, "Inter.ttf")
CHEMIN_POLICE_TITRES = os.path.join(DOSSIER_STATIC, "Cinzel.ttf")


#Couleurs du thème sombre de Streamlit, reprises dans le graphique pour qu'il s'y fonde.
FOND_SOMBRE = "#0E1117"
TEXTE_CLAIR = "#FAFAFA"


def configurer_matplotlib() -> None:
    "Graphiques Matplotlib en mode sombre, dans la même police que l'interface (Inter) si présente."
    plt.style.use("dark_background")
    plt.rcParams.update({"figure.facecolor": FOND_SOMBRE, "axes.facecolor": FOND_SOMBRE,
                         "savefig.facecolor": FOND_SOMBRE, "text.color": TEXTE_CLAIR})
    if os.path.exists(CHEMIN_POLICE):
        font_manager.fontManager.addfont(CHEMIN_POLICE)
        plt.rcParams["font.family"] = "Inter"
    if os.path.exists(CHEMIN_POLICE_TITRES):
        font_manager.fontManager.addfont(CHEMIN_POLICE_TITRES)


configurer_matplotlib()


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


#Noms ECCC des stations (gardés tels quels pour le modèle) → région affichée à l'utilisateur.
NOMS_STATIONS = {
    "MONTREAL INTL A": "Ouest de l'île (Dorval, aéroport YUL)",
    "MONTREAL/ST-HUBERT": "Rive-Sud (Saint-Hubert)",
    "MONTREAL MIRABEL INTL A": "Rive-Nord (Mirabel)",
}


def nom_station(code: str) -> str:
    "Nom de région d'une station ECCC ; le code lui-même si la station est inconnue."
    return NOMS_STATIONS.get(code, code)


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

    station_ref = st.sidebar.selectbox("Station de référence", categorielles["Station Name"],
                                       format_func=nom_station)  # n'affiche que le nom de région
    date_mesure = st.sidebar.date_input("Date")
    #Saisie HH:MM en 24 h, comme une alarme ; seules les heures comptent (données horaires)
    heure_saisie = st.sidebar.time_input("Heure (HNL)", value=time(23, 0), format="24h",
                                         help="Les minutes sont ignorées : les mesures sont horaires.")
    heure_mesure = heure_saisie.hour

    #Détermination automatique de la saison et du moment de la journée (même logique que l'entraînement)
    saison = calculer_saison(date_mesure.month)
    moment = moment_journee(heure_mesure)
    st.sidebar.markdown(f"**Saison :** {NOMS_SAISONS.get(saison, saison)} — **Moment :** {moment} *(calculés automatiquement)*")

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


def sans_moins_zero(valeur: float) -> float:
    "Arrondit à 0,1 et transforme -0.0 en 0.0 (sinon l'affichage montre « -0.0 »)."
    return round(valeur, 1) + 0.0


def afficher_resultat(station_ref: str, prediction: Prediction, rmse_modele: float) -> None:
    "Affiche l'écart prédit et la température estimée au centre-ville, avec la RMSE comme marge."
    st.markdown("Résultat")
    colonne1, colonne2 = st.columns(2)
    ecart = sans_moins_zero(prediction.ecart)
    marge = f"± {rmse_modele:.1f} °C (erreur RMSE, découpage chronologique)"

    with colonne1:
        st.metric(
            label="Écart prédit (McTavish - Référence)",
            value=f"{ecart:+.1f} °C",
            delta=marge,
            delta_color="off",
        )
    with colonne2:
        st.metric(
            label="Température estimée au centre-ville",
            value=f"{sans_moins_zero(prediction.temperature_centre_ville):.1f} °C",
            delta=marge,
            delta_color="off",
        )
        st.caption(f"{prediction.temperature_reference:.1f} °C mesurés à {nom_station(station_ref)} {ecart:+.1f} °C d'écart")


def enregistrer_historique(saisie: dict, date_heure: datetime, prediction: Prediction) -> None:
    "Ajoute la prédiction en tête de l'historique CSV (dossier créé au besoin)."
    vent = str(saisie["Wind Spd (km/h)"]).strip()
    nouvelle_ligne = pd.DataFrame([{
        "Date et heure": date_heure.strftime("%Y-%m-%d %H:00"),
        "Référence": nom_station(saisie["Station Name"]),
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


#Codes de saison (donnees.saison, sans accent) → texte affiché.
NOMS_SAISONS = {"hiver": "hiver", "printemps": "printemps", "ete": "été", "automne": "automne"}


def courbe_json(valeurs: list) -> list[float]:
    "Liste du JSON → valeurs à tracer (None, heure sans donnée, devient NaN : trou dans la courbe)."
    return [np.nan if v is None else v for v in valeurs]


def preparer_axe_heures(ax, titre: str, etiquette_y: str) -> None:
    "Mise en forme commune des deux sous-graphiques (axe des heures, grille, légende)."
    police_titre = "Cinzel" if os.path.exists(CHEMIN_POLICE_TITRES) else None
    ax.set_title(titre, fontsize=11, fontfamily=police_titre)
    ax.set_xlabel("Heure (HNL)")
    ax.set_ylabel(etiquette_y)
    ax.set_xticks([0, 6, 12, 18, 23])
    ax.set_xticklabels(["0h", "6h", "12h", "18h", "23h"])
    ax.grid(True, linestyle="--", alpha=0.25)
    ax.legend(loc="best", frameon=False, fontsize=9)  # « best » : là où la légende cache le moins


def afficher_graphique(metadonnees: dict, station_ref: str, date_heure: datetime,
                       prediction: Prediction | None = None) -> None:
    """Deux graphiques Matplotlib côte à côte (moyennes tirées du JSON, jamais des données) :
    à gauche l'écart moyen selon l'heure, à droite les températures moyennes de la saison
    à la référence et au centre-ville. Une ligne verticale marque l'heure choisie.

    Sans prédiction (avant le premier clic sur « Prédire »), seules les moyennes historiques
    sont tracées ; avec une prédiction, la saisie et le résultat s'ajoutent en points."""
    saison = calculer_saison(date_heure.month)
    nom_saison = NOMS_SAISONS.get(saison, saison)
    heure = date_heure.hour
    heures_jour = np.arange(24)
    if prediction is None:
        st.markdown(f"**Historique 2025** — Référence : {nom_station(station_ref)}. Cliquez sur « Prédire » pour situer une prédiction.")
    else:
        st.markdown(f"**Où se situe cette prédiction ?** Référence : {nom_station(station_ref)}")

    fig, (ax_ecart, ax_temp) = plt.subplots(1, 2, figsize=(13, 4.2))

    #Gauche : écart moyen selon l'heure (toute l'année)
    ecart_moyen = courbe_json(metadonnees["ecart_moyen_par_heure"][station_ref])
    ax_ecart.plot(heures_jour, ecart_moyen, color="#4DA3FF", linewidth=2.5, label="Écart moyen (2025)")
    if prediction is not None:
        ax_ecart.scatter([heure], [prediction.ecart], color="#FF4B4B", s=110, zorder=5, label="Écart prédit")
    ax_ecart.axvline(heure, color="#FFD43B", linewidth=1.4, linestyle="--", alpha=0.8, label=f"{heure} h choisie")
    ax_ecart.axhline(0, color="#FAFAFA", linewidth=0.8, alpha=0.4)
    preparer_axe_heures(ax_ecart, "Écart McTavish − référence", "Écart (°C)")

    #Droite : températures moyennes de la saison de la date choisie
    temperatures = metadonnees.get("temperatures_moyennes_par_heure", {}).get(station_ref, {}).get(saison)
    if temperatures is None:
        ax_temp.text(0.5, 0.5, "Températures historiques absentes du modèle :\nrelancer « python src/modele.py »",
                     ha="center", va="center", transform=ax_temp.transAxes)
        ax_temp.set_axis_off()
    else:
        ax_temp.plot(heures_jour, courbe_json(temperatures["reference"]), color="#4DA3FF", linewidth=2,
                     label=f"Référence ({nom_saison}, moyenne)")
        ax_temp.plot(heures_jour, courbe_json(temperatures["centre_ville"]), color="#FFA94D", linewidth=2,
                     label=f"Centre-ville ({nom_saison}, moyenne)")
        if prediction is not None:
            ax_temp.scatter([heure], [prediction.temperature_reference], color="#4DA3FF", edgecolor="#FAFAFA",
                            s=90, zorder=5, label="Température saisie")
            ax_temp.scatter([heure], [prediction.temperature_centre_ville], color="#FF4B4B", s=110, zorder=5,
                            label="Centre-ville estimé")
        ax_temp.axvline(heure, color="#FFD43B", linewidth=1.4, linestyle="--", alpha=0.8)
        preparer_axe_heures(ax_temp, f"Températures moyennes en {nom_saison}", "Température (°C)")

    fig.tight_layout()  # évite de couper les titres des axes
    st.pyplot(fig)
    plt.close(fig)  # libère la mémoire : Streamlit réexécute le script à chaque clic


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
    st.caption(f"Modèle : {metadonnees['type_modele']} — erreur typique (RMSE) ± {predicteur.rmse:.1f} °C")
    saisie, date_heure, bouton_predire = lire_saisie(metadonnees)

    prediction = None
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
        except (DonneeInvalideError, ErreurPredictionError) as e:
            prediction = None
            st.error(f"Prédiction impossible : {e}")

    #Graphique toujours visible : moyennes historiques seules tant qu'il n'y a pas de prédiction
    afficher_graphique(metadonnees, saisie["Station Name"], date_heure, prediction)

    afficher_historique()

    # Avertissement pédagogique requis par les consignes du projet
    st.markdown("---")
    st.caption("Exercice pédagogique (INF1007, Polytechnique Montréal). Données : Environnement et Changement climatique Canada, licence du gouvernement ouvert – Canada")
