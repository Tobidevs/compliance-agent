"""Langfuse tracing setup for the compliance agent.

The agent runs on LangGraph/LangChain, so we use Langfuse's LangChain CallbackHandler
integration: a single handler passed into the top-level graph invocation auto-captures
every nested LLM call (model names, token usage, generations) across the evidence and
validation subagents. This module configures the Langfuse singleton, masks credential-like
tokens before export, and exposes a root-span context manager that sets trace-level
attributes (name, session, tags, metadata) shared by all nested observations.
"""

import os
import re
from contextlib import contextmanager

# Conservative redaction of credential-like tokens before anything is sent to Langfuse.
# Kept tight so normal source code / compliance text is never mangled.
_SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9\-_]{8,}|pk-lf-[A-Za-z0-9\-]{6,}|gh[pousr]_[A-Za-z0-9]{20,}|Bearer\s+[A-Za-z0-9._\-+/]+=*)"
)


def _mask(*, data, **_):
    """Recursively redact secret-like strings in trace input/output."""
    if isinstance(data, str):
        return _SECRET_RE.sub("[REDACTED]", data)
    if isinstance(data, dict):
        return {key: _mask(data=value) for key, value in data.items()}
    if isinstance(data, (list, tuple)):
        return [_mask(data=value) for value in data]
    return data


_enabled = False


def init_langfuse() -> bool:
    """Configure the Langfuse singleton if credentials are present; safe no-op otherwise.

    Called once at startup AFTER env vars are loaded so the client never initializes with
    missing credentials. Supports either LANGFUSE_HOST or LANGFUSE_BASE_URL for the host.
    """
    global _enabled
    if not (os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")):
        return False

    from langfuse import Langfuse  # imported lazily, after env is loaded

    Langfuse(
        host=os.getenv("LANGFUSE_HOST") or os.getenv("LANGFUSE_BASE_URL"),
        environment=os.getenv("LANGFUSE_TRACING_ENVIRONMENT", "development"),
        mask=_mask,
    )
    _enabled = True
    return True


def langfuse_enabled() -> bool:
    return _enabled


@contextmanager
def langfuse_trace(*, name, input, session_id, tags, metadata):
    """Open a root Langfuse span and propagate trace-level attributes to every nested
    LangGraph/LangChain observation created by the CallbackHandler within this context."""
    from langfuse import get_client, propagate_attributes

    client = get_client()
    with propagate_attributes(
        trace_name=name, session_id=session_id, tags=tags, metadata=metadata
    ):
        with client.start_as_current_observation(
            as_type="span", name=name, input=input
        ) as span:
            yield span
