class OuranosError(Exception):
    "C'est une classe parente pour toutes les exceptions personnalisées..."
    pass

class DonneeInvalideError(OuranosError):
    "Levée lorsque l'utilisateur ou une valeur de donnée est invalide (hors limite, mauvais type, format incorrect, etc.)"
    def __init__(self, message = "L'entrée n'est pas valide...") -> None:
        super().__init__(message)

class ModeleNonTrouveError(OuranosError):
    "Levée lorsque le fichier du modèle entraîné (.pkl) ou le fichier de métadonnées (JSON) est introuvable."
    def __init__(self, message = "Le modèle entraîné ou ses métadonnées sont introuvables.") -> None:
        super().__init__(message)

class ErreurPredictionError(OuranosError):
    "Levée lorsqu'une erreur survient lors du calcul de la prédiction par le modèle."
    def __init__(self, message = "Erreur lors de la génération de la prédiction.") -> None:
        super().__init__(message)
        