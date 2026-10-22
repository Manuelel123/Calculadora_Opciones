"""Modelo de Black-Scholes-Merton con rendimiento continuo q.

q representa el dividend yield de una acción o la tasa extranjera de una divisa
(modelo de Garman-Kohlhagen). Con q = 0 se obtiene el Black-Scholes clásico.
"""

from dataclasses import asdict, dataclass
from math import exp, log, sqrt
from statistics import NormalDist

_N = NormalDist()


@dataclass(frozen=True)
class BlackScholesResult:
    price: float
    d1: float
    d2: float
    delta: float
    gamma: float
    vega: float  # por 1 punto de volatilidad (σ + 0.01)
    theta: float  # por día calendario
    rho: float  # por 1 punto de tasa (r + 0.01)
    intrinsic: float
    time_value: float

    def to_dict(self) -> dict:
        return asdict(self)


def d1_d2(S: float, K: float, r: float, sigma: float, T: float, q: float = 0.0) -> tuple[float, float]:
    vol_sqrt_t = sigma * sqrt(T)
    d1 = (log(S / K) + (r - q + 0.5 * sigma**2) * T) / vol_sqrt_t
    return d1, d1 - vol_sqrt_t


def price_black_scholes(
    S: float,
    K: float,
    r: float,
    sigma: float,
    T: float,
    option_type: str = "call",
    q: float = 0.0,
) -> BlackScholesResult:
    """Precio y griegas de una opción europea."""
    d1, d2 = d1_d2(S, K, r, sigma, T, q)
    disc_r, disc_q = exp(-r * T), exp(-q * T)
    pdf_d1 = _N.pdf(d1)

    if option_type == "call":
        price = S * disc_q * _N.cdf(d1) - K * disc_r * _N.cdf(d2)
        delta = disc_q * _N.cdf(d1)
        theta_year = (
            -S * disc_q * pdf_d1 * sigma / (2 * sqrt(T))
            - r * K * disc_r * _N.cdf(d2)
            + q * S * disc_q * _N.cdf(d1)
        )
        rho = K * T * disc_r * _N.cdf(d2)
        intrinsic = max(S - K, 0.0)
    elif option_type == "put":
        price = K * disc_r * _N.cdf(-d2) - S * disc_q * _N.cdf(-d1)
        delta = disc_q * (_N.cdf(d1) - 1)
        theta_year = (
            -S * disc_q * pdf_d1 * sigma / (2 * sqrt(T))
            + r * K * disc_r * _N.cdf(-d2)
            - q * S * disc_q * _N.cdf(-d1)
        )
        rho = -K * T * disc_r * _N.cdf(-d2)
        intrinsic = max(K - S, 0.0)
    else:
        raise ValueError(f"Tipo de opción no válido: {option_type!r}")

    gamma = disc_q * pdf_d1 / (S * sigma * sqrt(T))
    vega = S * disc_q * pdf_d1 * sqrt(T)

    return BlackScholesResult(
        price=price,
        d1=d1,
        d2=d2,
        delta=delta,
        gamma=gamma,
        vega=vega / 100,
        theta=theta_year / 365,
        rho=rho / 100,
        intrinsic=intrinsic,
        time_value=price - intrinsic,
    )
