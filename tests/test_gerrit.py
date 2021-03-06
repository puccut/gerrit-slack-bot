import gerrit
import pytest


@pytest.mark.parametrize(
    "url, expected_query",
    (
        (
            "https://review.balabit/#/q/topic:f/matez+(status:open)",
            "topic:f/matez+(status:open)",
        ),
        ("https://review.balabit/#/c/39170/", "39170"),
        ("https://review.balabit/39170", "39170"),
    ),
)
def test_parse_url(url, expected_query):
    assert gerrit.parse_query(url) == expected_query


def test_invalid_parse_url():
    with pytest.raises(ValueError):
        gerrit.parse_query("some-invalid-url.com")


class TestGerritClient:
    def test_changes_url(self):
        client = gerrit.AsyncApi("http://some.url", None, None)
        assert client.changes_url("some-query") == "http://some.url/#/q/some-query"
