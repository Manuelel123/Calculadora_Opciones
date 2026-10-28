"""Modelo binomial de Cox-Ross-Rubinstein para opciones europeas y americanas."""

from dataclasses import dataclass
from math import exp, sqrt

import numpy as np


@dataclass(frozen=True)
class BinomialResult:
    price: float
    dt: float
    u: float
    d: float
    p: float
    discount: float

    def to_dict(self) -> dict:
        return {"price": self.price, "dt": self.dt, "u": self.u, "d": self.d, "p": self.p, "discount": self.discount}


def _parameters(r: float, sigma: float, T: float, N: int, q: float) -> tuple[float, float, float, float, float]:
    dt = T / N
    u = exp(sigma * sqrt(dt))
    d = 1 / u
    p = (exp((r - q) * dt) - d) / (u - d)
    if not 0 < p < 1:
        raise ValueError(
            "La probabilidad neutral al riesgo quedó fuera de (0, 1). "
            "Aumenta el número de pasos o revisa la volatilidad y las tasas."
        )
    return dt, u, d, p, exp(-r * dt)


def _payoff(prices: np.ndarray, K: float, option_type: str) -> np.ndarray:
    if option_type == "call":
        return np.maximum(prices - K, 0.0)
    if option_type == "put":
        return np.maximum(K - prices, 0.0)
    raise ValueError(f"Tipo de opción no válido: {option_type!r}")


def _price_ladder(S: float, u: float, N: int) -> np.ndarray:
    """S·u^k para k = -N..N. Como d = 1/u, todo nodo del árbol está en esta escalera."""
    return S * u ** np.arange(-N, N + 1, dtype=float)


def _prices_at(ladder: np.ndarray, N: int, step: int) -> np.ndarray:
    """Precios del subyacente en el paso `step`, del nodo más alto (u^step) al más bajo (u^-step)."""
    return ladder[N + step :: -2][: step + 1]


def price_binomial(
    S: float,
    K: float,
    r: float,
    sigma: float,
    T: float,
    N: int,
    option_type: str = "call",
    exercise: str = "european",
    q: float = 0.0,
) -> BinomialResult:
    """Prima por inducción hacia atrás, vectorizada por paso (memoria O(N))."""
    if exercise not in ("european", "american"):
        raise ValueError(f"Estilo de ejercicio no válido: {exercise!r}")
    dt, u, d, p, disc = _parameters(r, sigma, T, N, q)
    ladder = _price_ladder(S, u, N)
    up, down = disc * p, disc * (1 - p)

    values = _payoff(_prices_at(ladder, N, N), K, option_type)
    for step in range(N - 1, -1, -1):
        values = up * values[:-1] + down * values[1:]
        if exercise == "american":
            np.maximum(values, _payoff(_prices_at(ladder, N, step), K, option_type), out=values)

    return BinomialResult(price=float(values[0]), dt=dt, u=u, d=d, p=p, discount=disc)


def build_tree(
    S: float,
    K: float,
    r: float,
    sigma: float,
    T: float,
    N: int,
    option_type: str = "call",
    exercise: str = "european",
    q: float = 0.0,
    levels: int | None = None,
) -> list[list[dict]]:
    """Primeros `levels` pasos del árbol de N pasos: tree[paso][nodo] con precio, valor y ejercicio anticipado.

    La inducción hacia atrás recorre los N pasos (mismos dt, u, d y p que `price_binomial`), así que el
    valor de la raíz coincide con la prima; solo se guardan los nodos hasta `levels`. El nodo 0 de cada
    paso es el más alto.
    """
    if exercise not in ("european", "american"):
        raise ValueError(f"Estilo de ejercicio no válido: {exercise!r}")
    levels = N if levels is None else min(levels, N)
    _, u, _, p, disc = _parameters(r, sigma, T, N, q)
    ladder = _price_ladder(S, u, N)
    up, down = disc * p, disc * (1 - p)

    stock: list[np.ndarray] = [np.empty(0)] * (levels + 1)
    option: list[np.ndarray] = [np.empty(0)] * (levels + 1)
    early: list[np.ndarray] = [np.empty(0, dtype=bool)] * (levels + 1)

    values = _payoff(_prices_at(ladder, N, N), K, option_type)
    flags = np.zeros(N + 1, dtype=bool)
    for step in range(N, -1, -1):
        if step < N:
            values = up * values[:-1] + down * values[1:]
            if exercise == "american":
                intrinsic = _payoff(_prices_at(ladder, N, step), K, option_type)
                flags = (intrinsic > values) & (intrinsic > 0)
                values = np.maximum(values, intrinsic)
            else:
                flags = np.zeros(step + 1, dtype=bool)
        if step <= levels:
            stock[step] = _prices_at(ladder, N, step)
            option[step] = values
            early[step] = flags

    return [
        [
            {"stock": float(stock[step][j]), "value": float(option[step][j]), "early": bool(early[step][j])}
            for j in range(step + 1)
        ]
        for step in range(levels + 1)
    ]
