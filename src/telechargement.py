"""Téléchargement unique des données climatiques horaires d'ECCC.

Télécharge un CSV par station et par mois depuis le service de téléchargement en lot
d'Environnement et Changement climatique Canada, et l'enregistre dans donnees/brutes/.
Les fichiers déjà présents ne sont pas retéléchargés.

Utilisation : python src/telechargement.py
"""

import os
import time
import urllib.error
import urllib.request
from collections.abc import Iterator

# Station de la ville (McTavish) et stations de référence (aéroports), avec leur stationID ECCC.
STATIONS: dict[str, int] = {
    "MCTAVISH": 10761,
    "MONTREAL INTL A": 51157,
    "MONTREAL/ST-HUBERT": 48374,
    "MONTREAL MIRABEL INTL A": 49608,
}
ANNEE: int = 2025

URL_BASE: str = "https://climate.weather.gc.ca/climate_data/bulk_data_e.html"
DOSSIER_BRUTES: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "donnees", "brutes")
ENTETE_ATTENDUE: str = "Date/Time (LST)"
DELAI_SECONDES: float = 0.5  # pause entre deux requêtes, pour ne pas surcharger le serveur
TIMEOUT_SECONDES: int = 30


def generer_mois(stations: dict[str, int], annee: int) -> Iterator[tuple[int, int]]:
    """Génère les couples (stationID, mois) à télécharger.

    Entrées : stations, dictionnaire nom -> stationID ; annee, l'année voulue.
    Sortie : un couple (stationID, mois) à la fois, mois de 1 à 12.
    Cas d'échec : aucun ; un dictionnaire vide ne génère rien.
    """
    for station_id in stations.values():
        for mois in range(1, 13):
            yield station_id, mois


def construire_url(station_id: int, annee: int, mois: int) -> str:
    """Construit l'URL de téléchargement en lot des données horaires d'un mois.

    Entrées : station_id, identifiant ECCC ; annee ; mois, de 1 à 12.
    Sortie : l'URL complète (timeframe=1 signifie données horaires).
    Cas d'échec : ValueError si le mois n'est pas entre 1 et 12.
    """
    if not 1 <= mois <= 12:
        raise ValueError(f"Mois invalide : {mois} (attendu entre 1 et 12)")
    return (
        f"{URL_BASE}?format=csv&stationID={station_id}&Year={annee}"
        f"&Month={mois}&Day=1&timeframe=1&submit=Download+Data"
    )


def chemin_fichier(dossier: str, station_id: int, annee: int, mois: int) -> str:
    """Donne le chemin du fichier brut d'une station pour un mois.

    Entrées : dossier de destination, station_id, annee, mois.
    Sortie : chemin de la forme <dossier>/<stationID>_<annee>_<mois sur 2 chiffres>.csv.
    Cas d'échec : aucun.
    """
    return os.path.join(dossier, f"{station_id}_{annee}_{mois:02d}.csv")


def telecharger_fichier(url: str, chemin: str) -> None:
    """Télécharge un CSV et l'enregistre, après avoir vérifié son contenu.

    Entrées : url à télécharger ; chemin du fichier à écrire.
    Sortie : aucune (le fichier est écrit sur le disque).
    Cas d'échec : urllib.error.URLError (réseau, serveur) ; ValueError si la réponse
    n'est pas un CSV de données horaires (rien n'est alors écrit).
    """
    with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDES) as reponse:
        contenu = reponse.read()
    premiere_ligne = contenu.decode("utf-8-sig", errors="replace").split("\n", 1)[0]
    if ENTETE_ATTENDUE not in premiere_ligne:
        raise ValueError(f"Réponse inattendue (pas un CSV horaire) pour {url}")
    with open(chemin, "wb") as fichier:
        fichier.write(contenu)


def telecharger_tout(stations: dict[str, int], annee: int, dossier: str) -> list[str]:
    """Télécharge tous les mois de toutes les stations, sans refaire les fichiers existants.

    Entrées : stations, dictionnaire nom -> stationID ; annee ; dossier de destination.
    Sortie : la liste des messages d'échec (vide si tout a réussi).
    Cas d'échec : les erreurs de téléchargement sont collectées, pas levées ;
    OSError si le dossier ne peut pas être créé.
    """
    os.makedirs(dossier, exist_ok=True)
    echecs: list[str] = []
    for station_id, mois in generer_mois(stations, annee):
        chemin = chemin_fichier(dossier, station_id, annee, mois)
        if os.path.exists(chemin):
            continue
        url = construire_url(station_id, annee, mois)
        try:
            telecharger_fichier(url, chemin)
        except (urllib.error.URLError, TimeoutError, ValueError) as erreur:
            echecs.append(f"station {station_id}, mois {mois} : {erreur}")
        time.sleep(DELAI_SECONDES)
    return echecs


def main() -> None:
    """Lance le téléchargement et affiche un résumé."""
    print(f"Téléchargement {ANNEE} de {len(STATIONS)} stations vers {os.path.normpath(DOSSIER_BRUTES)}")
    echecs = telecharger_tout(STATIONS, ANNEE, DOSSIER_BRUTES)
    if echecs:
        print(f"{len(echecs)} fichier(s) en échec (relancer le script pour réessayer) :")
        for message in echecs:
            print(f"  - {message}")
    else:
        print("Tous les fichiers sont présents.")


if __name__ == "__main__":
    main()
