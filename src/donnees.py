"""Construction du tableau final et validation des saisies.

- Conversions : petites fonctions pures, réutilisées par l'interface.
- Appariement : McTavish avec chaque station de référence (jointure interne).
- Classes de variables : validation d'une saisie selon le type de la variable.

Squelette : chaque corps est à écrire par l'équipe.
"""

import polars as pl
from abc import ABC, abstractmethod

from station import Station

# TODO : créer src/exceptions.py avec DonneeInvalideError(Exception), puis l'importer ici.


# ---------------------------------------------------------------------------
# Conversions
# ---------------------------------------------------------------------------


def saison(mois: int) -> str:
    """Donne la saison d'un mois.

    Entrée : mois, de 1 à 12.
    Sortie : nom de la saison.
    Échec : mois hors de 1 à 12.
    """
    # TODO : quelles bornes pour chaque saison ? Saisons astronomiques ou météorologiques ?
    if mois < 1 or mois > 12:
        raise ValueError(f"Mois Invalide :{mois}")
    saison = mois // 3
    match saison:
        case 0 | 4:
            return "hiver"
        case 1:
            return "printemps"
        case 2:
            return "ete"
        case 3:
            return "automne"
        case 4:
            return "hiver"
        case _:
            raise ValueError(f"Mois Invalide {mois}")

def moment_journee(heure: int) -> str:
    """Donne le moment de la journée d'une heure.

    Entrée : heure, de 0 à 23.
    Sortie : nom du moment (ex. nuit, matin…).
    Échec : heure hors de 0 à 23.
    """
    # TODO : combien de moments, et où couper ? Penser à l'îlot de chaleur la nuit.
    raise NotImplementedError


def direction_8_points(dizaines_degres: float | None) -> str | None:
    """Convertit une direction du vent ECCC (dizaines de degrés) en 8 points cardinaux.

    Entrée : direction de 1 à 36 (10 à 360°), ou None si manquante.
    Sortie : N, NE, E, SE, S, SO, O ou NO ; None si l'entrée est manquante.
    Échec : valeur hors de 1 à 36.
    """
    # TODO : chaque point couvre 45° ; où commence le secteur N ?
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Appariement et tableau final
# ---------------------------------------------------------------------------


def apparier(mctavish: pl.DataFrame, reference: pl.DataFrame) -> pl.DataFrame:
    """Aligne McTavish et une station de référence à la même heure et calcule l'écart.

    Entrées :
        mctavish : date et température de McTavish (sortie de Station.make_target).
        reference : données nettoyées de la référence (sortie de Station.clean_data).
    Sortie : une ligne par heure commune, caractéristiques de la référence + colonne « ecart ».
    Échec : colonne « Date/Time (LST) » ou « Temp (°C) » absente.
    """
    # TODO :
    # 1. renommer la température de McTavish (les deux tableaux ont « Temp (°C) ») ;
    # 2. jointure interne sur « Date/Time (LST) » ;
    # 3. calculer l'écart ;
    # 4. retirer la température de McTavish (sinon fuite de la cible).
    raise NotImplementedError


def ajouter_categories(tableau: pl.DataFrame) -> pl.DataFrame:
    """Ajoute saison, moment de la journée et direction du vent en 8 points.

    Entrée : tableau avec « Date/Time (LST) » et « Wind Dir (10s deg) ».
    Sortie : même tableau avec les colonnes catégorielles ajoutées.
    Échec : colonnes nécessaires absentes.
    """
    # TODO : réutiliser les trois fonctions de conversion ci-dessus.
    # La date est-elle déjà lue comme une date, ou encore comme du texte ?
    raise NotImplementedError


def construire_tableau(mctavish: Station, references: list[Station]) -> pl.DataFrame:
    """Construit le tableau final : une ligne par (heure, station de référence).

    Entrées : la station McTavish et la liste des stations de référence.
    Sortie : les tableaux appariés empilés, avec les catégories.
    Échec : liste de références vide.
    """
    # TODO : apparier McTavish avec chaque référence, puis empiler.
    # Combien de lignes perd-on ? (à noter dans le README)
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Classes de variables
# ---------------------------------------------------------------------------


class Variable(ABC):
    """Variable d'entrée du modèle, capable de valider une saisie."""

    def __init__(self, nom: str) -> None:
        # TODO : quels attributs, et lesquels protéger (_attribut + propriété) ?
        raise NotImplementedError

    @abstractmethod
    def valider(self, valeur: object) -> object:
        """Vérifie une saisie et la retourne convertie.

        Entrée : la valeur saisie.
        Sortie : la valeur dans le bon type.
        Échec : DonneeInvalideError avec un message clair.
        """

    # TODO : au moins une méthode spéciale (__repr__, __str__, __eq__…).


class VariableNumerique(Variable):
    """Variable numérique bornée par des limites physiques."""

    def __init__(self, nom: str, minimum: float, maximum: float) -> None:
        # TODO : aussi le min/max d'entraînement pour l'avertissement ?
        raise NotImplementedError

    def valider(self, valeur: object) -> float:
        # TODO : saisie vide ? non numérique ? hors des limites physiques ?
        raise NotImplementedError


class VariableCategorielle(Variable):
    """Variable catégorielle limitée à une liste de valeurs permises."""

    def __init__(self, nom: str, valeurs_permises: list[str]) -> None:
        raise NotImplementedError

    def valider(self, valeur: object) -> str:
        # TODO : saisie vide ? valeur absente de la liste ?
        raise NotImplementedError
