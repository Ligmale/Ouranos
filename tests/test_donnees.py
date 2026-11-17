"""Tests de src/donnees.py.

Données de test : tests/fake_donnees/ (10761 = McTavish, 51157 = YUL, 2025-01-01 00:00 à 11:00).
"""

import os

import pandas as pd
import pytest

import station
from donnees import (
    Variable,
    VariableCategorielle,
    VariableNumerique,
    ajouter_categories,
    apparier,
    construire_tableau,
    direction_8_points,
    moment_journee,
    saison,
)
from exceptions import DonneeInvalideError
from station import Station

DOSSIER_FAUX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake_donnees")


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


@pytest.mark.parametrize("mois", [0, 13, -5])
def test_saison_mois_invalide(mois: int) -> None:
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
# (les faux CSV sont chargés en redirigeant station.PATH_DONNEES vers tests/fake_donnees/)
# ---------------------------------------------------------------------------


@pytest.fixture
def stations(monkeypatch: pytest.MonkeyPatch) -> tuple[Station, Station]:
    """McTavish et YUL chargées depuis tests/fake_donnees/ (2025-01-01, 00:00 à 11:00)."""
    monkeypatch.setattr(station, "PATH_DONNEES", DOSSIER_FAUX)
    return Station(10761, mois=[1], years=[2025]), Station(51157, mois=[1], years=[2025])


@pytest.fixture
def tableau_apparie(stations: tuple[Station, Station]) -> pd.DataFrame:
    mctavish, yul = stations
    return apparier(mctavish.make_target(), yul.data)


def test_apparier_colonne_ecart(tableau_apparie: pd.DataFrame) -> None:
    # À 00:00, écart McTavish − YUL = −3,5 − (−5,0) = 1,5.
    ligne = tableau_apparie[tableau_apparie["Date/Time (LST)"] == "2025-01-01 00:00"]
    assert ligne["ecart"].iloc[0] == pytest.approx(1.5)


def test_apparier_sans_temperature_mctavish(tableau_apparie: pd.DataFrame) -> None:
    # Seules les colonnes de la référence + « ecart » restent (sinon fuite de la cible).
    assert not any("mctavish" in c.lower() for c in tableau_apparie.columns)
    assert list(tableau_apparie.columns) == list(station.COLONNES_GARDEES) + [
        "delta_pression3h",
        "tendance_pression",
        "ecart",
    ]
    assert (tableau_apparie["Station Name"] == "MONTREAL INTL A").all()


def test_apparier_nombre_de_lignes(tableau_apparie: pd.DataFrame) -> None:
    # 12 heures communes ; 05:00 (YUL manquante) et 08:00 (McTavish manquante) n'ont pas de cible.
    assert len(tableau_apparie) == 10
    assert tableau_apparie["ecart"].notna().all()
    heures = set(tableau_apparie["Date/Time (LST)"])
    assert "2025-01-01 05:00" not in heures
    assert "2025-01-01 08:00" not in heures


def test_apparier_jointure_interne() -> None:
    # Une heure présente d'un seul côté est retirée.
    mctavish = pd.DataFrame({"Date/Time (LST)": ["h1", "h2"], "Temp (°C)": [1.0, 2.0]})
    reference = pd.DataFrame({"Date/Time (LST)": ["h2", "h3"], "Temp (°C)": [0.5, 0.0]})
    resultat = apparier(mctavish, reference)
    assert resultat["Date/Time (LST)"].tolist() == ["h2"]
    assert resultat["ecart"].iloc[0] == pytest.approx(1.5)


def test_apparier_colonne_absente(stations: tuple[Station, Station]) -> None:
    mctavish, yul = stations
    with pytest.raises(ValueError, match="Date/Time"):
        apparier(mctavish.make_target(), yul.data.drop(columns="Date/Time (LST)"))


# ---------------------------------------------------------------------------
# ajouter_categories
# ---------------------------------------------------------------------------


def test_ajouter_categories_colonnes(tableau_apparie: pd.DataFrame) -> None:
    resultat = ajouter_categories(tableau_apparie)
    for colonne in ("saison", "moment_journee", "direction_8_points"):
        assert colonne in resultat.columns
    # Le tableau d'origine n'est pas modifié.
    assert "saison" not in tableau_apparie.columns


def test_ajouter_categories_valeurs(tableau_apparie: pd.DataFrame) -> None:
    resultat = ajouter_categories(tableau_apparie)
    premiere = resultat.iloc[0]  # 2025-01-01 00:00, vent 27
    assert premiere["saison"] == "hiver"
    assert premiere["direction_8_points"] == "O"
    assert premiere["moment_journee"] == "nuit"
    # 03:00 : direction manquante à YUL → valeur manquante, sans erreur.
    ligne_3h = resultat[resultat["Date/Time (LST)"] == "2025-01-01 03:00"]
    assert pd.isna(ligne_3h["direction_8_points"].iloc[0])


