"""Tests de src/donnees.py.

Seuls les cas réussis de saison() sont écrits. Les autres tests sont des squelettes
marqués « skip » : retirer le décorateur et écrire le corps au fur et à mesure.
Données de test : tests/fake_donnees/ (10761 = McTavish, 51157 = YUL, 2025-01-01 00:00 à 11:00).
"""

import pytest

from abc import ABC, abstractmethod
from donnees import direction_8_points, moment_journee, saison

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


@pytest.mark.parametrize(
    ("heure", "attendu"),
    [(3, "nuit"), (8, "matin"), (14, "apres-midi"), (20, "soir")],
)
def test_moment_journee(heure: int, attendu: str) -> None:
    assert moment_journee(heure) == attendu


@pytest.mark.parametrize(
    ("heure", "attendu"),
    [
        (0, "nuit"),
        (5, "nuit"),
        (6, "matin"),
        (10, "matin"),
        (11, "apres-midi"),
        (16, "apres-midi"),
        (17, "soir"),
        (23, "soir"),
    ],
)
def test_moment_journee_bornes(heure: int, attendu: str) -> None:
    assert moment_journee(heure) == attendu


@pytest.mark.parametrize("heure", [-1, 24])
def test_moment_journee_heure_invalide(heure: int) -> None:
    with pytest.raises(ValueError):
        moment_journee(heure)


# ---------------------------------------------------------------------------
# direction_8_points
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("dizaines", "attendue"),
    [
        (36, "N"),
        (4.5, "NE"),
        (9, "E"),
        (13.5, "SE"),
        (18, "S"),
        (22.5, "SO"),
        (27, "O"),
        (31.5, "NO"),
    ],
)
def test_direction_8_points(dizaines: float, attendue: str) -> None:
    # Centre de chaque secteur (multiples de 45°).
    assert direction_8_points(dizaines) == attendue


@pytest.mark.parametrize(
    ("dizaines", "attendue"),
    [
        # Le secteur N chevauche 360° : de 337,5° à 22,5°.
        (1, "N"),
        (2, "N"),
        (3, "NE"),
        (33, "NO"),
        (34, "N"),
        (35, "N"),
        # Autre frontière : E (67,5° à 112,5°) / SE.
        (6, "NE"),
        (7, "E"),
        (11, "E"),
        (12, "SE"),
    ],
)
def test_direction_8_points_limites_de_secteur(dizaines: float, attendue: str) -> None:
    assert direction_8_points(dizaines) == attendue


def test_direction_8_points_manquante() -> None:
    assert direction_8_points(None) is None


@pytest.mark.parametrize("dizaines", [0, 37, -1, 0.5])
def test_direction_8_points_invalide(dizaines: float) -> None:
    with pytest.raises(ValueError):
        direction_8_points(dizaines)


# ---------------------------------------------------------------------------
# apparier
# (il faudra une fixture qui charge les faux CSV : rediriger station.PATH_DONNEES
#  vers tests/fake_donnees/ avec monkeypatch, ou construire de petits pd.DataFrame à la main)
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
