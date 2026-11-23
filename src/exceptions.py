class OuranosError(Exception):
    "C'est une classe parente pour toutes les exceptions personnalisées..."
    pass

class DonneeInvalideError(OuranosError):
    "Levée lorsque l'utilisateur ou une valeur de donnée est invalide (hors limite, mauvais type, format incorrect, etc.)"
    def __init__(self, message: str = "L'entrée n'est pas valide...") -> None:
        """Entrée : le message à afficher à l'utilisateur (un message par défaut sinon)."""
        super().__init__(message)

class ModeleNonTrouveError(OuranosError):
    "Levée lorsque le fichier du modèle entraîné (.joblib) ou le fichier de métadonnées (JSON) est introuvable."
    def __init__(self, message: str = "Le modèle entraîné ou ses métadonnées sont introuvables.") -> None:
        """Entrée : le message à afficher, idéalement avec le chemin du fichier manquant."""
        super().__init__(message)

class ErreurPredictionError(OuranosError):
    "Levée lorsqu'une erreur survient lors du calcul de la prédiction par le modèle."
    def __init__(self, message: str = "Erreur lors de la génération de la prédiction.") -> None:
        """Entrée : le message à afficher, avec la cause de l'échec si elle est connue."""
        super().__init__(message)
