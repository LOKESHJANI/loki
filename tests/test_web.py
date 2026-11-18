"""Web tool tests. No real network: search and fetch are replaced with fakes."""
import pytest

from loki.tools import web


@pytest.fixture
def public_dns(monkeypatch):
    """Pretend every hostname resolves to a public IP (except obvious local ones)."""
    real = web.is_public_host

    def fake(host):
        return real(host) if host in {"localhost", "127.0.0.1", "192.168.1.1", "10.0.0.5"} else True

    monkeypatch.setattr(web, "is_public_host", fake)


def test_web_search_formats_and_marks_untrusted(monkeypatch):
    fake_results = [
        {"title": "Chief Minister of Tamil Nadu", "href": "https://example.org/cm", "body": "The current  CM is X."},
        {"title": "Second", "href": "https://example.org/2", "body": "More"},
    ]
    monkeypatch.setattr(web, "_search", lambda q, n: fake_results[:n])
    out = web.web_search("tamil nadu cm", max_results=2)
    assert out.startswith(web.UNTRUSTED_START) and out.endswith(web.UNTRUSTED_END)
    assert "1. Chief Minister of Tamil Nadu" in out
    assert "https://example.org/cm" in out
    assert "The current CM is X." in out  # whitespace collapsed


def test_web_search_clamps_result_count(monkeypatch):
    seen = {}
    monkeypatch.setattr(web, "_search", lambda q, n: seen.setdefault("n", n) and [])
    web.web_search("x", max_results=50)
    assert seen["n"] == 8


def test_web_search_reports_failures(monkeypatch):
    def boom(q, n):
        raise RuntimeError("rate limited")

    monkeypatch.setattr(web, "_search", boom)
    assert web.web_search("x").startswith("Web search failed: RuntimeError")


@pytest.mark.parametrize("url", ["http://localhost:11434", "http://127.0.0.1", "http://192.168.1.1/admin", "10.0.0.5"])
def test_read_webpage_refuses_local_addresses(url, public_dns, monkeypatch):
    monkeypatch.setattr(web, "_fetch", lambda u: pytest.fail("must not fetch local addresses"))
    assert web.read_webpage(url).startswith("Refused")


def test_read_webpage_extracts_truncates_and_marks_untrusted(public_dns, monkeypatch):
    monkeypatch.setattr(web, "_fetch", lambda u: "<html>...</html>")
    monkeypatch.setattr(web, "_extract_text", lambda html: "A" * 5000)
    out = web.read_webpage("example.org/article")
    assert "Source: https://example.org/article" in out
    assert "[truncated, 5000 characters total]" in out
    assert out.startswith(web.UNTRUSTED_START)


def test_read_webpage_blocks_redirect_to_local_network(public_dns, monkeypatch):
    def redirected(u):
        raise web.BlockedAddress("192.168.1.1 is not a public web address")

    monkeypatch.setattr(web, "_fetch", redirected)
    assert web.read_webpage("https://example.org").startswith("Refused: 192.168.1.1")


def test_read_webpage_handles_empty_pages(public_dns, monkeypatch):
    monkeypatch.setattr(web, "_fetch", lambda u: "<html></html>")
    monkeypatch.setattr(web, "_extract_text", lambda html: "")
    assert web.read_webpage("https://example.org").startswith("Could not find readable text")


def test_redirect_hook_checks_every_hop():
    import httpx

    with pytest.raises(web.BlockedAddress):
        web._check_request(httpx.Request("GET", "http://127.0.0.1/secret"))
