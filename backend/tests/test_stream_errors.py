"""Phase 5.5 — `_format_stream_error` must not leak raw exception text to the browser.

The old fall-through was `f"Compliance agent failed: {raw_message}"`, which shipped internal
paths, model ids and upstream API detail straight into the SSE `error` event.
"""

import pytest

from app.api import _GENERIC_STREAM_ERROR, _format_stream_error


class UpstreamError(Exception):
    pass


LEAKY_ERRORS = [
    UpstreamError(
        "anthropic.InternalServerError: model claude-sonnet-4-6 failed at "
        "/Users/someone/SWE/compliance-agent/backend/agent/nodes.py:312"
    ),
    UpstreamError("Invalid API key sk-proj-AbCdEf123456789 for org org-abc123"),
    UpstreamError("connection refused to pinecone index compliance-frameworks"),
    KeyError("PINECONE_API_KEY"),
    ValueError("/Users/tobiakere/SWE/compliance-agent/backend/.env not found"),
]


@pytest.mark.parametrize("error", LEAKY_ERRORS, ids=lambda e: type(e).__name__)
def test_unclassified_errors_return_a_generic_message(error):
    assert _format_stream_error(error) == _GENERIC_STREAM_ERROR


@pytest.mark.parametrize("error", LEAKY_ERRORS, ids=lambda e: type(e).__name__)
def test_no_fragment_of_the_exception_survives(error):
    message = _format_stream_error(error)

    for leak in ("/Users/", ".py", "sk-proj", "org-", "PINECONE", "claude-sonnet"):
        assert leak not in message


def test_rate_limits_are_still_classified():
    message = _format_stream_error(Exception("429 Too Many Requests: quota exceeded"))

    assert "Rate limit reached" in message
    assert "429" not in message


def test_missing_repositories_are_still_classified():
    message = _format_stream_error(Exception("repo not found: acme/private"))

    assert "Repository not found" in message
    # The repo the user typed is theirs, but the upstream phrasing still stays out.
    assert "acme/private" not in message


def test_timeouts_are_still_classified():
    assert "timed out" in _format_stream_error(TimeoutError("request timed out after 120s"))


def test_an_empty_exception_still_produces_copy():
    assert _format_stream_error(Exception("")) == _GENERIC_STREAM_ERROR
