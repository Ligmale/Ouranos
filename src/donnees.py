"""Construction du tableau final et validation des saisies.

- Conversions : petites fonctions pures, réutilisées par l'interface.
- Appariement : McTavish avec chaque station de référence (jointure interne).
- Classes de variables : validation d'une saisie selon le type de la variable.
"""

import math
from abc import ABC, abstractmethod

import pandas as pd

from exceptions import DonneeInvalideError
from station import Station


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
    # Nuit 0-5, matin 6-10, après-midi 11-16, soir 17-23 (heure normale locale).
    if heure < 0 or heure > 23:
        raise ValueError(f"Heure invalide : {heure}")
    if heure < 6:
        return "nuit"
    if heure < 11:
        return "matin"
    if heure < 17:
        return "apres-midi"
    return "soir"


def direction_8_points(dizaines_degres: float | None) -> str | None:
    """Convertit une direction du vent ECCC (dizaines de degrés) en 8 points cardinaux.

    Entrée : direction de 1 à 36 (10 à 360°), ou None si manquante.
    Sortie : N, NE, E, SE, S, SO, O ou NO ; None si l'entrée est manquante (None ou NaN).
    Échec : valeur hors de 1 à 36.
    """
    # Chaque point couvre 45 = 4,5 dizaines, centré sur sa direction :
    # le secteur N va de 337,5 à 22,5
    # Manquante : None, ou NaN quand la valeur vient d'une colonne float de pandas.
    if dizaines_degres is None or math.isnan(dizaines_degres):
        return None
    if dizaines_degres < 1 or dizaines_degres > 36:
        raise ValueError(f"Direction du vent invalide : {dizaines_degres}")
    # +0,5 puis int() : arrondi au secteur le plus proche ; % 8 ramène 360° (indice 8) sur N.
    secteur = int(dizaines_degres / 4.5 + 0.5) % 8
    match secteur:
        case 0:
            return "N"
        case 1:
            return "NE"
        case 2:
            return "E"
        case 3:
            return "SE"
        case 4:
            return "S"
        case 5:
            return "SO"
        case 6:
            return "O"
        case 7:
            return "NO"
        case _:
            raise ValueError(f"Direction du vent invalide : {dizaines_degres}")


# ---------------------------------------------------------------------------
# Appariement et tableau final
# ---------------------------------------------------------------------------

COLONNE_DATE = "Date/Time (LST)"
COLONNE_TEMP = "Temp (°C)"
COLONNE_VENT = "Wind Dir (10s deg)"


def _verifier_colonnes(tableau: pd.DataFrame, colonnes: list[str], nom: str) -> None:
    """Vérifie que le tableau contient les colonnes demandées.

    Entrées : le tableau, les colonnes requises et le nom du tableau (pour le message).
    Sortie : aucune.
    Échec : ValueError qui nomme les colonnes absentes.
    """
    manquantes = [c for c in colonnes if c not in tableau.columns]
    if manquantes:
        raise ValueError(f"Colonnes absentes du tableau {nom} : {manquantes}")


def apparier(mctavish: pd.DataFrame, reference: pd.DataFrame) -> pd.DataFrame:
    """Aligne McTavish et une station de référence à la même heure et calcule l'écart.

    Entrées :
        mctavish : date et température de McTavish (sortie de Station.make_target).
        reference : données nettoyées de la référence (sortie de Station.clean_data).
    Sortie : une ligne par heure commune où l'écart est connu, caractéristiques de la
        référence + colonne « ecart » = température McTavish − température référence.
    Échec : ValueError si « Date/Time (LST) » ou « Temp (°C) » est absente, ou si une
        heure apparaît deux fois dans un des tableaux.
    """
    _verifier_colonnes(mctavish, [COLONNE_DATE, COLONNE_TEMP], "McTavish")
    _verifier_colonnes(reference, [COLONNE_DATE, COLONNE_TEMP], "de référence")

    # 1. renommer la température de McTavish, 2. jointure interne : une heure présente
    # d'un seul côté n'a pas de cible (ou pas de caractéristiques), elle est retirée.
    cible = mctavish[[COLONNE_DATE, COLONNE_TEMP]].rename(columns={COLONNE_TEMP: "temp_mctavish"})
    tableau = reference.merge(cible, on=COLONNE_DATE, how="inner", validate="one_to_one")

    # 3. écart ; une température manquante d'un côté ou de l'autre → pas de cible.
    tableau["ecart"] = tableau["temp_mctavish"] - tableau[COLONNE_TEMP]
    tableau = tableau.dropna(subset=["ecart"])

    # 4. retirer la température de McTavish (sinon fuite de la cible).
    return tableau.drop(columns="temp_mctavish").reset_index(drop=True)


def ajouter_categories(tableau: pd.DataFrame) -> pd.DataFrame:
    """Ajoute saison, moment de la journée et direction du vent en 8 points.

    Entrée : tableau avec « Date/Time (LST) » et « Wind Dir (10s deg) » (non modifié).
    Sortie : copie du tableau avec les colonnes « saison », « moment_journee » et
        « direction_8_points » (valeur manquante si la direction l'est ; l'imputation
        du modèle s'en occupe).
    Échec : ValueError si une colonne nécessaire est absente ou une date illisible.
    """
    _verifier_colonnes(tableau, [COLONNE_DATE, COLONNE_VENT], "à catégoriser")

    resultat = tableau.copy()
    # read_csv laisse la date en texte : on la convertit avant d'en tirer mois et heure.
    date = pd.to_datetime(resultat[COLONNE_DATE])
    resultat["saison"] = date.dt.month.apply(saison)
    resultat["moment_journee"] = date.dt.hour.apply(moment_journee)
    # NaN → None dans direction_8_points ; pandas le range ensuite comme valeur manquante.
    resultat["direction_8_points"] = resultat[COLONNE_VENT].apply(direction_8_points)
    return resultat


