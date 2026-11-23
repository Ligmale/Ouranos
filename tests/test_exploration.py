"""Tests de src/exploration.py, sur un petit tableau construit à la main (sans donnees/)."""

import os

import numpy as np
import pandas as pd
import pytest

from exceptions import DonneeInvalideError
from exploration import creer_figure_exploration, ecart_par_heure, enregistrer_figure


@pytest.fixture
def petit_tableau() -> pd.DataFrame:
    """Deux stations, deux jours : à 00:00 l'écart vaut 1 puis 3 (moyenne 2) pour la station A."""
    return pd.DataFrame({
        "Date/Time (LST)": ["2025-01-01 00:00", "2025-01-02 00:00", "2025-01-01 12:00",
                            "2025-01-01 00:00", "2025-01-01 12:00"],
        "Station Name": ["A", "A", "A", "B", "B"],
        "ecart": [1.0, 3.0, -0.5, 0.25, np.nan],
    })


def test_ecart_par_heure_moyenne(petit_tableau: pd.DataFrame) -> None:
    moyennes = ecart_par_heure(petit_tableau)
    assert moyennes.loc[0, "A"] == pytest.approx(2.0)
    assert moyennes.loc[12, "A"] == pytest.approx(-0.5)
    assert moyennes.loc[0, "B"] == pytest.approx(0.25)


def test_ecart_par_heure_24_heures(petit_tableau: pd.DataFrame) -> None:
    # Une ligne par heure, même sans donnée (NaN), pour que l'axe aille de 0 à 23.
    moyennes = ecart_par_heure(petit_tableau)
    assert list(moyennes.index) == list(range(24))
    assert np.isnan(moyennes.loc[5, "A"])
    assert np.isnan(moyennes.loc[12, "B"])  # seule valeur à 12:00 pour B : manquante


@pytest.mark.parametrize("colonne", ["Date/Time (LST)", "Station Name", "ecart"])
def test_ecart_par_heure_colonne_absente(petit_tableau: pd.DataFrame, colonne: str) -> None:
    with pytest.raises(DonneeInvalideError, match="absentes"):
        ecart_par_heure(petit_tableau.drop(columns=colonne))


def test_ecart_par_heure_tableau_vide(petit_tableau: pd.DataFrame) -> None:
    with pytest.raises(DonneeInvalideError, match="vide"):
        ecart_par_heure(petit_tableau.iloc[0:0])


def test_figure_enregistree(petit_tableau: pd.DataFrame, tmp_path) -> None:
    figure = creer_figure_exploration(petit_tableau)
    gauche, droite = figure.axes
    assert gauche.get_xlabel() == "Heure (HNL)"
    assert len(gauche.get_lines()) >= 2  # une courbe par station
    chemin = enregistrer_figure(figure, dossier=str(tmp_path / "figures"), nom="test.png")
    assert os.path.exists(chemin)
    assert os.path.getsize(chemin) > 0
