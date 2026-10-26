from dataclasses import asdict

from flask import Blueprint, current_app, jsonify, render_template, request

from .. import validation as v
from ..pricing import Leg, evaluate_strategy, price_black_scholes

bp = Blueprint("black_scholes", __name__)

# Estrategias predefinidas: strikes como múltiplos del spot ("stock" es el subyacente,
# que entra siempre al spot y no usa strike).
PRESETS = {
    "long_synthetic_call": ("Largo call sintético", [("stock", "long", 1.00), ("put", "long", 1.00)]),
    "short_synthetic_call": ("Corto call sintético", [("stock", "short", 1.00), ("put", "short", 1.00)]),
    "long_synthetic_put": ("Largo put sintético", [("stock", "short", 1.00), ("call", "long", 1.00)]),
    "short_synthetic_put": ("Corto put sintético", [("stock", "long", 1.00), ("call", "short", 1.00)]),
    "bull_call_spread": ("Bull call spread", [("call", "long", 0.95), ("call", "short", 1.05)]),
    "bear_call_spread": ("Bear call spread", [("call", "short", 0.95), ("call", "long", 1.05)]),
    "bull_put_spread": ("Bull put spread", [("put", "long", 0.95), ("put", "short", 1.05)]),
    "bear_put_spread": ("Bear put spread", [("put", "long", 1.05), ("put", "short", 0.95)]),
    "butterfly": (
        "Butterfly spread con calls",
        [("call", "long", 0.90), ("call", "short", 1.00), ("call", "short", 1.00), ("call", "long", 1.10)],
    ),
    "put_butterfly": (
        "Butterfly spread con puts",
        [("put", "long", 0.90), ("put", "short", 1.00), ("put", "short", 1.00), ("put", "long", 1.10)],
    ),
}


@bp.get("/black-scholes")
def page():
    presets = {key: {"label": label, "legs": legs} for key, (label, legs) in PRESETS.items()}
    return render_template("black_scholes.html", presets=presets, max_legs=current_app.config["MAX_LEGS"])


@bp.post("/api/black-scholes")
def calculate():
    data = request.get_json(silent=True) or {}
    params = v.market(data)
    option_type = v.choice(data, "option_type", "El tipo de opción", ("call", "put"))
    result = price_black_scholes(**params, option_type=option_type)
    call, put = (price_black_scholes(**params, option_type=t).price for t in ("call", "put"))

    # Precio de la opción hoy frente a su valor intrínseco, para un rango de spots.
    spots = [params["K"] * (0.5 + i / 100) for i in range(101)]
    curve = [price_black_scholes(**{**params, "S": s}, option_type=option_type) for s in spots]

    return jsonify(
        {
            **result.to_dict(),
            "call": call,
            "put": put,
            "curve": {
                "spots": spots,
                "prices": [c.price for c in curve],
                "intrinsic": [c.intrinsic for c in curve],
                "delta": [c.delta for c in curve],
            },
        }
    )


@bp.post("/api/estrategias")
def strategy():
    data = request.get_json(silent=True) or {}
    params = v.market(data, require_strike=False)
    raw_legs = data.get("legs") or []
    if not isinstance(raw_legs, list) or not raw_legs:
        raise v.ValidationError("Agrega al menos una posición.", "legs")
    if len(raw_legs) > current_app.config["MAX_LEGS"]:
        raise v.ValidationError(f"Máximo {current_app.config['MAX_LEGS']} posiciones.", "legs")

    legs = []
    for i, raw in enumerate(raw_legs, start=1):
        if not isinstance(raw, dict):
            raise v.ValidationError(f"La posición {i} no es válida.", "legs")
        option_type = v.choice(raw, "option_type", f"El tipo de la posición {i}", ("call", "put", "stock"))
        legs.append(
            Leg(
                option_type=option_type,
                side=v.choice(raw, "side", f"El lado de la posición {i}", ("long", "short")),
                # El subyacente entra al spot: no necesita strike.
                strike=params["S"]
                if option_type == "stock"
                else v.number(raw, "strike", f"El strike de la posición {i}", min_value=0, exclusive_min=True),
                quantity=v.integer(raw, "quantity", f"La cantidad de la posición {i}", min_value=1, max_value=1000),
            )
        )

    return jsonify(asdict(evaluate_strategy(legs, **params)))
