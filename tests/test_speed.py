from econ_eval import stats


def test_latency_summary_known_values():
    s = stats.latency_summary([0.0, 10.0])
    assert s["n"] == 2
    assert s["mean"] == 5.0
    assert s["median"] == 5.0
    assert s["p95"] == 9.5
    assert s["min"] == 0.0
    assert s["max"] == 10.0


def test_latency_summary_single_sample():
    s = stats.latency_summary([4.0])
    assert s["n"] == 1
    assert s["mean"] == s["median"] == s["p95"] == s["min"] == s["max"] == 4.0


def test_latency_summary_empty_raises():
    try:
        stats.latency_summary([])
    except ValueError:
        return
    raise AssertionError("expected ValueError for empty input")


def test_check_bars_flags_only_violations():
    medians = {"deepseek-flash": 5.8, "muse": 32.2, "gemini": 35.3}
    bars = {"deepseek-flash": 15.0, "muse": 30.0, "gemini": 60.0}
    assert stats.check_latency_bars(medians, bars) == ["muse"]


def test_check_bars_ignores_models_without_rows():
    assert stats.check_latency_bars({}, {"deepseek-flash": 15.0}) == []
