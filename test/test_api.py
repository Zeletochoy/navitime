from navitime import api


def test_address_search():
    results = api.address_search("六本木グランドタワー")
    assert results