def test_ajouter_categories_colonne_absente(tableau_apparie: pd.DataFrame) -> None:
    with pytest.raises(ValueError, match="Wind Dir"):
        ajouter_categories(tableau_apparie.drop(columns="Wind Dir (10s deg)"))


# ---------------------------------------------------------------------------
# construire_tableau
# ---------------------------------------------------------------------------


def test_construire_tableau_une_ligne_par_heure_et_reference(stations: tuple[Station, Station]) -> None:
    mctavish, yul = stations
    tableau = construire_tableau(mctavish, [yul])
    assert len(tableau) == len(apparier(mctavish.make_target(), yul.data))
    # Deux fois la même référence : deux fois plus de lignes, empilées.
    assert len(construire_tableau(mctavish, [yul, yul])) == 2 * len(tableau)
    assert "saison" in tableau.columns


def test_construire_tableau_references_vide(stations: tuple[Station, Station]) -> None:
    mctavish, _ = stations
    with pytest.raises(ValueError, match="vide"):
        construire_tableau(mctavish, [])


# ---------------------------------------------------------------------------
# VariableNumerique
# ---------------------------------------------------------------------------


@pytest.fixture
def temperature() -> VariableNumerique:
    return VariableNumerique("Temp (°C)", -50.0, 45.0)


@pytest.mark.parametrize("saisie", ["12.5", 12.5, " 12.5 ", "12,5"])
def test_variable_numerique_valeur_valide(temperature: VariableNumerique, saisie: object) -> None:
    resultat = temperature.valider(saisie)
    assert isinstance(resultat, float)
    assert resultat == pytest.approx(12.5)


def test_variable_numerique_bornes_incluses(temperature: VariableNumerique) -> None:
    assert temperature.valider(-50) == pytest.approx(-50.0)
    assert temperature.valider(45) == pytest.approx(45.0)


@pytest.mark.parametrize("saisie", ["", "abc", None, "nan"])
def test_variable_numerique_saisie_invalide(temperature: VariableNumerique, saisie: object) -> None:
    with pytest.raises(DonneeInvalideError):
        temperature.valider(saisie)


@pytest.mark.parametrize("saisie", [-50.1, 45.0001, 1000])
def test_variable_numerique_hors_intervalle(temperature: VariableNumerique, saisie: float) -> None:
    with pytest.raises(DonneeInvalideError, match="intervalle"):
        temperature.valider(saisie)


def test_variable_numerique_bornes_inversees() -> None:
    with pytest.raises(DonneeInvalideError):
        VariableNumerique("x", 10, 0)


# ---------------------------------------------------------------------------
# VariableCategorielle
# ---------------------------------------------------------------------------


@pytest.fixture
def saison_var() -> VariableCategorielle:
    return VariableCategorielle("saison", ["hiver", "printemps", "ete", "automne"])


def test_variable_categorielle_valeur_permise(saison_var: VariableCategorielle) -> None:
    assert saison_var.valider("ete") == "ete"
    assert saison_var.valider("  hiver ") == "hiver"


@pytest.mark.parametrize("saisie", ["", "inconnue", None, "été"])
def test_variable_categorielle_saisie_invalide(saison_var: VariableCategorielle, saisie: object) -> None:
    with pytest.raises(DonneeInvalideError):
        saison_var.valider(saisie)


def test_variable_categorielle_encapsulation(saison_var: VariableCategorielle) -> None:
    # La propriété renvoie une copie : modifier la liste ne change pas la variable.
    saison_var.valeurs_permises.append("mousson")
    with pytest.raises(DonneeInvalideError):
        saison_var.valider("mousson")


def test_variable_categorielle_liste_vide() -> None:
    with pytest.raises(DonneeInvalideError):
        VariableCategorielle("saison", [])


# ---------------------------------------------------------------------------
# Variable (classe abstraite)
# ---------------------------------------------------------------------------


def test_variable_non_instanciable() -> None:
    with pytest.raises(TypeError):
        Variable("x")  # type: ignore[abstract]


def test_variable_nom_vide() -> None:
    with pytest.raises(DonneeInvalideError):
        VariableCategorielle("  ", ["a"])


def test_variable_methode_speciale(temperature: VariableNumerique, saison_var: VariableCategorielle) -> None:
    assert repr(temperature) == "VariableNumerique('Temp (°C)', -50.0, 45.0)"
    assert repr(saison_var) == "VariableCategorielle('saison', ['hiver', 'printemps', 'ete', 'automne'])"
