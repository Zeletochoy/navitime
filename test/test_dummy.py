from navitime import api, cli


def test_nothing():
    api = cli
    assert 21 * 2 == 42
