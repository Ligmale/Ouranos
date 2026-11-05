"""Tests de src/donnees.py.

Seuls les cas réussis de saison() sont écrits. Les autres tests sont des squelettes
marqués « skip » : retirer le décorateur et écrire le corps au fur et à mesure.
Données de test : tests/fake_donnees/ (10761 = McTavish, 51157 = YUL, 2025-01-01 00:00 à 11:00).
"""

import pytest

from abc import ABC, abstractmethod
from donnees import saison

A_ECRIRE = pytest.mark.skip(reason="test à écrire")


# ---------------------------------------------------------------------------
# saison
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("mois", "attendue"),
    [
        (1, "hiver"),
        (2, "hiver"),
        (12, "hiver"),
        (3, "printemps"),
        (4, "printemps"),
        (5, "printemps"),
        (6, "ete"),
        (7, "ete"),
        (8, "ete"),
        (9, "automne"),
        (10, "automne"),
        (11, "automne"),
    ],
)
def test_saison(mois: int, attendue: str) -> None:
    assert saison(mois) == attendue


@A_ECRIRE
@pytest.mark.parametrize("mois", [0, 13, -5])
def test_saison_mois_invalide(mois: int) -> None:
    # TODO : pytest.raises(ValueError)
    with pytest.raises(ValueError):
        saison(mois)


# ---------------------------------------------------------------------------
# moment_journee
# ---------------------------------------------------------------------------


@A_ECRIRE
def test_moment_journee() -> None:
    # TODO : une heure typique par moment (selon les bornes choisies)
    ...


@A_ECRIRE
def test_moment_journee_bornes() -> None:
    # TODO : 0, 23 et les heures de transition entre deux moments
    ...


@A_ECRIRE
@pytest.mark.parametrize("heure", [-1, 24])
def test_moment_journee_heure_invalide(heure: int) -> None:
    # TODO : pytest.raises(...)
    ...


# ---------------------------------------------------------------------------
# direction_8_points
# ---------------------------------------------------------------------------


@A_ECRIRE
def test_direction_8_points() -> None:
    # TODO : 9 → E, 18 → S, 27 → O, 36 → N…
    ...


@A_ECRIRE
def test_direction_8_points_limites_de_secteur() -> None:
    # TODO : valeurs à la frontière entre deux secteurs (ex. autour du N : 1, 2, 35)
    ...


@A_ECRIRE
def test_direction_8_points_manquante() -> None:
    # TODO : None → None
    ...


@A_ECRIRE
@pytest.mark.parametrize("dizaines", [0, 37])
def test_direction_8_points_invalide(dizaines: float) -> None:
    # TODO : pytest.raises(...)
    ...


# ---------------------------------------------------------------------------
# apparier
# (il faudra une fixture qui charge les faux CSV : rediriger station.PATH_DONNEES
#  vers tests/fake_donnees/ avec monkeypatch, ou construire de petits pl.DataFrame à la main)
# ---------------------------------------------------------------------------


@A_ECRIRE
def test_apparier_colonne_ecart() -> None:
    # TODO : à 00:00, écart McTavish − YUL = −3,5 − (−5,0) = 1,5 (pytest.approx)
    ...


@A_ECRIRE
def test_apparier_sans_temperature_mctavish() -> None:
    # TODO : la température de McTavish ne doit plus être dans le résultat (fuite)
    ...


@A_ECRIRE
def test_apparier_nombre_de_lignes() -> None:
    # TODO : 12 heures communes ; 10 si on retire les lignes sans cible (05:00 et 08:00)
    ...


@A_ECRIRE
def test_apparier_colonne_absente() -> None:
    # TODO : tableau sans « Date/Time (LST) » → pytest.raises(...)
    ...


# ---------------------------------------------------------------------------
# ajouter_categories
# ---------------------------------------------------------------------------


@A_ECRIRE
def test_ajouter_categories_colonnes() -> None:
    # TODO : saison, moment de la journée et direction présents
    ...


@A_ECRIRE
def test_ajouter_categories_valeurs() -> None:
    # TODO : janvier → hiver ; 27 → O ; moment de 00:00
    ...


@A_ECRIRE
def test_ajouter_categories_colonne_absente() -> None:
    # TODO : pytest.raises(...)
    ...


# ---------------------------------------------------------------------------
# construire_tableau
# ---------------------------------------------------------------------------


@A_ECRIRE
def test_construire_tableau_une_ligne_par_heure_et_reference() -> None:
    # TODO : avec une seule référence (YUL), le nombre de lignes de apparier()
    ...


@A_ECRIRE
def test_construire_tableau_references_vide() -> None:
    # TODO : liste vide → pytest.raises(...)
    ...


# ---------------------------------------------------------------------------
# VariableNumerique
# ---------------------------------------------------------------------------


@A_ECRIRE
def test_variable_numerique_valeur_valide() -> None:
    # TODO : "12.5" ou 12.5 → 12.5
    ...


@A_ECRIRE
def test_variable_numerique_bornes_incluses() -> None:
    # TODO : minimum et maximum exacts acceptés
    ...


@A_ECRIRE
@pytest.mark.parametrize("saisie", ["", "abc", None])
def test_variable_numerique_saisie_invalide(saisie: object) -> None:
    # TODO : pytest.raises(DonneeInvalideError)
    ...


@A_ECRIRE
def test_variable_numerique_hors_intervalle() -> None:
    # TODO : pytest.raises(DonneeInvalideError)
    ...


# ---------------------------------------------------------------------------
# VariableCategorielle
# ---------------------------------------------------------------------------


@A_ECRIRE
def test_variable_categorielle_valeur_permise() -> None: ...


@A_ECRIRE
@pytest.mark.parametrize("saisie", ["", "inconnue"])
def test_variable_categorielle_saisie_invalide(saisie: object) -> None:
    # TODO : pytest.raises(DonneeInvalideError)
    ...


# ---------------------------------------------------------------------------
# Variable (classe abstraite)
# ---------------------------------------------------------------------------


@A_ECRIRE
def test_variable_non_instanciable() -> None:
    # TODO : Variable("x") → pytest.raises(TypeError)
    ...


@A_ECRIRE
def test_variable_methode_speciale() -> None:
    # TODO : __repr__ / __str__ / __eq__ selon celle choisie
    ...
