from monitoring_agent import holt_linear_trend


def test_holt_linear_trend():
    # Test a simple rising trend: 10, 15, 20, 25 (increasing by 5 each time)
    # Using alpha=0.9, beta=0.9 to make it very responsive to the recent trend
    series = [10.0, 15.0, 20.0, 25.0]
    pred = holt_linear_trend(series, alpha=0.9, beta=0.9, steps_ahead=3)
    # Expectation: trend is ~5 per step, so next 3 steps = 25 + 3*5 = ~40
    print(f"Predicted: {pred}")
    assert pred > 35.0

