"""Graphique d'exploration de l'écart McTavish − référence, enregistré dans figures/.

Lancer : python src/exploration.py (lit donnees/brutes/, écrit figures/exploration_ecart.png).

Le graphique a deux parties :
- à gauche, l'écart moyen selon l'heure pour chaque référence (l'îlot de chaleur est-il nocturne ?) ;
- à droite, la distribution de l'écart par référence (valeurs aberrantes, différences entre stations).

On utilise matplotlib.figure.Figure plutôt que pyplot : aucune fenêtre ne s'ouvre et le module
n'interfère pas avec la configuration de pyplot faite par l'interface.
"""

import os

import pandas as pd
from matplotlib.figure import Figure

from donnees import COLONNE_DATE
from exceptions import DonneeInvalideError

CIBLE = "ecart"
DOSSIER_FIGURES = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "figures"))
NOM_FIGURE = "exploration_ecart.png"

# Noms courts pour la légende ; un nom inconnu est affiché tel quel.
NOMS_COURTS = {
    "MONTREAL INTL A": "Trudeau (YUL)",
    "MONTREAL/ST-HUBERT": "St-Hubert",
    "MONTREAL MIRABEL INTL A": "Mirabel",
}


def ecart_par_heure(tableau: pd.DataFrame) -> pd.DataFrame:
    """Écart moyen pour chaque heure de la journée, par station de référence.

    Entrée : le tableau final (date, « Station Name » et « ecart »).
    Sortie : un DataFrame avec une ligne par heure (0 à 23) et une colonne par station ;
        NaN pour une heure sans donnée.
    Échec : DonneeInvalideError si une colonne nécessaire est absente ou si le tableau est vide.
    """
    manquantes = [c for c in (COLONNE_DATE, "Station Name", CIBLE) if c not in tableau.columns]
    if manquantes:
        raise DonneeInvalideError(f"Colonnes absentes du tableau : {manquantes}")
    if tableau.empty:
        raise DonneeInvalideError("Le tableau est vide : rien à tracer.")
    heure = pd.to_datetime(tableau[COLONNE_DATE]).dt.hour
    moyennes = tableau.assign(heure=heure).pivot_table(
        index="heure", columns="Station Name", values=CIBLE, aggfunc="mean"
    )
    return moyennes.reindex(range(24))


def creer_figure_exploration(tableau: pd.DataFrame) -> Figure:
    """Construit la figure d'exploration, sans l'afficher ni l'enregistrer.

    Entrée : le tableau final (date, « Station Name » et « ecart »).
    Sortie : la Figure Matplotlib (deux graphiques côte à côte, titres, axes et légende).
    Échec : DonneeInvalideError (voir ecart_par_heure).
    """
    moyennes = ecart_par_heure(tableau)
    stations = list(moyennes.columns)
    figure = Figure(figsize=(11, 4.5), layout="constrained")
    gauche, droite = figure.subplots(1, 2)

    for station in stations:
        gauche.plot(moyennes.index, moyennes[station], marker="o", markersize=3,
                    label=NOMS_COURTS.get(station, station))
    gauche.axhline(0, color="grey", linewidth=0.8)
    gauche.set_title("Écart moyen selon l'heure")
    gauche.set_xlabel("Heure (HNL)")
    gauche.set_ylabel("Écart McTavish − référence (°C)")
    gauche.set_xticks([0, 3, 6, 9, 12, 15, 18, 21, 23])
    gauche.grid(True, linestyle="--", alpha=0.5)
    # En haut, vers 11 h à 17 h : la seule zone que les courbes laissent vide.
    gauche.legend(title="Référence", loc="upper center", bbox_to_anchor=(0.62, 0.98))

    valeurs = [tableau.loc[tableau["Station Name"] == s, CIBLE].dropna() for s in stations]
    droite.boxplot(valeurs, tick_labels=[NOMS_COURTS.get(s, s) for s in stations])
    droite.axhline(0, color="grey", linewidth=0.8)
    droite.set_title("Distribution de l'écart (points : valeurs extrêmes)")
    droite.set_xlabel("Station de référence")
    droite.set_ylabel("Écart McTavish − référence (°C)")
    droite.grid(True, axis="y", linestyle="--", alpha=0.5)

    figure.suptitle(f"Îlot de chaleur : McTavish contre trois références ({len(tableau)} heures × stations)")
    return figure


def enregistrer_figure(figure: Figure, dossier: str = DOSSIER_FIGURES, nom: str = NOM_FIGURE) -> str:
    """Enregistre une figure en PNG avec savefig, en créant le dossier au besoin.

    Entrées : la figure, le dossier et le nom du fichier.
    Sortie : le chemin du fichier écrit.
    Échec : OSError si le dossier ne peut pas être créé ou le fichier écrit.
    """
    os.makedirs(dossier, exist_ok=True)
    chemin = os.path.join(dossier, nom)
    figure.savefig(chemin, dpi=150)
    return chemin


if __name__ == "__main__":
    from donnees import construire_tableau
    from station import Station

    ID_MCTAVISH = 10761
    ID_REFERENCES = [51157, 48374, 49608]  # YUL, St-Hubert, Mirabel

    tableau_final = construire_tableau(Station(ID_MCTAVISH), [Station(i) for i in ID_REFERENCES])
    chemin_figure = enregistrer_figure(creer_figure_exploration(tableau_final))
    print(f"Figure enregistrée : {chemin_figure}")
    print(ecart_par_heure(tableau_final).round(2).to_string())
