"""Tests de src/telechargement.py, sans réseau (aucun fichier n'est téléchargé)."""

import os

import pytest

import telechargement
from telechargement import (
    ANNEE,
    chemin_fichier,
    construire_url,
    generer_mois,
    lire_annees,
    telecharger_tout,
    verifier_annees,
)


def test_generer_mois_plusieurs_annees():
    triplets = list(generer_mois({"A": 1, "B": 2}, [2024, 2025]))
    assert len(triplets) == 2 * 2 * 12
    assert triplets[0] == (1, 2024, 1)
    assert triplets[12] == (1, 2025, 1)   # la 2e année suit la 1re pour la même station
    assert triplets[-1] == (2, 2025, 12)


def test_generer_mois_vide():
    assert list(generer_mois({}, [2025])) == []
    assert list(generer_mois({"A": 1}, [])) == []


def test_verifier_annees_trie_et_retire_les_doublons():
    assert verifier_annees([2025, 2023, 2025, 2024], 2026) == [2023, 2024, 2025]


@pytest.mark.parametrize("annees", [[], [1839], [2027], [2025, 3000]])
def test_verifier_annees_invalides(annees):
    with pytest.raises(ValueError):
        verifier_annees(annees, 2026)


def test_verifier_annees_bornes_incluses():
    assert verifier_annees([1840, 2026], 2026) == [1840, 2026]


def test_lire_annees():
    assert lire_annees([]) == [ANNEE]  # sans argument : année par défaut
    assert lire_annees(["2023", "2025"]) == [2023, 2025]


def test_lire_annees_pas_un_entier():
    with pytest.raises(SystemExit):  # argparse affiche un message clair puis quitte
        lire_annees(["deux-mille"])


def test_construire_url():
    url = construire_url(10761, 2024, 3)
    assert "stationID=10761" in url and "Year=2024" in url and "Month=3" in url
    assert "timeframe=1" in url  # données horaires


def test_construire_url_mois_invalide():
    with pytest.raises(ValueError):
        construire_url(10761, 2024, 13)


def test_chemin_fichier_par_annee():
    assert os.path.basename(chemin_fichier("d", 10761, 2024, 3)) == "10761_2024_03.csv"


def test_telecharger_tout_ne_refait_pas_les_fichiers(tmp_path, monkeypatch):
    # Tous les fichiers existent déjà : aucun téléchargement ne doit être tenté.
    for annee in (2024, 2025):
        for mois in range(1, 13):
            open(chemin_fichier(str(tmp_path), 1, annee, mois), "w").close()

    def interdit(url: str, chemin: str) -> None:
        raise AssertionError(f"téléchargement inattendu : {url}")

    monkeypatch.setattr(telechargement, "telecharger_fichier", interdit)
    assert telecharger_tout({"A": 1}, [2024, 2025], str(tmp_path)) == []


def test_telecharger_tout_collecte_les_echecs(tmp_path, monkeypatch):
    def echoue(url: str, chemin: str) -> None:
        raise ValueError("pas un CSV horaire")

    monkeypatch.setattr(telechargement, "telecharger_fichier", echoue)
    monkeypatch.setattr(telechargement, "DELAI_SECONDES", 0)
    echecs = telecharger_tout({"A": 1}, [2024], str(tmp_path))
    assert len(echecs) == 12
    assert echecs[0].startswith("station 1, 2024-01")
