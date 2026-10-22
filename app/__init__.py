from flask import Flask, jsonify, render_template, request

from .config import Config
from .validation import ValidationError


def create_app(config: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config)

    from .pages import binomial, black_scholes, home

    app.register_blueprint(home.bp)
    app.register_blueprint(binomial.bp)
    app.register_blueprint(black_scholes.bp)

    @app.errorhandler(ValidationError)
    def handle_validation_error(error: ValidationError):
        return jsonify({"error": str(error), "field": error.field}), 400

    @app.errorhandler(404)
    def not_found(_error):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Recurso no encontrado"}), 404
        return render_template("404.html"), 404

    return app
