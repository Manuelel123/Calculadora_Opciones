import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev")
    JSON_SORT_KEYS = False

    # Límites de cálculo
    MAX_BINOMIAL_STEPS = 5000
    MAX_TREE_STEPS = 6  # pasos máximos para dibujar el árbol nodo a nodo
    MAX_LEGS = 4
