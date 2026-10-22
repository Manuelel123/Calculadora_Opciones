"""Estrategias de varias patas valoradas con Black-Scholes."""

from dataclasses import dataclass

import numpy as np

from .black_scholes import BlackScholesResult, price_black_scholes

GREEKS = ("delta", "gamma", "vega", "theta", "rho")


@dataclass(frozen=True)
class Leg:
    option_type: str  # "call" | "put"
    side: str  # "long" | "short"
    strike: float
    quantity: int = 1

    @property
    def sign(self) -> int:
        return 1 if self.side == "long" else -1


@dataclass
class StrategyResult:
    legs: list[dict]
    net_premium: float  # > 0 débito pagado, < 0 crédito recibido
    greeks: dict[str, float]
    prices: list[float]
    leg_payoffs: list[list[float]]
    total_payoff: list[float]
    breakevens: list[float]
    max_profit: float | None  # None = ilimitada
    max_loss: float | None


def leg_payoff(prices: np.ndarray, leg: Leg, premium: float) -> np.ndarray:
    """P&L al vencimiento de una pata, ya neto de la prima."""
    if leg.option_type == "call":
        intrinsic = np.maximum(prices - leg.strike, 0.0)
    else:
        intrinsic = np.maximum(leg.strike - prices, 0.0)
    return leg.sign * leg.quantity * (intrinsic - premium)


def _breakevens(prices: np.ndarray, payoff: np.ndarray) -> list[float]:
    points = []
    for i in np.nonzero(np.diff(np.sign(payoff)))[0]:
        x0, x1, y0, y1 = prices[i], prices[i + 1], payoff[i], payoff[i + 1]
        points.append(float(x0 - y0 * (x1 - x0) / (y1 - y0)) if y1 != y0 else float(x0))
    return points


def evaluate_strategy(
    legs: list[Leg],
    S: float,
    r: float,
    sigma: float,
    T: float,
    q: float = 0.0,
    points: int = 600,
) -> StrategyResult:
    priced: list[tuple[Leg, BlackScholesResult]] = [
        (leg, price_black_scholes(S, leg.strike, r, sigma, T, leg.option_type, q)) for leg in legs
    ]

    strikes = [leg.strike for leg in legs]
    low = max(0.0, min(S, *strikes) * 0.5)
    high = max(S, *strikes) * 1.5
    # Los strikes se incluyen en la malla para que los vértices del payoff sean exactos.
    prices = np.union1d(np.linspace(low, high, points), strikes)

    leg_payoffs = [leg_payoff(prices, leg, res.price) for leg, res in priced]
    total = np.sum(leg_payoffs, axis=0)

    # Pendiente del payoff para S → ∞: con pendiente positiva la ganancia es ilimitada,
    # con negativa la pérdida es ilimitada. Hacia S → 0 el payoff siempre está acotado.
    call_slope = sum(leg.sign * leg.quantity for leg in legs if leg.option_type == "call")
    at_zero = float(sum(leg_payoff(np.array([0.0]), leg, res.price)[0] for leg, res in priced))
    finite = [*total.tolist(), at_zero]

    return StrategyResult(
        legs=[
            {
                "option_type": leg.option_type,
                "side": leg.side,
                "strike": leg.strike,
                "quantity": leg.quantity,
                **res.to_dict(),
            }
            for leg, res in priced
        ],
        net_premium=sum(leg.sign * leg.quantity * res.price for leg, res in priced),
        greeks={g: sum(leg.sign * leg.quantity * getattr(res, g) for leg, res in priced) for g in GREEKS},
        prices=prices.tolist(),
        leg_payoffs=[p.tolist() for p in leg_payoffs],
        total_payoff=total.tolist(),
        breakevens=_breakevens(prices, total),
        max_profit=None if call_slope > 0 else max(finite),
        max_loss=None if call_slope < 0 else min(finite),
    )
