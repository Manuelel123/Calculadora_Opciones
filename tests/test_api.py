import pytest

from app import create_app

MARKET = {"spot": 100, "strike": 100, "rate": 5, "volatility": 20, "maturity": 1}


@pytest.fixture
def client():
    app = create_app()
    app.testing = True
    return app.test_client()


@pytest.mark.parametrize("path", ["/", "/binomial", "/black-scholes"])
def test_pages_render(client, path):
    assert client.get(path).status_code == 200


def test_unknown_page_returns_404(client):
    assert client.get("/no-existe").status_code == 404


def test_binomial_endpoint(client):
    res = client.post(
        "/api/binomial", json={**MARKET, "option_type": "put", "exercise": "american", "steps": 200}
    )
    assert res.status_code == 200
    body = res.get_json()
    assert body["price"] == pytest.approx(6.09, abs=0.01)
    assert body["early_exercise_premium"] > 0
    assert body["tree"]["truncated"] is True
    assert body["convergence"]["steps"][-1] == 200


def test_black_scholes_endpoint(client):
    res = client.post("/api/black-scholes", json={**MARKET, "option_type": "call"})
    assert res.status_code == 200
    body = res.get_json()
    assert body["price"] == pytest.approx(10.4506, abs=1e-4)
    assert len(body["curve"]["spots"]) == 101


def test_strategy_endpoint(client):
    legs = [
        {"side": "long", "option_type": "call", "strike": 100, "quantity": 1},
        {"side": "long", "option_type": "put", "strike": 100, "quantity": 1},
    ]
    res = client.post("/api/estrategias", json={**MARKET, "legs": legs})
    assert res.status_code == 200
    body = res.get_json()
    assert body["max_profit"] is None
    assert len(body["breakevens"]) == 2


@pytest.mark.parametrize(
    "payload, field",
    [
        ({**MARKET, "volatility": 0, "option_type": "call", "exercise": "european", "steps": 10}, "volatility"),
        ({**MARKET, "spot": "abc", "option_type": "call", "exercise": "european", "steps": 10}, "spot"),
        ({**MARKET, "option_type": "call", "exercise": "european", "steps": 2.5}, "steps"),
        ({**MARKET, "option_type": "binaria", "exercise": "european", "steps": 10}, "option_type"),
    ],
)
def test_binomial_validation_errors(client, payload, field):
    res = client.post("/api/binomial", json=payload)
    assert res.status_code == 400
    assert res.get_json()["field"] == field


def test_strategy_rejects_too_many_legs(client):
    leg = {"side": "long", "option_type": "call", "strike": 100, "quantity": 1}
    res = client.post("/api/estrategias", json={**MARKET, "legs": [leg] * 5})
    assert res.status_code == 400
