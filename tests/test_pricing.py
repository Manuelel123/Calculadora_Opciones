from math import exp

import pytest

from app.pricing import Leg, build_tree, evaluate_strategy, price_binomial, price_black_scholes

# Caso de referencia (Hull): S=K=100, r=5 %, σ=20 %, T=1 → call ≈ 10.4506, put ≈ 5.5735
MARKET = dict(S=100.0, K=100.0, r=0.05, sigma=0.20, T=1.0)


def test_black_scholes_reference_values():
    assert price_black_scholes(**MARKET, option_type="call").price == pytest.approx(10.4506, abs=1e-4)
    assert price_black_scholes(**MARKET, option_type="put").price == pytest.approx(5.5735, abs=1e-4)


@pytest.mark.parametrize("q", [0.0, 0.03])
def test_put_call_parity(q):
    call = price_black_scholes(**MARKET, option_type="call", q=q).price
    put = price_black_scholes(**MARKET, option_type="put", q=q).price
    S, K, r, T = MARKET["S"], MARKET["K"], MARKET["r"], MARKET["T"]
    assert call - put == pytest.approx(S * exp(-q * T) - K * exp(-r * T), abs=1e-10)


def test_greeks_match_finite_differences():
    h = 1e-4
    base = price_black_scholes(**MARKET, option_type="call")
    up = price_black_scholes(**{**MARKET, "S": 100 + h}, option_type="call").price
    down = price_black_scholes(**{**MARKET, "S": 100 - h}, option_type="call").price
    assert base.delta == pytest.approx((up - down) / (2 * h), abs=1e-6)
    assert base.gamma == pytest.approx((up - 2 * base.price + down) / h**2, abs=1e-4)
    vol_up = price_black_scholes(**{**MARKET, "sigma": 0.21}, option_type="call").price
    assert base.vega == pytest.approx(vol_up - base.price, abs=2e-3)  # vega por 1 pp


@pytest.mark.parametrize("option_type", ["call", "put"])
def test_binomial_european_converges_to_black_scholes(option_type):
    bs = price_black_scholes(**MARKET, option_type=option_type).price
    binom = price_binomial(**MARKET, N=2000, option_type=option_type).price
    assert binom == pytest.approx(bs, abs=2e-3)


def test_american_put_worth_more_than_european():
    eu = price_binomial(**MARKET, N=500, option_type="put", exercise="european").price
    am = price_binomial(**MARKET, N=500, option_type="put", exercise="american").price
    assert am > eu
    assert am == pytest.approx(6.0896, abs=2e-3)  # valor de referencia del put americano


def test_american_call_without_dividends_equals_european():
    eu = price_binomial(**MARKET, N=300, option_type="call", exercise="european").price
    am = price_binomial(**MARKET, N=300, option_type="call", exercise="american").price
    assert am == pytest.approx(eu, abs=1e-10)


def test_tree_root_matches_price_and_flags_early_exercise():
    tree = build_tree(**MARKET, N=6, option_type="put", exercise="american")
    price = price_binomial(**MARKET, N=6, option_type="put", exercise="american").price
    assert tree[0][0]["value"] == pytest.approx(price)
    assert [len(col) for col in tree] == list(range(1, 8))
    assert any(node["early"] for col in tree for node in col)


def test_invalid_risk_neutral_probability_raises():
    with pytest.raises(ValueError):
        price_binomial(S=100, K=100, r=0.9, sigma=0.01, T=1, N=1)


def test_bull_call_spread_metrics():
    legs = [Leg("call", "long", 95), Leg("call", "short", 105)]
    result = evaluate_strategy(legs, S=100, r=0.05, sigma=0.2, T=1)
    assert result.net_premium > 0
    assert result.max_profit == pytest.approx(10 - result.net_premium)
    assert result.max_loss == pytest.approx(-result.net_premium)
    assert len(result.breakevens) == 1
    assert result.breakevens[0] == pytest.approx(95 + result.net_premium, abs=1e-6)


def test_unlimited_profit_and_loss_detected():
    long_call = evaluate_strategy([Leg("call", "long", 100)], S=100, r=0.05, sigma=0.2, T=1)
    short_call = evaluate_strategy([Leg("call", "short", 100)], S=100, r=0.05, sigma=0.2, T=1)
    assert long_call.max_profit is None and long_call.max_loss is not None
    assert short_call.max_loss is None and short_call.max_profit is not None
