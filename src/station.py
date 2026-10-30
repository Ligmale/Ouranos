import os.path as path
import polars as pl

PATH_DONNEES = path.join(path.dirname(path.abspath(__file__)), "..", "donnees", "brutes")
STATIONS_ID = [10761, 48374, 49608, 51157]  # McTavish, St-Hubert, Mirabel, YUL (Montréal-Trudeau)

try:
    pl.read_csv(path.join(PATH_DONNEES, "10761_2025_10.csv"))
except FileNotFoundError:
    print("Le fichier de données n'existe pas. Veuillez vérifier le chemin et le nom du fichier.")


class Station:
    def __init__(self, station_id: int, mois: list[int] | None = None, years: list[int] | None = None):
        self.station_id = station_id
        self.load_data(mois, years)

    def load_data(self, mois: list[int] | None = None, years: list[int] | None = None) -> None:
        self.data = []
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
                    self.data.append(pl.read_csv(path.join(PATH_DONNEES, f"{self.station_id}_{year}_{moi:02d}.csv")))

    def clean_data(self) -> pl.DataFrame:
        return pl.DataFrame()


if __name__ == "__main__":
    stations = []
    for station in STATIONS_ID:
        stations.append(Station(station, mois=list(range(1, 13)), years=[2025]))
    print("Tests Locaux Réussis")
