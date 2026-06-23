from econ_eval import stats


def test_bootstrap_ci_brackets_point():
    scores = [[1.0, 1.0], [0.0, 1.0], [1.0, 0.0]]
    point, lo, hi = stats.bootstrap_ci(scores, iters=2000, seed=1)
    assert lo <= point <= hi
    assert 0.0 <= lo and hi <= 1.0


def test_winrate_all_a():
    a = [[1.0], [1.0], [1.0]]
    b = [[0.0], [0.0], [0.0]]
    rate, n = stats.paired_winrate(a, b)
    assert rate == 1.0 and n == 3


def test_winrate_tie():
    a = [[0.5], [0.5]]
    b = [[0.5], [0.5]]
    rate, _ = stats.paired_winrate(a, b)
    assert rate == 0.5


def test_sign_test_significant_and_not():
    a = [[1.0]] * 6
    b = [[0.0]] * 6
    assert stats.sign_test(a, b) < 0.05      # 6-0 sweep -> p = 2/64 ~ 0.03
    a2 = [[1.0], [0.0]]
    b2 = [[0.0], [1.0]]
    assert stats.sign_test(a2, b2) == 1.0     # 1-1 -> not significant
