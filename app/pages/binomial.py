from flask import Blueprint, current_app, jsonify, render_template, request

from .. import validation as v
from ..pricing import build_tree, price_binomial, price_black_scholes

bp = Blueprint("binomial", __name__)

CONVERGENCE_STEPS = (5, 10, 25, 50, 100, 250, 500, 1000)


@bp.get("/binomial")
def page():
    return render_template("binomial.html", max_steps=current_app.config["MAX_BINOMIAL_STEPS"])


@bp.post("/api/binomial")
def calculate():
    data = request.get_json(silent=True) or {}
    params = v.market(data)
    option_type = v.choice(data, "option_type", "El tipo de opción", ("call", "put"))
    exercise = v.choice(data, "exercise", "El estilo de ejercicio", ("european", "american"))
    steps = v.integer(
        data, "steps", "El número de pasos (N)", min_value=1, max_value=current_app.config["MAX_BINOMIAL_STEPS"]
    )

    try:
        result = price_binomial(**params, N=steps, option_type=option_type, exercise=exercise)
        convergence_steps = sorted({n for n in CONVERGENCE_STEPS if n <= max(steps, 100)} | {steps})
        convergence = [
            price_binomial(**params, N=n, option_type=option_type, exercise=exercise).price
            for n in convergence_steps
        ]
        tree_steps = min(steps, current_app.config["MAX_TREE_STEPS"])
        tree = build_tree(**params, N=steps, option_type=option_type, exercise=exercise, levels=tree_steps)
    except ValueError as exc:
        raise v.ValidationError(str(exc)) from exc

    # Black-Scholes como referencia: valor exacto para la europea y cota inferior para la americana.
    reference = price_black_scholes(**params, option_type=option_type).price

    return jsonify(
        {
            **result.to_dict(),
            "black_scholes": reference,
            "early_exercise_premium": result.price - reference if exercise == "american" else None,
            "convergence": {"steps": convergence_steps, "prices": convergence},
            "tree": {"steps": tree_steps, "total_steps": steps, "truncated": tree_steps < steps, "nodes": tree},
        }
    )
