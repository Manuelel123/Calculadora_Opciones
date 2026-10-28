from math import exp

import numpy as np
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


def test_truncated_tree_uses_all_steps():
    tree = build_tree(**MARKET, N=200, option_type="put", exercise="american", levels=6)
    price = price_binomial(**MARKET, N=200, option_type="put", exercise="american")
    assert tree[0][0]["value"] == pytest.approx(price.price)
    assert tree[1][0]["stock"] == pytest.approx(MARKET["S"] * price.u)
    assert [len(col) for col in tree] == list(range(1, 8))


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


@pytest.mark.parametrize(
    "legs, replicated",
    [
        ([Leg("stock", "long", 0), Leg("put", "long", 100)], Leg("call", "long", 100)),
        ([Leg("stock", "short", 0), Leg("put", "short", 100)], Leg("call", "short", 100)),
        ([Leg("stock", "short", 0), Leg("call", "long", 100)], Leg("put", "long", 100)),
        ([Leg("stock", "long", 0), Leg("call", "short", 100)], Leg("put", "short", 100)),
    ],
)
def test_synthetic_positions_replicate_option(legs, replicated):
    synthetic = evaluate_strategy(legs, S=100, r=0.05, sigma=0.2, T=1)
    option = evaluate_strategy([replicated], S=100, r=0.05, sigma=0.2, T=1)
    # Mismo perfil de pagos salvo una constante (el costo de financiamiento de K) y mismas griegas.
    diff = np.subtract(synthetic.total_payoff, option.total_payoff)
    assert np.ptp(diff) == pytest.approx(0, abs=1e-9)
    for greek in ("delta", "gamma", "vega"):
        assert synthetic.greeks[greek] == pytest.approx(option.greeks[greek])
    assert (synthetic.max_profit is None) == (option.max_profit is None)
    assert (synthetic.max_loss is None) == (option.max_loss is None)


def test_stock_leg_is_priced_at_spot():
    result = evaluate_strategy([Leg("stock", "long", 0)], S=100, r=0.05, sigma=0.2, T=1)
    assert result.net_premium == 100
    assert result.greeks["delta"] == 1
    assert result.breakevens == [pytest.approx(100)]
    assert result.max_profit is None and result.max_loss == pytest.approx(-100)


@pytest.mark.parametrize(
    "legs, credit",
    [
        ([Leg("call", "short", 95), Leg("call", "long", 105)], True),  # bear call spread
        ([Leg("put", "long", 95), Leg("put", "short", 105)], True),  # bull put spread
        ([Leg("put", "long", 105), Leg("put", "short", 95)], False),  # bear put spread
    ],
)
def test_vertical_spreads_are_bounded(legs, credit):
    result = evaluate_strategy(legs, S=100, r=0.05, sigma=0.2, T=1)
    assert (result.net_premium < 0) == credit
    assert result.max_profit is not None and result.max_loss is not None
    assert result.max_profit - result.max_loss == pytest.approx(10)
    assert len(result.breakevens) == 1


@pytest.mark.parametrize("option_type", ["call", "put"])
def test_butterfly_spread_metrics(option_type):
    legs = [Leg(option_type, "long", 90), Leg(option_type, "short", 100, 2), Leg(option_type, "long", 110)]
    result = evaluate_strategy(legs, S=100, r=0.05, sigma=0.2, T=1)
    assert result.net_premium > 0
    assert result.max_profit == pytest.approx(10 - result.net_premium)
    assert result.max_loss == pytest.approx(-result.net_premium)
    assert len(result.breakevens) == 2
