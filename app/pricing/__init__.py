"""Motores de valoración de opciones, independientes de Flask."""

from .binomial import BinomialResult, build_tree, price_binomial
from .black_scholes import BlackScholesResult, price_black_scholes
from .strategies import Leg, StrategyResult, evaluate_strategy

__all__ = [
    "BinomialResult",
    "BlackScholesResult",
    "Leg",
    "StrategyResult",
    "build_tree",
    "evaluate_strategy",
    "price_binomial",
    "price_black_scholes",
]
