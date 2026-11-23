import os.path as path
import pandas as pd

PATH_DONNEES = path.join(path.dirname(path.abspath(__file__)), "..", "donnees", "brutes")
STATIONS_ID = [10761, 48374, 49608, 51157]  # McTavish, St-Hubert, Mirabel, YUL (Montréal-Trudeau)

# Types imposés : sinon pandas devine le type colonne par colonne,
# et une colonne vide ou avec du texte serait lue comme du texte.
SCHEMA_NUMERIQUE = {
    "Temp (°C)": "float64",
    "Dew Point Temp (°C)": "float64",
    "Rel Hum (%)": "float64",
    "Precip. Amount (mm)": "float64",
    "Wind Dir (10s deg)": "float64",
    "Wind Spd (km/h)": "float64",
    "Visibility (km)": "float64",
    "Stn Press (kPa)": "float64",
    "Hmdx": "float64",
    "Wind Chill": "float64",
}

COLONNES_GARDEES = [
    "Station Name",
    "Date/Time (LST)",
    "Temp (°C)",
    "Dew Point Temp (°C)",
    "Rel Hum (%)",
    "Wind Dir (10s deg)",
    "Wind Spd (km/h)",
    "Visibility (km)",
    "Stn Press (kPa)",
]

COLONNES_CIBLE_GARDEES = ["Temp (°C)", "Date/Time (LST)"]

# Seuil de la tendance de pression sur 3 h (à noter dans DECISIONS.md).
SEUIL_PRESSION_KPA = 0.1

try:
    pd.read_csv(path.join(PATH_DONNEES, "10761_2025_10.csv"), encoding="utf-8-sig")
except FileNotFoundError:
    print("Le fichier de données n'existe pas. Veuillez vérifier le chemin et le nom du fichier.")


class Station:
    """Données horaires d'une station ECCC : chargement des CSV mensuels, nettoyage et cible."""

    def __init__(self, station_id: int, mois: list[int] | None = None, years: list[int] | None = None) -> None:
        """Charge et nettoie aussitôt les données de la station.

        Entrées : l'identifiant ECCC (voir STATIONS_ID), les mois (1 à 12, tous par défaut)
            et les années (2025 par défaut).
        Échec : ValueError si un mois ou une année est invalide ; FileNotFoundError si un CSV manque.
        """
        self.station_id = station_id
        # Deux attributs, un type chacun : les mois bruts, puis le tableau nettoyé.
        self._brutes: list[pd.DataFrame] = []
        self._data: pd.DataFrame = pd.DataFrame()
        self.load_data(mois, years)
        self.clean_data()

    @property
    def data(self) -> pd.DataFrame:
        """Tableau nettoyé de la station (lecture seule)."""
        return self._data

    def load_data(self, mois: list[int] | None = None, years: list[int] | None = None) -> list[pd.DataFrame]:
        """Lit un CSV par (année, mois) dans donnees/brutes/, avec les types numériques imposés.

        Entrées : les mois (1 à 12, tous par défaut) et les années (2025 par défaut).
        Sortie : la liste des tableaux bruts, un par mois (aussi gardée dans self._brutes) ;
            vide si la station n'est pas dans STATIONS_ID.
        Échec : ValueError si un mois n'est pas entre 1 et 12 ou une année dépasse 2026 ;
            FileNotFoundError si un CSV est absent (lancer telechargement.py).
        """
        self._brutes = []
        if mois is None:
            mois = list(range(1, 13))
        else:
            for moi in mois:
                if moi not in list(range(1, 13)):
                    raise ValueError(f"Mois Invalide : {moi} (pas entre 0 - 12)")
        if years is None:
            years = [2025]
        else:
            for year in years:
                if year > 2026:
                    raise ValueError(f"Année Invalide : {year} (avant 2026)")
        if self.station_id in STATIONS_ID:
            for year in years:
                for moi in mois:
                    self._brutes.append(
                        pd.read_csv(
                            path.join(PATH_DONNEES, f"{self.station_id}_{year}_{moi:02d}.csv"),
                            dtype=SCHEMA_NUMERIQUE,
                            encoding="utf-8-sig",
                            encoding_errors="replace",
                        )
                    )
        return self._brutes

    def clean_data(self) -> pd.DataFrame:
        """Assemble les mois, garde les colonnes utiles, trie par date et ajoute la tendance de pression.

        Sortie : le tableau nettoyé (aussi gardé dans self._data), avec « delta_pression3h »
            (variation sur 3 h) et « tendance_pression » (hausse, stable, baisse ; None si inconnue).
        Échec : ValueError si aucun mois n'a été chargé ; KeyError si une colonne attendue manque.
        """
        # Tri par date : shift(3) décale de 3 lignes, qui doivent être 3 heures.
        self._data = (
            pd.concat(self._brutes, ignore_index=True)[COLONNES_GARDEES]
            .sort_values("Date/Time (LST)")
            .reset_index(drop=True)
        )
        pression = self._data["Stn Press (kPa)"]
        self._data["delta_pression3h"] = pression - pression.shift(3)
        delta = self._data["delta_pression3h"]
        tendance = pd.Series("stable", index=self._data.index, dtype="object")
        tendance[delta > SEUIL_PRESSION_KPA] = "hausse"
        tendance[delta < -SEUIL_PRESSION_KPA] = "baisse"
        # pression manquante : on garde le manquant, l'imputation s'en occupe
        tendance[delta.isna()] = None
        self._data["tendance_pression"] = tendance
        return self._data

    def make_target(self) -> pd.DataFrame:
        """Réduit les données à la date et à la température : la cible, côté McTavish.

        Sortie : un tableau à deux colonnes (« Temp (°C) », « Date/Time (LST) »), qui remplace self._data.
        Échec : comme clean_data.
        """
        self._data = self.clean_data()[COLONNES_CIBLE_GARDEES]
        return self._data


if __name__ == "__main__":
    stations = []
    for station in STATIONS_ID:
        stations.append(Station(station, mois=list(range(1, 13)), years=[2025]))
    print("Tests Locaux Réussis")
    for station in stations:
        print(station.data.head(5))
        print(station.data.columns)
