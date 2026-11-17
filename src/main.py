"""Point d'entrée d'Ouranos : streamlit run src/main.py

Streamlit réexécute ce fichier à chaque interaction ; afficher_application() reconstruit
donc la page à chaque fois. Le modèle n'est jamais réentraîné ici : il est chargé depuis
modeles/ (créé par python src/modele.py).
"""

from interface import afficher_application

afficher_application()