def construire_tableau(mctavish: Station, references: list[Station]) -> pd.DataFrame:
    """Construit le tableau final : une ligne par (heure, station de référence).

    Entrées : la station McTavish et la liste des stations de référence.
    Sortie : les tableaux appariés empilés, avec les catégories. La colonne
        « Station Name » indique la référence de chaque ligne.
    Échec : ValueError si la liste de références est vide.
    """
    if not references:
        raise ValueError("La liste des stations de référence est vide.")

    cible = mctavish.make_target()
    morceaux = [apparier(cible, reference.data) for reference in references]
    return ajouter_categories(pd.concat(morceaux, ignore_index=True))


# ---------------------------------------------------------------------------
# Classes de variables
# ---------------------------------------------------------------------------


class Variable(ABC):
    """Variable d'entrée du modèle, capable de valider une saisie."""

    def __init__(self, nom: str) -> None:
        """Entrée : nom de la colonne du modèle. Échec : DonneeInvalideError si le nom est vide."""
        if not isinstance(nom, str) or not nom.strip():
            raise DonneeInvalideError("Le nom d'une variable ne peut pas être vide.")
        self._nom = nom

    @property
    def nom(self) -> str:
        """Nom de la variable (lecture seule)."""
        return self._nom

    @abstractmethod
    def valider(self, valeur: object) -> object:
        """Vérifie une saisie et la retourne convertie.

        Entrée : la valeur saisie.
        Sortie : la valeur dans le bon type.
        Échec : DonneeInvalideError avec un message clair.
        """

    def _verifier_non_vide(self, valeur: object) -> str:
        """Retourne la saisie en texte sans espaces autour ; DonneeInvalideError si vide."""
        if valeur is None or str(valeur).strip() == "":
            raise DonneeInvalideError(f"{self._nom} : la saisie est vide.")
        return str(valeur).strip()

    def __repr__(self) -> str:
        """Représentation lisible pour le débogage, ex. Variable('saison')."""
        return f"{type(self).__name__}({self._nom!r})"


class VariableNumerique(Variable):
    """Variable numérique bornée par des limites physiques."""

    def __init__(self, nom: str, minimum: float, maximum: float) -> None:
        """Entrées : nom, bornes incluses. Échec : DonneeInvalideError si minimum > maximum."""
        super().__init__(nom)
        if minimum > maximum:
            raise DonneeInvalideError(f"{nom} : minimum ({minimum}) supérieur au maximum ({maximum}).")
        self._minimum = float(minimum)
        self._maximum = float(maximum)

    @property
    def minimum(self) -> float:
        """Borne inférieure acceptée, incluse (lecture seule)."""
        return self._minimum

    @property
    def maximum(self) -> float:
        """Borne supérieure acceptée, incluse (lecture seule)."""
        return self._maximum

    def valider(self, valeur: object) -> float:
        """Entrée : nombre ou texte (« 12.5 » ou « 12,5 »).
        Sortie : la valeur en float.
        Échec : DonneeInvalideError si vide, non numérique ou hors de [minimum, maximum].
        """
        texte = self._verifier_non_vide(valeur)
        try:
            nombre = float(texte.replace(",", "."))
        except ValueError:
            raise DonneeInvalideError(f"{self._nom} : « {texte} » n'est pas un nombre.") from None
        # NaN n'est ni < ni > aux bornes : on le refuse à part.
        if math.isnan(nombre) or not self._minimum <= nombre <= self._maximum:
            raise DonneeInvalideError(
                f"{self._nom} : {texte} est hors de l'intervalle [{self._minimum}, {self._maximum}]."
            )
        return nombre

    def __repr__(self) -> str:
        """Représentation avec le nom et les bornes, ex. VariableNumerique('Temp (°C)', -50.0, 45.0)."""
        return f"VariableNumerique({self._nom!r}, {self._minimum}, {self._maximum})"


class VariableCategorielle(Variable):
    """Variable catégorielle limitée à une liste de valeurs permises."""

    def __init__(self, nom: str, valeurs_permises: list[str]) -> None:
        """Entrées : nom, valeurs permises. Échec : DonneeInvalideError si la liste est vide."""
        super().__init__(nom)
        if not valeurs_permises:
            raise DonneeInvalideError(f"{nom} : aucune valeur permise.")
        self._valeurs_permises = [str(v) for v in valeurs_permises]

    @property
    def valeurs_permises(self) -> list[str]:
        """Copie de la liste : la modifier ne change pas la variable."""
        return list(self._valeurs_permises)

    def valider(self, valeur: object) -> str:
        """Entrée : la saisie.
        Sortie : la saisie en texte, sans espaces autour.
        Échec : DonneeInvalideError si vide ou absente des valeurs permises.
        """
        texte = self._verifier_non_vide(valeur)
        if texte not in self._valeurs_permises:
            raise DonneeInvalideError(
                f"{self._nom} : « {texte} » n'est pas permis ; choisir parmi {self._valeurs_permises}."
            )
        return texte

    def __repr__(self) -> str:
        """Représentation avec le nom et les valeurs permises."""
        return f"VariableCategorielle({self._nom!r}, {self._valeurs_permises})"
