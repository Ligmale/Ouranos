"""Téléchargement unique des données climatiques horaires d'ECCC.

Télécharge un CSV par station et par mois depuis le service de téléchargement en lot
d'Environnement et Changement climatique Canada, et l'enregistre dans donnees/brutes/.
Les fichiers déjà présents ne sont pas retéléchargés.

Utilisation :
    python src/telechargement.py                  # année par défaut (2025)
    python src/telechargement.py 2023 2024 2025   # plusieurs années en une fois
"""

import argparse
import os
import time
from datetime import date
import urllib.error
import urllib.request
from collections.abc import Iterator

# Station de la ville (McTavish) et stations de référence (aéroports), avec leur stationID ECCC.
STATIONS: dict[str, int] = {
    "MCTAVISH": 10761,  # McTavish (McGill, centre-ville) — station de la ville
    "MONTREAL INTL A": 51157,  # Aéroport Montréal-Trudeau (YUL, Dorval) — référence
    "MONTREAL/ST-HUBERT": 48374,  # Aéroport de St-Hubert (Longueuil) — référence
    "MONTREAL MIRABEL INTL A": 49608,  # Aéroport de Mirabel (rural, 42 km au nord) — référence
}
ANNEE: int = 2025  # année utilisée si aucune n'est donnée en argument
PREMIERE_ANNEE: int = 1840  # plus anciennes données d'ECCC ; avant, l'année est refusée

URL_BASE: str = "https://climate.weather.gc.ca/climate_data/bulk_data_e.html"
DOSSIER_BRUTES: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "donnees", "brutes")
ENTETE_ATTENDUE: str = "Date/Time (LST)"
DELAI_SECONDES: float = 0.5  # pause entre deux requêtes, pour ne pas surcharger le serveur
TIMEOUT_SECONDES: int = 30


def generer_mois(stations: dict[str, int], annees: list[int]) -> Iterator[tuple[int, int, int]]:
    """Génère les triplets (stationID, année, mois) à télécharger.

    Entrées : stations, dictionnaire nom -> stationID ; annees, les années voulues.
    Sortie : un triplet (stationID, année, mois) à la fois, mois de 1 à 12.
    Cas d'échec : aucun ; un dictionnaire ou une liste vide ne génère rien.
    """
    for station_id in stations.values():
        for annee in annees:
            for mois in range(1, 13):
                yield station_id, annee, mois


def verifier_annees(annees: list[int], annee_courante: int) -> list[int]:
    """Vérifie les années demandées et les met en ordre, sans doublon.

    Entrées : les années demandées ; l'année en cours (limite supérieure).
    Sortie : les années triées, chacune une seule fois.
    Cas d'échec : ValueError si la liste est vide ou si une année est avant 1840 ou
    après l'année en cours.
    """
    if not annees:
        raise ValueError("Aucune année demandée.")
    for annee in annees:
        if not PREMIERE_ANNEE <= annee <= annee_courante:
            raise ValueError(f"Année invalide : {annee} (attendue entre {PREMIERE_ANNEE} et {annee_courante})")
    return sorted(set(annees))


def construire_url(station_id: int, annee: int, mois: int) -> str:
    """Construit l'URL de téléchargement en lot des données horaires d'un mois.

    Entrées : station_id, identifiant ECCC ; annee ; mois, de 1 à 12.
    Sortie : l'URL complète (timeframe=1 signifie données horaires).
    Cas d'échec : ValueError si le mois n'est pas entre 1 et 12.
    """
    if not 1 <= mois <= 12:
        raise ValueError(f"Mois invalide : {mois} (attendu entre 1 et 12)")
    return (
        f"{URL_BASE}?format=csv&stationID={station_id}&Year={annee}&Month={mois}&Day=1&timeframe=1&submit=Download+Data"
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


def telecharger_tout(stations: dict[str, int], annees: list[int], dossier: str) -> list[str]:
    """Télécharge tous les mois de toutes les stations et années, sans refaire les fichiers existants.

    Entrées : stations, dictionnaire nom -> stationID ; annees ; dossier de destination.
    Sortie : la liste des messages d'échec (vide si tout a réussi).
    Cas d'échec : les erreurs de téléchargement sont collectées, pas levées ;
    OSError si le dossier ne peut pas être créé.
    """
    os.makedirs(dossier, exist_ok=True)
    echecs: list[str] = []
    for station_id, annee, mois in generer_mois(stations, annees):
        chemin = chemin_fichier(dossier, station_id, annee, mois)
        if os.path.exists(chemin):
            continue
        url = construire_url(station_id, annee, mois)
        try:
            telecharger_fichier(url, chemin)
        except (urllib.error.URLError, TimeoutError, ValueError) as erreur:
            echecs.append(f"station {station_id}, {annee}-{mois:02d} : {erreur}")
        time.sleep(DELAI_SECONDES)
    return echecs


def lire_annees(arguments: list[str] | None = None) -> list[int]:
    """Lit les années sur la ligne de commande.

    Entrée : les arguments (None : ceux du terminal, sys.argv).
    Sortie : les années demandées, ou [ANNEE] si aucune n'est donnée.
    Cas d'échec : argparse affiche un message et quitte si un argument n'est pas un entier.
    """
    analyseur = argparse.ArgumentParser(description="Télécharge les données horaires d'ECCC (un CSV par station et par mois).")
    analyseur.add_argument("annees", nargs="*", type=int, metavar="ANNEE",
                           help=f"années à télécharger (par défaut : {ANNEE})")
    annees: list[int] = analyseur.parse_args(arguments).annees
    return annees or [ANNEE]


def main() -> None:
    """Lit les années demandées, lance le téléchargement et affiche un résumé."""
    try:
        annees = verifier_annees(lire_annees(), date.today().year)
    except ValueError as erreur:
        print(erreur)
        return
    liste = ", ".join(str(a) for a in annees)
    print(f"Téléchargement {liste} de {len(STATIONS)} stations vers {os.path.normpath(DOSSIER_BRUTES)}")
    echecs = telecharger_tout(STATIONS, annees, DOSSIER_BRUTES)
    if echecs:
        print(f"{len(echecs)} fichier(s) en échec (relancer le script pour réessayer) :")
        for message in echecs:
            print(f"  - {message}")
    else:
        print("Tous les fichiers sont présents.")


if __name__ == "__main__":
    main()
