"""Lectura y validación de los parámetros que llegan por JSON."""

from math import isfinite
from typing import Any


class ValidationError(ValueError):
    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.field = field


def number(
    data: dict[str, Any],
    field: str,
    label: str,
    *,
    default: float | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    exclusive_min: bool = False,
) -> float:
    raw = data.get(field, default)
    if raw is None or raw == "":
        raise ValidationError(f"{label} es obligatorio.", field)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ValidationError(f"{label} debe ser un número.", field) from None
    if not isfinite(value):
        raise ValidationError(f"{label} debe ser un número finito.", field)
    if min_value is not None and (value <= min_value if exclusive_min else value < min_value):
        relation = "mayor que" if exclusive_min else "mayor o igual a"
        raise ValidationError(f"{label} debe ser {relation} {min_value:g}.", field)
    if max_value is not None and value > max_value:
        raise ValidationError(f"{label} no puede superar {max_value:g}.", field)
    return value


def integer(data: dict[str, Any], field: str, label: str, *, min_value: int, max_value: int, default: int | None = None) -> int:
    value = number(data, field, label, default=default, min_value=min_value, max_value=max_value)
    if not value.is_integer():
        raise ValidationError(f"{label} debe ser un número entero.", field)
    return int(value)


def choice(data: dict[str, Any], field: str, label: str, options: tuple[str, ...], *, default: str | None = None) -> str:
    value = str(data.get(field, default) or "").lower()
    if value not in options:
        raise ValidationError(f"{label} no es válido.", field)
    return value


def market(data: dict[str, Any], *, require_strike: bool = True) -> dict[str, float]:
    """Parámetros de mercado comunes a ambos modelos. Las tasas y σ llegan en porcentaje."""
    params = {
        "S": number(data, "spot", "El precio spot (S₀)", min_value=0, exclusive_min=True),
        "r": number(data, "rate", "La tasa libre de riesgo (r)", min_value=-50, max_value=100) / 100,
        "sigma": number(data, "volatility", "La volatilidad (σ)", min_value=0, exclusive_min=True, max_value=500) / 100,
        "T": number(data, "maturity", "El vencimiento (T)", min_value=0, exclusive_min=True, max_value=100),
        "q": number(data, "yield", "El rendimiento q", default=0, min_value=-50, max_value=100) / 100,
    }
    if require_strike:
        params["K"] = number(data, "strike", "El strike (K)", min_value=0, exclusive_min=True)
    return params
